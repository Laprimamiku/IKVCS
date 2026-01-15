"""
视频管理 API

功能：
1. 更新视频信息（仅上传者）
2. 删除视频（仅上传者）
3. 上传封面（仅上传者）
4. 上传字幕（仅上传者）
"""
import os
import uuid
import logging
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
from app.schemas.video import (
    VideoDetailResponse,
    VideoUpdateRequest,
    SubtitleUploadResponse,
    CoverUploadResponse,
)
from app.services.video import (
    VideoManagementService,
    VideoResponseBuilder,
)

logger = logging.getLogger(__name__)
router = APIRouter()


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

    logger.info(f"视频 {video_id} 字幕上传成功：{subtitle_url}")
    return SubtitleUploadResponse(message="字幕上传成功", subtitle_url=subtitle_url, video_id=video_id)


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
    
    # 验证视频存在且属于当前用户
    video = VideoRepository.get_by_id(db, video_id)
    if not video:
        raise ResourceNotFoundException("视频不存在")
    
    if video.uploader_id != current_user.id:
        raise ForbiddenException("无权操作此视频")
    
    # 检查是否已启用高码率转码
    if not settings.HIGH_BITRATE_TRANSCODE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="高码率转码功能已禁用"
        )
    
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
    
    # 确定需要转码的高码率清晰度（720p和1080p）
    high_bitrate_resolutions = []
    for res in TranscodeService.RESOLUTIONS:
        name = res[0]
        if name in ["720p", "1080p"]:
            # 检查是否已转码
            resolution_dir = os.path.join(output_dir, name)
            resolution_output = os.path.join(resolution_dir, "index.m3u8")
            if not os.path.exists(resolution_output):
                high_bitrate_resolutions.append(res)
    
    if not high_bitrate_resolutions:
        return success_response(
            message="所有高码率清晰度已转码完成",
            data={"video_id": video_id, "status": "completed"}
        )
    
    # 启动后台转码任务
    import threading
    thread = threading.Thread(
        target=TranscodeService._transcode_other_resolutions_sync,
        args=(video_id, high_bitrate_resolutions, input_path, output_dir),
        daemon=True
    )
    thread.start()
    
    logger.info(f"用户 {current_user.id} 触发高码率转码：video_id={video_id}, resolutions={[r[0] for r in high_bitrate_resolutions]}")
    
    return success_response(
        message="高码率转码任务已启动",
        data={
            "video_id": video_id,
            "status": "transcoding",
            "resolutions": [r[0] for r in high_bitrate_resolutions]
        }
    )

