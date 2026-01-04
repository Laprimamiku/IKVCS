"""
视频查询 API

功能：
1. 获取视频列表（已发布）
2. 获取我的视频列表
3. 获取视频详情（并增加播放量）
4. 查询视频状态（开发调试）
5. 增加播放量（公开）
6. 获取视频大纲、摘要、知识点
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, ForbiddenException
from app.core.response import success_response
from app.models.user import User
from app.schemas.video import (
    VideoListResponse,
    VideoDetailResponse,
    VideoStatusResponse,
)
from app.services.video import (
    VideoStatsService,
    VideoResponseBuilder,
)
from app.repositories.video_repository import VideoRepository
from app.models.video import Video

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=VideoListResponse)
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
    return VideoResponseBuilder.get_video_list_response(
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
    return VideoResponseBuilder.get_user_video_list_response(
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
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    获取视频详情并增加播放量
    
    权限说明：
    - 已发布的视频（status=2）：所有用户都可以查看
    - 非发布状态的视频：只有上传者和管理员可以查看
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    # 先获取视频基本信息，用于权限检查
    video = VideoRepository.get_by_id(db, video_id)
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 权限检查：非发布状态的视频，只有上传者和管理员可以查看
    if video.status != 2:  # 非已发布状态
        if not current_user:
            raise ForbiddenException("该视频正在审核中，请登录后查看")
        if current_user.id != video.uploader_id and current_user.role != "admin":
            raise ForbiddenException("该视频正在审核中，只有上传者和管理员可以查看")
    
    # 增加播放量（仅对已发布的视频）
    if video.status == 2:
        VideoStatsService.increment_view_count(db, video_id)
    
    # 如果用户已登录，记录观看历史
    if current_user:
        from app.repositories.watch_history_repository import WatchHistoryRepository
        try:
            WatchHistoryRepository.record_watch(db, current_user.id, video_id)
        except Exception as e:
            logger.warning(f"记录观看历史失败: {e}")
    
    # 获取视频详情响应（包含所有数据组装逻辑）
    video_detail = VideoResponseBuilder.get_video_detail_response(db, video_id)
    if not video_detail:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return video_detail


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询视频状态（开发/调试专用接口）
    
    注意：此接口仅用于开发和调试，生产环境应通过视频详情接口获取状态
    """
    from app.services.video.video_status_service import VideoStatusService
    
    status_info = VideoStatusService.get_video_status(db, video_id)
    return VideoStatusResponse(**status_info)


@router.post("/{video_id}/view")
async def increase_view_count(
    video_id: int,
    db: Session = Depends(get_db),
):
    """增加视频播放量（公开接口）"""
    success = VideoStatsService.increment_view_count(db, video_id)
    if not success:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    view_count = VideoStatsService.get_merged_view_count(db, video_id)
    return success_response(
        data={"view_count": view_count},
        message="播放量已记录"
    )


@router.get("/{video_id}/outline", response_model=dict)
async def get_video_outline(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    获取视频内容大纲
    
    注意：此接口只返回已有的大纲，不会自动生成
    如需生成大纲，请使用 POST /videos/{video_id}/outline/generate
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 如果已有大纲，直接返回
    if video.outline:
        try:
            outline_data = json.loads(video.outline)
            return success_response(
                data={"outline": outline_data},
                message="获取大纲成功"
            )
        except:
            pass
    
    # 如果没有大纲，返回空列表（不自动生成）
    return success_response(
        data={"outline": []},
        message="暂无大纲"
    )


@router.get("/{video_id}/outline/progress", response_model=dict)
async def get_outline_progress(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    获取大纲生成进度
    """
    from app.core.redis import get_redis
    redis_client = get_redis()
    progress_key = f"outline:progress:{video_id}"
    
    progress_data = redis_client.get(progress_key)
    if progress_data:
        try:
            data = json.loads(progress_data)
            return success_response(
                data=data,
                message="获取进度成功"
            )
        except:
            pass
    
    return success_response(
        data={"progress": 0, "message": "未找到进度信息", "status": "unknown"},
        message="获取进度成功"
    )


@router.get("/{video_id}/summary", summary="获取视频摘要")
async def get_video_summary(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    获取视频摘要（简短摘要和详细摘要）
    
    如果摘要不存在，返回空字符串
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 从独立字段获取摘要
    return success_response(
        data={
            "summary_short": video.summary_short or "",
            "summary_detailed": video.summary_detailed or ""
        }
    )


@router.get("/{video_id}/knowledge", summary="获取核心知识点")
async def get_video_knowledge(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    获取视频核心知识点
    
    返回：概念、步骤、数据、观点
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 从独立字段获取知识点
    knowledge_points = video.knowledge_points or {
        "concepts": [],
        "steps": [],
        "data": [],
        "opinions": []
    }
    
    return success_response(
        data={
            "knowledge_points": knowledge_points
        }
    )

