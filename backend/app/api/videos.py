"""
视频管理 API

这个文件的作用：
1. 获取视频列表（GET /api/v1/videos）
2. 获取视频详情（GET /api/v1/videos/{video_id}）
3. 测试转码功能（POST /api/v1/videos/{video_id}/transcode）- 仅用于测试

类比 Java：
    相当于 Spring Boot 的 VideoController
    
需求：5.1-5.5
"""
import os
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.video import Video
from pydantic import BaseModel

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
                "duration": 120
            }
        }


class TranscodeTestRequest(BaseModel):
    """转码测试请求"""
    video_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": 1
            }
        }


class TranscodeTestResponse(BaseModel):
    """转码测试响应"""
    message: str
    video_id: int
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "转码任务已启动",
                "video_id": 1,
                "status": "transcoding"
            }
        }


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取视频状态
    
    用于测试：查看视频转码状态
    
    状态说明：
    - 0: 转码中
    - 1: 审核中
    - 2: 已发布
    - 3: 已拒绝
    - -1: 转码失败
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视频 {video_id} 不存在"
        )
    
    # 状态文本映射
    status_map = {
        0: "转码中",
        1: "审核中",
        2: "已发布",
        3: "已拒绝",
        -1: "转码失败"
    }
    
    return VideoStatusResponse(
        video_id=video.id,
        title=video.title,
        status=video.status,
        status_text=status_map.get(video.status, "未知状态"),
        video_url=video.video_url,
        duration=video.duration
    )


