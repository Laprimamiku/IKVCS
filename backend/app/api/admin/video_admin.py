"""
视频管理 API（管理员）
功能：视频审核、封禁、恢复、管理列表、AI审核相关
"""
import math
import json
import logging
import os
from typing import Optional
from pathlib import Path as PathLib
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.core.config import settings
from app.models.user import User
from app.models.video import Video
from app.schemas.user import MessageResponse
from app.schemas.video import (
    VideoListResponse,
    AdminVideoListItemResponse,
    AdminVideoListResponse,
    UploaderBriefResponse,
    CategoryBriefResponse
)
from app.services.admin.video_admin_service import VideoAdminService
from app.services.video.video_stats_service import VideoStatsService
from app.services.ai.video_review_service import video_review_service
from app.repositories.upload_repository import UploadSessionRepository
from app.services.video.subtitle_parser import SubtitleParser

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pending", response_model=VideoListResponse, summary="获取待审核视频列表")
async def get_pending_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取待审核视频列表（status=1）"""
    query = db.query(Video).filter(Video.status == 1)
    total = query.count()
    offset = (page - 1) * page_size

    videos = (
        query.options(joinedload(Video.uploader), joinedload(Video.category))
        .order_by(desc(Video.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "items": videos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


@router.post("/{video_id}/approve", response_model=MessageResponse, summary="通过视频审核")
async def approve_video(
    video_id: int = Path(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员通过视频审核"""
    return VideoAdminService.approve_video(db, video_id, admin)


