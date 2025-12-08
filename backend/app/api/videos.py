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
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.video import Video
from app.schemas.video import (
    VideoListRequest,
    VideoListResponse,
    VideoListItemResponse,
    VideoDetailResponse,
    UploaderBriefResponse,
    CategoryBriefResponse,
    SubtitleUploadResponse,
    CoverUploadResponse,
)
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)
router = APIRouter()


class VideoStatusResponse(BaseModel):
    """视频状态响应"""
    video_id: int
    title: str
    status: int
    status_text: str
    video_url: Optional[str]
    duration: int

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": 1,
                "title": "测试视频",
                "status": 1,
                "status_text": "审核中",
                "video_url": "/videos/hls/1/master.m3u8",
                "duration": 120,
            }
        }


class TranscodeTestRequest(BaseModel):
    """转码测试请求"""
    video_id: int

    class Config:
        json_schema_extra = {"example": {"video_id": 1}}


class TranscodeTestResponse(BaseModel):
    """转码测试响应"""
    message: str
    video_id: int
    status: str

    class Config:
        json_schema_extra = {"example": {"message": "转码任务已启动", "video_id": 1, "status": "transcoding"}}


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询视频状态（开发测试用）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"视频 {video_id} 不存在")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"视频 {video_id} 不存在")

    from app.models.upload import UploadSession

    upload_session = db.query(UploadSession).filter(UploadSession.video_id == video_id).first()
    if not upload_session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有对应的上传会话，无法转码")

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
    """获取视频列表（已发布）"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    videos, total = VideoService.get_video_list(
        db=db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        keyword=keyword,
    )

    total_pages = ceil(total / page_size) if total > 0 else 0

    items = []
    for video in videos:
        uploader = db.query(User).filter(User.id == video.uploader_id).first()
        from app.models.video import Category

        category = db.query(Category).filter(Category.id == video.category_id).first()
        items.append(
            VideoListItemResponse(
                id=video.id,
                title=video.title,
                description=video.description,
                cover_url=video.cover_url,
                duration=video.duration,
                view_count=VideoService.get_merged_view_count(db, video.id),
                like_count=video.like_count,
                collect_count=video.collect_count,
                uploader=UploaderBriefResponse(
                    id=uploader.id,
                    username=uploader.username,
                    nickname=uploader.nickname,
                    avatar=uploader.avatar,
                ),
                category=CategoryBriefResponse(id=category.id, name=category.name),
                created_at=video.created_at,
            )
        )

    return VideoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video_detail(
    video_id: int,
    db: Session = Depends(get_db),
):
    """获取视频详情并增加播放量"""
    video = VideoService.get_video_detail(db, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在或未发布")

    VideoService.increment_view_count(db, video_id)

    uploader = db.query(User).filter(User.id == video.uploader_id).first()
    from app.models.video import Category

    category = db.query(Category).filter(Category.id == video.category_id).first()

    return VideoDetailResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        cover_url=video.cover_url,
        video_url=video.video_url,
        subtitle_url=video.subtitle_url,
        duration=video.duration,
        status=video.status,
        view_count=VideoService.get_merged_view_count(db, video.id),
        like_count=video.like_count,
        collect_count=video.collect_count,
        uploader=UploaderBriefResponse(
            id=uploader.id,
            username=uploader.username,
            nickname=uploader.nickname,
            avatar=uploader.avatar,
        ),
        category=CategoryBriefResponse(id=category.id, name=category.name),
        created_at=video.created_at,
    )


@router.post("/{video_id}/view")
async def increase_view_count(
    video_id: int,
    db: Session = Depends(get_db),
):
    """增加视频播放量（公开接口）"""
    success = VideoService.increment_view_count(db, video_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"视频 {video_id} 不存在")
    return {
        "success": True,
        "message": "播放量已记录",
        "view_count": VideoService.get_merged_view_count(db, video_id),
    }


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    if video.uploader_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有视频上传者可以上传封面")

    ext = os.path.splitext(cover.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="封面格式不支持，仅支持 JPG/PNG/WEBP")

    content = await cover.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="封面文件过大，最大 5MB")

    cover_dir = "uploads/covers"
    unique_filename = f"{video_id}_cover_{uuid.uuid4().hex[:8]}{ext}"
    cover_url = _save_upload_file(cover_dir, unique_filename, content)

    video.cover_url = cover_url
    db.commit()

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    if video.uploader_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有视频上传者可以上传字幕")

    ext = os.path.splitext(subtitle.filename or "")[1].lower()
    if ext not in [".srt", ".vtt", ".json", ".ass"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="字幕格式不支持，仅支持 SRT/VTT/JSON/ASS")

    content = await subtitle.read()
    subtitle_dir = "uploads/subtitles"
    unique_filename = f"{video_id}_subtitle_{uuid.uuid4().hex[:8]}{ext}"
    subtitle_url = _save_upload_file(subtitle_dir, unique_filename, content)

    video.subtitle_url = subtitle_url
    db.commit()

    logger.info(f"视频 {video_id} 字幕上传成功：{subtitle_url}")
    return SubtitleUploadResponse(message="字幕上传成功", subtitle_url=subtitle_url, video_id=video_id)