@router.post("/{video_id}/transcode", response_model=TranscodeTestResponse)
async def test_transcode(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试转码功能（仅用于开发测试）
    
    ⚠️ 注意：这个接口仅用于测试转码功能
    正常流程中，转码会在上传完成后自动触发
    
    使用场景：
    1. 测试转码功能是否正常
    2. 重新转码失败的视频
    3. 开发调试
    
    前提条件：
    - 视频必须已经上传完成（有对应的 upload_session）
    - 原始视频文件必须存在
    
    测试步骤：
    1. 先完成视频上传（调用 /api/v1/upload/finish）
    2. 获取返回的 video_id
    3. 调用此接口触发转码
    4. 轮询 /api/v1/videos/{video_id}/status 查看转码状态
    """
    # 检查视频是否存在
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视频 {video_id} 不存在"
        )
    
    # 检查是否有对应的上传会话
    from app.models.upload import UploadSession
    upload_session = db.query(UploadSession).filter(
        UploadSession.video_id == video_id
    ).first()
    
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"视频 {video_id} 没有对应的上传会话，无法转码"
        )
    
    # 更新视频状态为转码中
    video.status = 0
    db.commit()
    
    # 触发转码任务
    from app.services.transcode_service import TranscodeService
    background_tasks.add_task(TranscodeService.transcode_video, video_id)
    
    return TranscodeTestResponse(
        message="转码任务已启动，请稍后查询视频状态",
        video_id=video_id,
        status="transcoding"
    )

from app.schemas.video import (
    VideoListRequest, 
    VideoListResponse, 
    VideoListItemResponse,
    VideoDetailResponse,
    UploaderBriefResponse,
    CategoryBriefResponse
)
from app.services.video_service import VideoService
from math import ceil


@router.get("", response_model=VideoListResponse)
async def get_video_list(
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取视频列表
    
    功能：
    - 分页展示已发布的视频
    - 支持按分类筛选
    - 支持关键词搜索（标题和描述）
    
    查询参数：
    - page: 页码（从1开始，默认1）
    - page_size: 每页数量（默认20，最大100）
    - category_id: 分类ID（可选）
    - keyword: 搜索关键词（可选）
    
    返回：
    - items: 视频列表
    - total: 总数
    - page: 当前页
    - page_size: 每页数量
    - total_pages: 总页数
    
    需求：5.1, 5.2, 5.3
    """
    # 参数验证
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    # 查询视频列表
    videos, total = VideoService.get_video_list(
        db=db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        keyword=keyword
    )
    
    # 计算总页数
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    # 构建响应
    items = []
    for video in videos:
        # 获取上传者信息
        uploader = db.query(User).filter(User.id == video.uploader_id).first()
        # 获取分类信息
        from app.models.video import Category
        category = db.query(Category).filter(Category.id == video.category_id).first()
        
        items.append(VideoListItemResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            cover_url=video.cover_url,
            duration=video.duration,
            view_count=VideoService.get_merged_view_count(db, video.id),  # 合并 Redis 和 MySQL 的播放量
            like_count=video.like_count,
            collect_count=video.collect_count,
            uploader=UploaderBriefResponse(
                id=uploader.id,
                username=uploader.username,
                nickname=uploader.nickname,
                avatar=uploader.avatar
            ),
            category=CategoryBriefResponse(
                id=category.id,
                name=category.name
            ),
            created_at=video.created_at
        ))
    
    return VideoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video_detail(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    获取视频详情
    
    功能：
    - 获取视频完整信息
    - 包含播放地址（m3u8）
    - 自动增加播放量
    
    路径参数：
    - video_id: 视频ID
    
    返回：
    - 视频完整信息
    
    需求：5.4, 5.5
    """
    # 获取视频详情
    video = VideoService.get_video_detail(db, video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视频不存在或未发布"
        )
    
    # 增加播放量（异步，不影响响应速度）
    VideoService.increment_view_count(db, video_id)
    
    # 获取上传者信息
    uploader = db.query(User).filter(User.id == video.uploader_id).first()
    
    # 获取分类信息
    from app.models.video import Category
    category = db.query(Category).filter(Category.id == video.category_id).first()
    
    # 构建响应
    return VideoDetailResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        cover_url=video.cover_url,
        video_url=video.video_url,
        subtitle_url=video.subtitle_url,
        duration=video.duration,
        status=video.status,
        view_count=VideoService.get_merged_view_count(db, video.id),  # 合并 Redis 和 MySQL 的播放量
        like_count=video.like_count,
        collect_count=video.collect_count,
        uploader=UploaderBriefResponse(
            id=uploader.id,
            username=uploader.username,
            nickname=uploader.nickname,
            avatar=uploader.avatar
        ),
        category=CategoryBriefResponse(
            id=category.id,
            name=category.name
        ),
        created_at=video.created_at
    )


@router.post("/{video_id}/view")
async def increase_view_count(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    增加视频播放量（公开接口）

    需求：5.5
    """
    success = VideoService.increment_view_count(db, video_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视频 {video_id} 不存在"
        )

    return {
        "success": True,
        "message": "播放量已记录",
        "view_count": VideoService.get_merged_view_count(db, video_id)
    }


def _save_upload_file(target_dir: str, filename: str, upload_file: UploadFile) -> str:
    """保存上传文件并返回相对 URL"""
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, filename)
    with open(file_path, "wb") as f:
        f.write(upload_file.file.read())
    # StaticFiles 挂载在 /uploads
    return f"/{file_path.replace(os.path.sep, '/')}"


@router.post("/{video_id}/cover")
async def upload_video_cover(
    video_id: int,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传视频封面

    需求：19.4
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

    if video.uploader_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该视频")

    ext = os.path.splitext(cover.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="封面格式不支持，仅支持 JPG/PNG/WEBP"
        )

    filename = f"{video_id}_cover_{uuid.uuid4().hex}{ext}"
    relative_url = _save_upload_file("uploads/covers", filename, cover)

    video.cover_url = relative_url
    db.commit()

    return {"success": True, "cover_url": relative_url}


@router.post("/{video_id}/subtitle")
async def upload_video_subtitle(
    video_id: int,
    subtitle: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传字幕文件（SRT/VTT/JSON/ASS）

    需求：19.1, 19.2
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

    if video.uploader_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该视频")

    ext = os.path.splitext(subtitle.filename or "")[1].lower()
    if ext not in [".srt", ".vtt", ".json", ".ass"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="字幕格式不支持，仅支持 SRT、VTT、JSON、ASS"
        )

    filename = f"{video_id}_subtitle_{uuid.uuid4().hex}{ext}"
    relative_url = _save_upload_file("uploads/subtitles", filename, subtitle)

    video.subtitle_url = relative_url
    db.commit()

    return {"success": True, "subtitle_url": relative_url}
