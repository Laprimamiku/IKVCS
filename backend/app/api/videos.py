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
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from fastapi import UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

import os
import uuid
import logging
logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.video import Video
from pydantic import BaseModel
from pathlib import Path

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
    CategoryBriefResponse,
    SubtitleUploadResponse,
    CoverUploadResponse
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

@router.post("/{video_id}/subtitle", response_model=SubtitleUploadResponse)
async def upload_subtitle(
    video_id: int,
    subtitle: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传字幕文件
    
    功能：
    - 为视频上传字幕文件
    - 支持 SRT、VTT、JSON、ASS 格式
    - 更新视频的 subtitle_url 字段
    
    路径参数：
    - video_id: 视频ID
    
    请求体：
    - subtitle: 字幕文件（multipart/form-data）
    
    返回：
    - message: 提示信息
    - subtitle_url: 字幕文件URL
    - video_id: 视频ID
    
    需求：19.1, 19.2, 19.3
    """
    # 1. 检查视频是否存在且属于当前用户
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在"
        )
    
    # 只有视频上传者可以上传字幕
    if video.uploader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有视频上传者可以上传字幕"
        )
    
    # 2. 验证文件格式（只支持 SRT 和 VTT）
    file_extension = subtitle.filename.split('.')[-1].lower()
    if file_extension not in ['srt', 'vtt', 'json', 'ass']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="字幕格式不支持，仅支持 SRT、VTT、JSON、ASS 格式"
        )
    
    # 3. 创建字幕存储目录
    subtitle_dir = Path("uploads/subtitles")
    subtitle_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. 生成唯一文件名（避免冲突）
    unique_filename = f"{video_id}_subtitle_{uuid.uuid4().hex[:8]}.{file_extension}"
    subtitle_path = subtitle_dir / unique_filename
    
    # 5. 保存字幕文件
    try:
        content = await subtitle.read()
        with open(subtitle_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"保存字幕文件失败：{e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="字幕文件保存失败"
        )
    
    # 6. 更新视频的 subtitle_url 字段
    subtitle_url = f"/uploads/subtitles/{unique_filename}"
    video.subtitle_url = subtitle_url
    db.commit()
    
    logger.info(f"视频 {video_id} 字幕上传成功：{subtitle_url}")
    
    return SubtitleUploadResponse(
        message="字幕上传成功",
        subtitle_url=subtitle_url,
        video_id=video_id
    )


@router.post("/{video_id}/cover", response_model=CoverUploadResponse)
async def upload_cover(
    video_id: int,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传封面图片
    
    功能：
    - 为视频上传封面图片
    - 支持 JPG、PNG、WEBP 格式
    - 更新视频的 cover_url 字段
    
    路径参数：
    - video_id: 视频ID
    
    请求体：
    - cover: 封面图片文件（multipart/form-data）
    
    返回：
    - message: 提示信息
    - cover_url: 封面图片URL
    - video_id: 视频ID
    
    需求：任务9补充需求
    """
    # 1. 检查视频是否存在且属于当前用户
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在"
        )
    
    # 只有视频上传者可以上传封面
    if video.uploader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有视频上传者可以上传封面"
        )
    
    # 2. 验证文件格式（只支持 JPG、PNG、WEBP）
    file_extension = cover.filename.split('.')[-1].lower()
    if file_extension not in ['jpg', 'jpeg', 'png', 'webp']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="封面格式不支持，仅支持 JPG、PNG、WEBP 格式"
        )
    
    # 3. 验证文件大小（限制为 5MB）
    content = await cover.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="封面文件过大，最大支持 5MB"
        )
    
    # 4. 创建封面存储目录
    cover_dir = Path("uploads/covers")
    cover_dir.mkdir(parents=True, exist_ok=True)
    
    # 5. 生成唯一文件名（避免冲突）
    unique_filename = f"{video_id}_cover_{uuid.uuid4().hex[:8]}.{file_extension}"
    cover_path = cover_dir / unique_filename
    
    # 6. 保存封面文件
    try:
        with open(cover_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"保存封面文件失败：{e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="封面文件保存失败"
        )
    
    # 7. 更新视频的 cover_url 字段
    cover_url = f"/uploads/covers/{unique_filename}"
    video.cover_url = cover_url
    db.commit()
    
    logger.info(f"视频 {video_id} 封面上传成功：{cover_url}")
    
    return CoverUploadResponse(
        message="封面上传成功",
        cover_url=cover_url,
        video_id=video_id
    )    

