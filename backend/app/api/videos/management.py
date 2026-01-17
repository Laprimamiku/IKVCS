"""
视频管理 API

功能：
1. 更新视频信息（仅上传者）
2. 删除视频（仅上传者）
3. 上传封面（仅上传者）
4. 上传字幕（仅上传者）
5. 标签管理（添加、删除、获取视频标签）
"""
import os
import uuid
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, ForbiddenException, ValidationException
from app.core.response import success_response
from app.core.transaction import transaction
from app.core.config import settings
from app.models.user import User
from app.models.video import Video
from app.models.video_tag import VideoTag, video_tag_association
from app.schemas.video import (
    VideoDetailResponse,
    VideoUpdateRequest,
    SubtitleUploadResponse,
    SubtitleListResponse,
    SubtitleSelectRequest,
    CoverUploadResponse,
)
from app.services.video import (
    VideoManagementService,
    VideoResponseBuilder,
)
from app.services.ai.asr_service import asr_service
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_subtitle_path(subtitle_url: str, subtitle_dir: str) -> str:
    if os.path.isabs(subtitle_url):
        return subtitle_url
    if subtitle_url.startswith("/"):
        return os.path.join(settings.STORAGE_ROOT, subtitle_url.lstrip("/"))
    return os.path.join(subtitle_dir, subtitle_url)


def _cleanup_subtitle_files(
    video_id: int,
    subtitle_dir: str,
    keep_filename: str,
    source: str,
) -> None:
    if not os.path.exists(subtitle_dir):
        return
    for path in Path(subtitle_dir).glob(f"{video_id}_subtitle*"):
        if path.name == keep_filename:
            continue
        is_ai = "_subtitle_ai_" in path.name
        if source == "ai" and not is_ai:
            continue
        if source == "manual" and is_ai:
            continue
        try:
            path.unlink()
        except Exception as exc:
            logger.warning(f"清理旧字幕失败: {path} error={exc}")