@router.post("/{video_id}/reject", response_model=MessageResponse, summary="拒绝视频审核")
async def reject_video(
    video_id: int = Path(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员拒绝视频审核"""
    return VideoAdminService.reject_video(db, video_id, admin)


@router.get("/manage", response_model=AdminVideoListResponse, summary="视频管理列表")
async def manage_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    status: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """视频管理列表（支持筛选）"""
    query = db.query(Video)

    if status is not None:
        query = query.filter(Video.status == status)
    if keyword:
        query = query.filter(Video.title.like(f"%{keyword}%"))

    total = query.count()
    offset = (page - 1) * page_size

    videos = (
        query.options(joinedload(Video.uploader), joinedload(Video.category))
        .order_by(desc(Video.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # 构建包含审核信息的响应
    items = []
    for video in videos:
        # 解析 review_report JSON 字符串
        review_report_dict = None
        if video.review_report:
            try:
                if isinstance(video.review_report, str):
                    review_report_dict = json.loads(video.review_report)
                else:
                    review_report_dict = video.review_report
            except (json.JSONDecodeError, TypeError):
                review_report_dict = None
        
        items.append(AdminVideoListItemResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            cover_url=video.cover_url,
            video_url=video.video_url or "",
            subtitle_url=video.subtitle_url,
            duration=video.duration,
            view_count=VideoStatsService.get_merged_view_count(db, video.id),
            like_count=video.like_count,
            collect_count=video.collect_count,
            danmaku_count=0,
            uploader=UploaderBriefResponse(
                id=video.uploader.id,
                username=video.uploader.username,
                nickname=video.uploader.nickname,
                avatar=video.uploader.avatar,
            ),
            category=CategoryBriefResponse(
                id=video.category.id,
                name=video.category.name
            ),
            created_at=video.created_at,
            status=video.status,
            review_score=video.review_score,
            review_status=video.review_status,
            review_report=review_report_dict,
        ))

    return AdminVideoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size)
    )


@router.post("/{video_id}/ban", response_model=MessageResponse, summary="封禁视频")
async def ban_video(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """封禁视频"""
    return VideoAdminService.ban_video(db, video_id)


@router.post("/{video_id}/restore", response_model=MessageResponse, summary="恢复视频")
async def restore_video(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """恢复视频发布"""
    return VideoAdminService.restore_video(db, video_id)


@router.post("/{video_id}/re-review", summary="重新触发AI初审")
async def re_review_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员重新触发视频AI初审（帧+字幕）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    
    # 获取视频文件路径
    upload_session = UploadSessionRepository.get_by_video_id(db, video_id)
    if not upload_session:
        raise HTTPException(404, "视频文件不存在")
    
    input_path = os.path.join(
        settings.VIDEO_ORIGINAL_DIR,
        f"{upload_session.file_hash}_{upload_session.file_name}"
    )
    
    if not os.path.exists(input_path):
        raise HTTPException(404, "视频文件不存在")
    
    # 获取字幕路径
    subtitle_path = video.subtitle_url if video.subtitle_url else None
    if subtitle_path and not os.path.isabs(subtitle_path):
        subtitle_path = os.path.join(settings.STORAGE_ROOT, subtitle_path.lstrip("/"))
    
    # 异步触发审核任务
    background_tasks.add_task(
        video_review_service.review_video,
        video_id=video_id,
        video_path=input_path,
        subtitle_path=subtitle_path
    )
    
    logger.info(f"管理员 {admin.username} 重新触发视频AI初审（帧+字幕）: video_id={video_id}")
    
    return {
        "message": "AI初审任务已启动（帧审核+字幕审核），请稍后查看审核结果",
        "video_id": video_id
    }


@router.post("/{video_id}/review-frames", summary="仅审核视频帧（云端/本地模型）")
async def review_frames_only(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员仅触发视频帧审核（使用 Moondream）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    
    # 获取视频文件路径
    upload_session = UploadSessionRepository.get_by_video_id(db, video_id)
    if not upload_session:
        raise HTTPException(404, "视频文件不存在")
    
    input_path = os.path.join(
        settings.VIDEO_ORIGINAL_DIR,
        f"{upload_session.file_hash}_{upload_session.file_name}"
    )
    
    if not os.path.exists(input_path):
        raise HTTPException(404, "视频文件不存在")
    
    # 异步触发帧审核（后台任务）
    background_tasks.add_task(
        video_review_service.review_frames_only,
        video_id=video_id,
        video_path=input_path
    )
    
    logger.info(f"管理员 {admin.username} 触发视频帧审核: video_id={video_id}")
    return {
        "message": "帧审核任务已启动（Moondream），请稍后查看审核结果",
        "video_id": video_id
    }


@router.post("/{video_id}/review-subtitle", summary="仅审核字幕（云端/本地模型）")
async def review_subtitle_only(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员仅触发字幕审核（使用 qwen2.5:0.5b-instruct）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    
    # 根据视频ID查找字幕文件
    subtitle_path = None
    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    
    if os.path.exists(subtitle_dir):
        # 查找以 {video_id}_ 开头的字幕文件
        subtitle_files = list(PathLib(subtitle_dir).glob(f"{video_id}_*"))
        if subtitle_files:
            subtitle_path = str(subtitle_files[0])
            logger.info(f"根据视频ID找到字幕文件: video_id={video_id}, subtitle_path={subtitle_path}")
        else:
            # 如果没有找到，尝试使用 video.subtitle_url
            if video.subtitle_url:
                subtitle_path = video.subtitle_url
                if not os.path.isabs(subtitle_path):
                    if subtitle_path.startswith("/"):
                        subtitle_path = os.path.join(settings.STORAGE_ROOT, subtitle_path.lstrip("/"))
                    else:
                        subtitle_path = os.path.join(subtitle_dir, subtitle_path)
                logger.info(f"使用视频记录中的字幕路径: video_id={video_id}, subtitle_path={subtitle_path}")
            else:
                logger.warning(f"未找到视频对应的字幕文件: video_id={video_id}, subtitle_dir={subtitle_dir}")
    else:
        logger.warning(f"字幕目录不存在: {subtitle_dir}")
    
    # 异步触发字幕审核（后台任务）
    background_tasks.add_task(
        video_review_service.review_subtitle_only,
        video_id=video_id,
        subtitle_path=subtitle_path
    )
    
    logger.info(f"管理员 {admin.username} 触发字幕审核: video_id={video_id}, subtitle_path={subtitle_path}")
    model_info = f"云端模型({settings.LLM_MODEL})" if settings.USE_CLOUD_LLM else "本地模型(qwen2.5:0.5b-instruct)"
    return {
        "message": f"字幕审核任务已启动（{model_info}），请稍后查看审核结果",
        "video_id": video_id
    }


@router.get("/{video_id}/original", summary="获取原始视频文件 URL（用于人工审核）")
async def get_original_video_url(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取原始视频文件的访问 URL（用于管理员人工审核）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    
    # 获取视频文件路径
    upload_session = UploadSessionRepository.get_by_video_id(db, video_id)
    if not upload_session:
        raise HTTPException(404, "视频文件不存在")
    
    input_path = os.path.join(
        settings.VIDEO_ORIGINAL_DIR,
        f"{upload_session.file_hash}_{upload_session.file_name}"
    )
    
    if not os.path.exists(input_path):
        raise HTTPException(404, "视频文件不存在")
    
    # 返回文件路径
    stored_file_name = f"{upload_session.file_hash}_{upload_session.file_name}"
    file_url = f"/videos/originals/{stored_file_name}"
    display_name = video.title if video.title else upload_session.file_name
    
    return {
        "video_id": video_id,
        "file_path": input_path,
        "file_url": file_url,
        "file_name": upload_session.file_name,
        "display_name": display_name,
        "stored_file_name": stored_file_name,
        "file_size": os.path.getsize(input_path) if os.path.exists(input_path) else 0
    }


@router.get("/{video_id}/subtitle-content", summary="获取字幕内容（用于人工审核）")
async def get_subtitle_content(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取字幕文件内容（用于管理员人工审核）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    
    # 根据视频ID查找字幕文件
    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    full_path = None
    
    if os.path.exists(subtitle_dir):
        # 查找以 {video_id}_ 开头的字幕文件
        subtitle_files = list(PathLib(subtitle_dir).glob(f"{video_id}_*"))
        if subtitle_files:
            full_path = str(subtitle_files[0])
            logger.info(f"根据视频ID找到字幕文件: video_id={video_id}, subtitle_path={full_path}")
        else:
            # 如果没有找到，尝试使用 video.subtitle_url
            if video.subtitle_url:
                subtitle_path = video.subtitle_url
                if os.path.isabs(subtitle_path):
                    full_path = subtitle_path
                elif subtitle_path.startswith("/"):
                    full_path = os.path.join(settings.STORAGE_ROOT, subtitle_path.lstrip("/"))
                else:
                    full_path = os.path.join(subtitle_dir, subtitle_path)
                logger.info(f"使用视频记录中的字幕路径: video_id={video_id}, subtitle_path={full_path}")
    
    if not full_path or not os.path.exists(full_path):
        raise HTTPException(404, f"该视频没有字幕文件（video_id={video_id}，已搜索目录：{subtitle_dir}）")
    
    # 解析字幕文件
    try:
        parser = SubtitleParser()
        subtitles = parser.parse_subtitle_file(full_path)
        
        # 读取原始文件内容（用于显示）
        with open(full_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        return {
            "video_id": video_id,
            "subtitle_url": video.subtitle_url,
            "file_path": full_path,
            "file_name": os.path.basename(full_path),
            "parsed_subtitles": subtitles,
            "raw_content": raw_content,
            "total_entries": len(subtitles)
        }
    except Exception as e:
        logger.error(f"读取字幕文件失败: {e}", exc_info=True)
        raise HTTPException(500, f"读取字幕文件失败: {str(e)}")

