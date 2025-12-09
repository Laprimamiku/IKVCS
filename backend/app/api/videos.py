"""
视频管理 API

功能：
1. 获取视频列表（已发布）
2. 获取视频详情（并增加播放量）
3. 查询/触发转码（开发调试）
4. 上传封面、字幕（仅上传者）
5. 增加播放量（公开）
"""

import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, ForbiddenException, ValidationException
from app.core.response import success_response
from app.core.transaction import transaction
from app.models.user import User
from app.models.video import Video
from app.schemas.video import (
    VideoListRequest,
    VideoListResponse,
    VideoDetailResponse,
    VideoUpdateRequest,
    SubtitleUploadResponse,
    CoverUploadResponse,
    VideoStatusResponse,
    TranscodeTestRequest,
    TranscodeTestResponse,
)
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询视频状态（开发测试用）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)

    status_map = {0: "转码中", 1: "审核中", 2: "已发布", 3: "已拒绝", -1: "转码失败"}
    return VideoStatusResponse(
        video_id=video.id,
        title=video.title,
        status=video.status,
        status_text=status_map.get(video.status, "未知状态"),
        video_url=video.video_url,
        duration=video.duration,
    )


@router.post("/{video_id}/transcode", response_model=TranscodeTestResponse)
async def test_transcode(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发转码（开发调试用）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)

    from app.models.upload import UploadSession

    upload_session = db.query(UploadSession).filter(UploadSession.video_id == video_id).first()
    if not upload_session:
        raise ValidationException(message="没有对应的上传会话，无法转码")

    video.status = 0
    db.commit()

    from app.services.transcode_service import TranscodeService

    background_tasks.add_task(TranscodeService.transcode_video, video_id)

    return TranscodeTestResponse(message="转码任务已启动，请稍后查询视频状态", video_id=video_id, status="transcoding")


@router.get("", response_model=VideoListResponse)
async def get_video_list(
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    获取视频列表（已发布）
    
    路由层只负责参数验证和调用 Service，所有业务逻辑在 Service 层
    """
    # 参数验证（也可以使用 Pydantic 的 Field 验证）
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    # 调用 Service 层获取响应（包含所有业务逻辑）
    return VideoService.get_video_list_response(
        db=db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        keyword=keyword,
    )


@router.get("/my", response_model=VideoListResponse)
async def get_my_videos(
    page: int = 1,
    page_size: int = 20,
    status: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户上传的视频列表
    
    路由层只负责参数验证和调用 Service，所有业务逻辑在 Service 层
    
    注意：此路由必须在 /{video_id} 之前定义，否则会被误匹配
    """
    # 参数验证
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    # 调用 Service 层获取响应
    return VideoService.get_user_video_list_response(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video_detail(
    video_id: int,
    db: Session = Depends(get_db),
):
    """
    获取视频详情并增加播放量
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    # 增加播放量
    VideoService.increment_view_count(db, video_id)
    
    # 获取视频详情响应（包含所有数据组装逻辑）
    video_detail = VideoService.get_video_detail_response(db, video_id)
    if not video_detail:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return video_detail


@router.post("/{video_id}/view")
async def increase_view_count(
    video_id: int,
    db: Session = Depends(get_db),
):
    """增加视频播放量（公开接口）"""
    success = VideoService.increment_view_count(db, video_id)
    if not success:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    view_count = VideoService.get_merged_view_count(db, video_id)
    return success_response(
        data={"view_count": view_count},
        message="播放量已记录"
    )


def _save_upload_file(target_dir: str, filename: str, data: bytes) -> str:
    """保存文件并返回相对 URL"""
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, filename)
    with open(file_path, "wb") as f:
        f.write(data)
    return f"/{file_path.replace(os.path.sep, '/')}"


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

    cover_dir = "uploads/covers"
    unique_filename = f"{video_id}_cover_{uuid.uuid4().hex[:8]}{ext}"
    cover_url = _save_upload_file(cover_dir, unique_filename, content)

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
    subtitle_dir = "uploads/subtitles"
    unique_filename = f"{video_id}_subtitle_{uuid.uuid4().hex[:8]}{ext}"
    subtitle_url = _save_upload_file(subtitle_dir, unique_filename, content)

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


# ==================== 用户视频管理 ====================

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
    video = VideoService.update_video(
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
    video_detail = VideoService.get_video_detail_response(db, video_id)
    if not video_detail:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return video_detail


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    hard_delete: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除视频（仅上传者可操作）
    
    默认使用软删除（status=4），设置 hard_delete=True 可硬删除
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    success = VideoService.delete_video(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        hard_delete=hard_delete,
    )
    
    if not success:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return success_response(
        message="视频删除成功" if not hard_delete else "视频已永久删除"
    )