@router.put("/{video_id}", response_model=VideoDetailResponse)
async def update_video(
    video_id: int,
    video_update: VideoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新视频信息（仅上传者可操作）
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    # 调用 Service 层更新视频
    video = VideoManagementService.update_video(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        title=video_update.title,
        description=video_update.description,
        category_id=video_update.category_id,
    )
    
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 获取更新后的视频详情响应
    video_detail = VideoResponseBuilder.get_video_detail_response(db, video_id)
    if not video_detail:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return video_detail


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除视频（仅上传者可操作）
    
    直接硬删除，前端已有确认弹框
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    success = VideoManagementService.delete_video(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        hard_delete=True,  # 直接硬删除
    )
    
    if not success:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return success_response(
        message="视频删除成功"
    )


@router.post("/{video_id}/cover", response_model=CoverUploadResponse)
async def upload_video_cover(
    video_id: int,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传封面图片（JPG/PNG/WEBP，<=5MB，仅上传者可操作）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以上传封面")

    ext = os.path.splitext(cover.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise ValidationException(message="封面格式不支持，仅支持 JPG/PNG/WEBP")

    content = await cover.read()
    if len(content) > 5 * 1024 * 1024:
        raise ValidationException(message="封面文件过大，最大 5MB")

    # 使用配置的封面目录，确保路径正确
    # 静态文件挂载：/uploads -> ./storage/uploads
    # 封面文件路径：./storage/uploads/covers/{filename}
    # URL路径应该是：/uploads/covers/{filename}
    cover_dir = settings.UPLOAD_COVER_DIR
    unique_filename = f"{video_id}_cover_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(cover_dir, unique_filename)
    os.makedirs(cover_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    # 生成URL路径：/uploads/covers/{filename}
    cover_url = f"/uploads/covers/{unique_filename}"

    # 使用事务管理，确保数据一致性
    try:
        with transaction(db):
            video.cover_url = cover_url
            # 事务上下文管理器会自动提交或回滚
    except Exception as e:
        # 如果数据库更新失败，删除已保存的文件
        file_path = os.path.join(cover_dir, unique_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"封面上传失败，已删除文件: {e}")
        raise

    logger.info(f"视频 {video_id} 封面上传成功：{cover_url}")
    return CoverUploadResponse(message="封面上传成功", cover_url=cover_url, video_id=video_id)


@router.post("/{video_id}/subtitle", response_model=SubtitleUploadResponse)
async def upload_video_subtitle(
    video_id: int,
    subtitle: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传字幕文件（SRT/VTT/JSON/ASS，仅上传者可操作）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以上传字幕")

    ext = os.path.splitext(subtitle.filename or "")[1].lower()
    if ext not in [".srt", ".vtt", ".json", ".ass"]:
        raise ValidationException(message="字幕格式不支持，仅支持 SRT/VTT/JSON/ASS")

    content = await subtitle.read()
    # 使用配置的字幕目录，确保路径正确
    # 静态文件挂载：/uploads -> ./storage/uploads
    # 字幕文件路径：./storage/uploads/subtitles/{filename}
    # URL路径应该是：/uploads/subtitles/{filename}
    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    unique_filename = f"{video_id}_subtitle_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(subtitle_dir, unique_filename)
    os.makedirs(subtitle_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    # 生成URL路径：/uploads/subtitles/{filename}
    subtitle_url = f"/uploads/subtitles/{unique_filename}"

    # 使用事务管理，确保数据一致性
    try:
        with transaction(db):
            video.subtitle_url = subtitle_url
            # 事务上下文管理器会自动提交或回滚
    except Exception as e:
        # 如果数据库更新失败，删除已保存的文件
        file_path = os.path.join(subtitle_dir, unique_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"字幕上传失败，已删除文件: {e}")
        raise

    _cleanup_subtitle_files(
        video_id=video_id,
        subtitle_dir=subtitle_dir,
        keep_filename=unique_filename,
        source="manual",
    )

    logger.info(f"视频 {video_id} 字幕上传成功：{subtitle_url}")
    return SubtitleUploadResponse(message="字幕上传成功", subtitle_url=subtitle_url, video_id=video_id)


@router.post("/{video_id}/subtitle/audio", response_model=SubtitleUploadResponse)
async def upload_audio_subtitle(
    video_id: int,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """音频转字幕（云端ASR），仅上传者可操作。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以上传音频字幕")

    ext = os.path.splitext(audio.filename or "")[1].lower()
    if ext not in [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".webm", ".mp4"]:
        raise ValidationException(message="格式不支持，仅支持 MP3/WAV/M4A/AAC/FLAC/OGG/OPUS/WEBM/MP4")

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp_path = tmp_file.name
    tmp_file.close()
    try:
        with open(tmp_path, "wb") as f:
            while True:
                chunk = await audio.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.getsize(tmp_path) == 0:
            raise ValidationException(message="音频文件为空，无法转字幕")

        asr_result, asr_errors = await asr_service.transcribe_media_file(
            Path(tmp_path),
            chunk_seconds=30,
            max_concurrent=5,
        )
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    if asr_errors:
        logger.warning("ASR部分片段失败: video_id=%s, errors=%s", video_id, asr_errors[:3])

    if not asr_result:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="音频转字幕失败，请稍后重试",
        )

    subtitles, full_text = asr_service.extract_segments(asr_result)
    if not subtitles:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="音频转字幕无有效结果，请检查音频内容",
        )

    subtitle_payload = {
        "subtitles": subtitles,
        "source": "ai_asr",
        "model": settings.ASR_MODEL,
        "generated_at": isoformat_in_app_tz(utc_now()),
    }
    if full_text:
        subtitle_payload["text"] = full_text

    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    unique_filename = f"{video_id}_subtitle_ai_{uuid.uuid4().hex[:8]}.json"
    file_path = os.path.join(subtitle_dir, unique_filename)
    os.makedirs(subtitle_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(subtitle_payload, f, ensure_ascii=False)

    subtitle_url = f"/uploads/subtitles/{unique_filename}"
    try:
        with transaction(db):
            video.subtitle_url = subtitle_url
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"音频字幕保存失败，已删除文件: {e}")
        raise

    _cleanup_subtitle_files(
        video_id=video_id,
        subtitle_dir=subtitle_dir,
        keep_filename=unique_filename,
        source="ai",
    )

    logger.info(f"视频 {video_id} 音频字幕生成成功：{subtitle_url}")
    return SubtitleUploadResponse(message="音频字幕生成成功", subtitle_url=subtitle_url, video_id=video_id)


@router.get("/{video_id}/subtitles", response_model=SubtitleListResponse)
async def get_video_subtitles(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取视频可用字幕列表（含手动与AI字幕）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以查看字幕列表")

    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    latest_manual = None
    latest_ai = None
    if os.path.exists(subtitle_dir):
        subtitle_files = sorted(
            Path(subtitle_dir).glob(f"{video_id}_subtitle*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in subtitle_files:
            filename = path.name
            source = "ai" if "_subtitle_ai_" in filename else "manual"
            if source == "ai" and latest_ai:
                continue
            if source == "manual" and latest_manual:
                continue
            url = f"/uploads/subtitles/{filename}"
            created_at = isoformat_in_app_tz(
                datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            )
            item = {
                "url": url,
                "filename": filename,
                "source": source,
                "is_active": url == video.subtitle_url,
                "created_at": created_at,
                "exists": True,
            }
            if source == "ai":
                latest_ai = item
            else:
                latest_manual = item
            if latest_manual and latest_ai:
                break

    items = [item for item in (latest_manual, latest_ai) if item]

    if not items and video.subtitle_url:
        resolved_path = _resolve_subtitle_path(video.subtitle_url, subtitle_dir)
        items.append(
            {
                "url": video.subtitle_url,
                "filename": os.path.basename(video.subtitle_url),
                "source": "legacy",
                "is_active": True,
                "created_at": None,
                "exists": os.path.exists(resolved_path),
            }
        )

    active_items = [item for item in items if item["is_active"]]
    rest_items = [item for item in items if not item["is_active"]]
    return SubtitleListResponse(items=active_items + rest_items, active_url=video.subtitle_url)


@router.post("/{video_id}/subtitle/select", response_model=SubtitleUploadResponse)
async def select_video_subtitle(
    video_id: int,
    request: SubtitleSelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """选择视频展示的字幕文件"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以选择字幕")

    subtitle_url = (request.subtitle_url or "").strip()
    if not subtitle_url:
        raise ValidationException(message="字幕地址不能为空")
    if subtitle_url == (video.subtitle_url or ""):
        return SubtitleUploadResponse(message="字幕切换成功", subtitle_url=subtitle_url, video_id=video_id)
    if not subtitle_url.startswith("/uploads/subtitles/"):
        raise ValidationException(message="字幕地址不合法")

    filename = os.path.basename(subtitle_url)
    if not filename.startswith(f"{video_id}_"):
        raise ValidationException(message="字幕文件不属于该视频")

    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    file_path = os.path.join(subtitle_dir, filename)
    if not os.path.exists(file_path):
        raise ResourceNotFoundException(resource="字幕文件", resource_id=filename)

    with transaction(db):
        video.subtitle_url = subtitle_url

    logger.info(f"视频 {video_id} 切换字幕：{subtitle_url}")
    return SubtitleUploadResponse(message="字幕切换成功", subtitle_url=subtitle_url, video_id=video_id)


@router.post("/{video_id}/reupload/finish")
async def finish_reupload(
    video_id: int,
    file_hash: str = Form(..., min_length=64, max_length=64),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    完成视频重新上传（替换现有视频文件）
    
    流程：
    1. 验证用户权限
    2. 完成分片合并
    3. 删除旧的视频文件和转码文件
    4. 更新视频记录
    5. 触发转码
    """
    from app.services.upload.upload_orchestration_service import UploadOrchestrationService
    from app.services.transcode import TranscodeService
    from app.services.transcode.playlist_generator import PlaylistGenerator
    from app.services.transcode.transcode_service import RESOLUTIONS
    
    try:
        video = UploadOrchestrationService.finish_reupload(
            db=db,
            user_id=current_user.id,
            video_id=video_id,
            file_hash=file_hash
        )
        
        # 触发后台转码任务
        background_tasks.add_task(TranscodeService.transcode_video, video.id)
        
        return success_response(
            message="视频重新上传成功，正在转码中",
            data={"video_id": video.id, "status": "transcoding"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成重新上传失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"完成重新上传失败：{str(e)}"
        )


@router.post("/{video_id}/transcode-high-bitrate")
async def transcode_high_bitrate(
    video_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    继续执行高码率转码（720p/1080p）
    
    用于继续执行未完成的高码率转码任务
    """
    from app.repositories.video_repository import VideoRepository
    from app.repositories.upload_repository import UploadSessionRepository
    from app.services.transcode import TranscodeService
    from app.services.transcode.playlist_generator import PlaylistGenerator
    from app.services.transcode.transcode_service import RESOLUTIONS
    
    # 验证视频存在且属于当前用户
    video = VideoRepository.get_by_id(db, video_id)
    if not video:
        raise ResourceNotFoundException("视频不存在")
    
    if video.uploader_id != current_user.id:
        raise ForbiddenException("无权操作此视频")
    
    if not settings.HIGH_BITRATE_TRANSCODE_ENABLED:
        logger.info(f"自动高码率转码已禁用，手动触发继续执行：video_id={video_id}")
    
    # 获取原始视频路径
    upload_session = UploadSessionRepository.get_by_video_id(db, video_id)
    if not upload_session:
        raise ResourceNotFoundException("视频文件不存在")
    
    input_path = os.path.join(
        settings.VIDEO_ORIGINAL_DIR,
        f"{upload_session.file_hash}_{upload_session.file_name}"
    )
    
    if not os.path.exists(input_path):
        raise ResourceNotFoundException("原始视频文件不存在")
    
    # 获取输出目录
    output_dir = os.path.join(settings.VIDEO_HLS_DIR, str(video_id))

    def _parse_master_resolutions(master_path: str) -> set:
        if not os.path.exists(master_path):
            return set()
        resolutions = set()
        try:
            with open(master_path, "r", encoding="utf-8") as file:
                for raw_line in file:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "index.m3u8" not in line:
                        continue
                    parts = line.split("/")
                    if len(parts) >= 2 and parts[-1].startswith("index.m3u8"):
                        resolutions.add(parts[-2])
        except Exception as exc:
            logger.warning(f"Failed to parse master.m3u8: {master_path}, error={exc}")
        return resolutions

    def _playlist_has_segments(playlist_path: str) -> bool:
        if not os.path.exists(playlist_path):
            return False
        try:
            with open(playlist_path, "r", encoding="utf-8") as file:
                for raw_line in file:
                    line = raw_line.strip()
                    if line and not line.startswith("#"):
                        return True
        except Exception as exc:
            logger.warning(f"Failed to read resolution playlist: {playlist_path}, error={exc}")
        return False

    # Determine which high bitrate resolutions should be (re)generated.
    high_bitrate_names = {"720p", "1080p"}
    high_bitrate_resolutions = [res for res in RESOLUTIONS if res[0] in high_bitrate_names]
    if not high_bitrate_resolutions:
        raise ValidationException(message="High bitrate resolutions are not configured.")

    from app.services.cache.redis_service import redis_service
    lock_key = f"transcode:high:running:{video_id}"
    lock_ttl_seconds = 2 * 60 * 60
    lock_value = redis_service.redis.get(lock_key)

    master_playlist_path = os.path.join(output_dir, "master.m3u8")
    master_resolutions = _parse_master_resolutions(master_playlist_path)

    resolution_order = {"360p": 1, "480p": 2, "720p": 3, "1080p": 4}

    def _collect_existing_resolutions():
        existing = []
        for res in RESOLUTIONS:
            name = res[0]
            resolution_dir = os.path.join(output_dir, name)
            resolution_output = os.path.join(resolution_dir, "index.m3u8")
            if _playlist_has_segments(resolution_output):
                bandwidth = int(res[2].replace('k', '')) * 1000
                existing.append((name, res[1], bandwidth))
        existing.sort(key=lambda item: resolution_order.get(item[0], 99))
        return existing

    invalid_resolutions = []
    missing_in_master = []
    for res in high_bitrate_resolutions:
        name = res[0]
        resolution_dir = os.path.join(output_dir, name)
        resolution_output = os.path.join(resolution_dir, "index.m3u8")
        playlist_ok = _playlist_has_segments(resolution_output)
        in_master = name in master_resolutions
        if playlist_ok:
            if not in_master:
                logger.info(f"master.m3u8 missing resolution: {name}")
                missing_in_master.append(res)
        else:
            logger.info(f"Resolution playlist missing segments: {resolution_output}")
            invalid_resolutions.append(res)

    if missing_in_master and not invalid_resolutions:
        existing = _collect_existing_resolutions()
        if existing:
            master_playlist_content = PlaylistGenerator.build_master_playlist(
                video_id,
                existing
            )
            with open(master_playlist_path, 'w', encoding='utf-8') as f:
                f.write(master_playlist_content)
            logger.info(
                f"高码率播放列表已补全：video_id={video_id}, resolutions={[r[0] for r in existing]}"
            )
        if lock_value:
            try:
                redis_service.redis.delete(lock_key)
            except Exception as exc:
                logger.warning(f"Failed to clear stale transcode lock: {lock_key}, error={exc}")
        return success_response(
            message="高码率播放列表已同步",
            data={
                "video_id": video_id,
                "status": "completed",
                "synced": True,
                "resolutions": [res[0] for res in high_bitrate_resolutions],
            },
        )

    if lock_value:
        if not invalid_resolutions and not missing_in_master:
            try:
                redis_service.redis.delete(lock_key)
            except Exception as exc:
                logger.warning(f"Failed to clear stale transcode lock: {lock_key}, error={exc}")
        elif not force:
            return success_response(
                message="检测到高码率任务锁，确认继续将重新转码。",
                data={
                    "video_id": video_id,
                    "status": "locked",
                    "confirm_required": True,
                    "confirm_message": "检测到未完成的高码率任务，是否重新开始？",
                    "resolutions": [res[0] for res in high_bitrate_resolutions],
                },
            )
        else:
            try:
                redis_service.redis.delete(lock_key)
            except Exception as exc:
                logger.warning(f"Failed to clear stale transcode lock: {lock_key}, error={exc}")

    if not invalid_resolutions and not force:
        return success_response(
            message="High bitrate streams are already available. Confirm to run again.",
            data={
                "video_id": video_id,
                "status": "completed",
                "confirm_required": True,
                "confirm_message": "高码率已完成，是否确认继续？",
                "resolutions": [res[0] for res in high_bitrate_resolutions],
            },
        )

    if not invalid_resolutions and force:
        invalid_resolutions = high_bitrate_resolutions

    # Clear existing outputs before forcing a re-transcode.
    import shutil
    for res in invalid_resolutions:
        name = res[0]
        resolution_dir = os.path.join(output_dir, name)
        resolution_output = os.path.join(resolution_dir, "index.m3u8")
        if os.path.exists(resolution_dir):
            try:
                shutil.rmtree(resolution_dir)
                continue
            except Exception as exc:
                logger.warning(f"Failed to remove resolution directory: {resolution_dir}, error={exc}")
        if os.path.exists(resolution_output):
            try:
                os.remove(resolution_output)
            except Exception as exc:
                logger.warning(f"Failed to remove resolution playlist: {resolution_output}, error={exc}")

    try:
        redis_service.redis.setex(lock_key, lock_ttl_seconds, "1")
    except Exception as exc:
        logger.warning(f"Failed to set transcode lock: {lock_key}, error={exc}")

    def _run_transcode():
        try:
            TranscodeService._transcode_other_resolutions_sync(
                video_id, invalid_resolutions, input_path, output_dir
            )
        finally:
            try:
                redis_service.redis.delete(lock_key)
            except Exception as exc:
                logger.warning(f"Failed to release transcode lock: {lock_key}, error={exc}")

    # Start background transcode task.

    import threading
    thread = threading.Thread(
        target=_run_transcode,
        daemon=True,
    )
    thread.start()
    
    logger.info(
        f"用户 {current_user.id} 触发高码率转码：video_id={video_id}, resolutions={[r[0] for r in invalid_resolutions]}"
    )
    
    return success_response(
        message="高码率转码任务已启动",
        data={
            "video_id": video_id,
            "status": "transcoding",
            "resolutions": [r[0] for r in invalid_resolutions],
            "force": force,
        }
    )


# ==================== 标签管理 API ====================

@router.post("/{video_id}/tags", summary="添加视频标签")
async def add_video_tag(
    video_id: int,
    tag_name: str = Form(..., min_length=1, max_length=50, description="标签名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加视频标签（仅上传者可操作）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以添加标签")
    
    # 清理标签名称（去除首尾空格，转换为小写）
    tag_name = tag_name.strip()
    if not tag_name:
        raise ValidationException(message="标签名称不能为空")
    
    # 查找或创建标签
    tag = db.query(VideoTag).filter(VideoTag.name == tag_name).first()
    if not tag:
        tag = VideoTag(name=tag_name, usage_count=0)
        db.add(tag)
        db.flush()  # 获取tag.id
    
    # 检查视频是否已有该标签
    existing_association = db.execute(
        video_tag_association.select().where(
            video_tag_association.c.video_id == video_id,
            video_tag_association.c.tag_id == tag.id
        )
    ).first()
    
    if existing_association:
        return success_response(
            message="标签已存在",
            data={"tag_id": tag.id, "tag_name": tag.name}
        )
    
    # 添加关联
    db.execute(
        video_tag_association.insert().values(
            video_id=video_id,
            tag_id=tag.id
        )
    )
    
    # 更新使用次数
    tag.usage_count += 1
    
    db.commit()
    
    logger.info(f"视频 {video_id} 添加标签：{tag_name}")
    return success_response(
        message="标签添加成功",
        data={"tag_id": tag.id, "tag_name": tag.name}
    )


@router.delete("/{video_id}/tags/{tag_id}", summary="删除视频标签")
async def remove_video_tag(
    video_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除视频标签（仅上传者可操作）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以删除标签")
    
    tag = db.query(VideoTag).filter(VideoTag.id == tag_id).first()
    if not tag:
        raise ResourceNotFoundException(resource="标签", resource_id=tag_id)
    
    # 检查关联是否存在
    existing_association = db.execute(
        video_tag_association.select().where(
            video_tag_association.c.video_id == video_id,
            video_tag_association.c.tag_id == tag_id
        )
    ).first()
    
    if not existing_association:
        raise ResourceNotFoundException(resource="视频标签关联", resource_id=f"{video_id}-{tag_id}")
    
    # 删除关联
    db.execute(
        video_tag_association.delete().where(
            video_tag_association.c.video_id == video_id,
            video_tag_association.c.tag_id == tag_id
        )
    )
    
    # 更新使用次数
    if tag.usage_count > 0:
        tag.usage_count -= 1
    
    db.commit()
    
    logger.info(f"视频 {video_id} 删除标签：{tag.name}")
    return success_response(message="标签删除成功")


@router.get("/{video_id}/tags", summary="获取视频标签列表")
async def get_video_tags(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """获取视频标签列表（公开接口，但需要视频存在）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 获取视频的所有标签
    tags = db.query(VideoTag).join(
        video_tag_association
    ).filter(
        video_tag_association.c.video_id == video_id
    ).all()
    
    tag_list = [{"id": tag.id, "name": tag.name, "usage_count": tag.usage_count} for tag in tags]
    
    return success_response(
        data={"tags": tag_list},
        message="获取标签列表成功"
    )
