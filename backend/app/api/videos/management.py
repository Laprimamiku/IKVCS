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

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

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

