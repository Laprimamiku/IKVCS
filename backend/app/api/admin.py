"""
管理后台 API
功能：
1. 视频管理（列表、审核、封禁、恢复）
2. 用户管理（列表、封禁、解封）
3. 举报处理（视频 / 评论 / 弹幕）
4. 数据统计（概览、趋势、分类分布）
"""

import math
import logging
logger = logging.getLogger(__name__)

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from pydantic import BaseModel
from datetime import datetime, timedelta


from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.video import Video, Category
from app.models.user import User
from app.models.report import Report
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.schemas.user import UserResponse, MessageResponse
from app.schemas.video import (
    VideoListResponse, 
    AdminVideoListItemResponse, 
    AdminVideoListResponse,
    UploaderBriefResponse,
    CategoryBriefResponse
)
from app.services.video.video_stats_service import VideoStatsService
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()

# =========================
# Schema 定义
# =========================

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportHandleRequest(BaseModel):
    action: str  # delete_target | ignore
    admin_note: Optional[str] = None


class ReportItemResponse(BaseModel):
    id: int
    target_type: str
    target_id: int
    reason: str
    description: Optional[str]
    status: int
    created_at: datetime
    reporter: UserResponse

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    items: List[ReportItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatsOverviewResponse(BaseModel):
    total_users: int
    new_users_today: int
    total_videos: int
    new_videos_today: int
    total_reports_pending: int


class CategoryStatItem(BaseModel):
    name: str
    count: int


# ==================== 4. 分类管理 API (新增) ====================

@router.post("/categories", response_model=CategoryResponse, summary="创建分类")
async def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """创建新分类"""
    # 查重
    if CategoryRepository.get_by_name(db, category_in.name):
        raise HTTPException(
            status_code=400,
            detail=f"分类名称 '{category_in.name}' 已存在"
        )
    
    return CategoryRepository.create(db, category_in)

@router.put("/categories/{category_id}", response_model=CategoryResponse, summary="更新分类")
async def update_category(
    category_in: CategoryUpdate,
    category_id: int = Path(..., description="分类ID"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """更新分类信息"""
    category = CategoryRepository.get_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    # 如果要修改名称，需检查新名称是否与其他分类重复
    if category_in.name and category_in.name != category.name:
        if CategoryRepository.get_by_name(db, category_in.name):
            raise HTTPException(status_code=400, detail="新分类名称已存在")
            
    return CategoryRepository.update(db, category, category_in)

@router.delete("/categories/{category_id}", response_model=MessageResponse, summary="删除分类")
async def delete_category(
    category_id: int = Path(..., description="分类ID"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    删除分类
    注意：如果分类下还有视频，禁止删除
    """
    # 1. 检查是否存在
    if not CategoryRepository.get_by_id(db, category_id):
        raise HTTPException(status_code=404, detail="分类不存在")
    
    # 2. 检查是否有视频关联
    # 数据库定义了 ON DELETE RESTRICT，直接删除会报错
    # 所以我们需要先手动检查并给前端友好的提示
    if CategoryRepository.has_videos(db, category_id):
        raise HTTPException(
            status_code=400, 
            detail="该分类下仍有视频，无法删除。请先移动或删除相关视频。"
        )
    
    # 3. 执行删除
    CategoryRepository.delete(db, category_id)
    
    return MessageResponse(message="分类已删除")


# =========================
# 视频审核管理
# =========================

@router.get("/videos/pending", response_model=VideoListResponse, summary="获取待审核视频列表")
async def get_pending_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
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


@router.post("/videos/{video_id}/approve", response_model=MessageResponse, summary="通过视频审核")
async def approve_video(
    video_id: int = Path(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员通过视频审核
    
    使用场景：
    - 审核中的视频（包括被举报的视频）
    - 如果视频原本是已发布状态，保持已发布状态（status=2）
    - 如果视频原本是其他状态，设置为已发布（status=2）
    """
    from app.services.admin.video_admin_service import VideoAdminService
    return VideoAdminService.approve_video(db, video_id, admin)


@router.post("/videos/{video_id}/reject", response_model=MessageResponse, summary="拒绝视频审核")
async def reject_video(
    video_id: int = Path(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员拒绝视频审核
    
    使用场景：
    - 审核中的视频（包括被举报的视频）
    - 将视频状态设置为拒绝（status=3）
    """
    from app.services.admin.video_admin_service import VideoAdminService
    return VideoAdminService.reject_video(db, video_id, admin)


# =========================
# 视频管理
# =========================

@router.get("/videos/manage", response_model=AdminVideoListResponse, summary="视频管理列表")
async def manage_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    status: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
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
    import json
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
            subtitle_url=video.subtitle_url,  # 添加字幕 URL
            duration=video.duration,
            view_count=VideoStatsService.get_merged_view_count(db, video.id),
            like_count=video.like_count,
            collect_count=video.collect_count,
            danmaku_count=0,  # 可以后续添加
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


@router.post("/videos/{video_id}/ban", response_model=MessageResponse, summary="封禁视频")
async def ban_video(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    from app.services.admin.video_admin_service import VideoAdminService
    return VideoAdminService.ban_video(db, video_id)


@router.post("/videos/{video_id}/restore", response_model=MessageResponse, summary="恢复视频")
async def restore_video(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    from app.services.admin.video_admin_service import VideoAdminService
    return VideoAdminService.restore_video(db, video_id)


@router.post("/videos/{video_id}/re-review", summary="重新触发AI初审")
async def re_review_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员重新触发视频AI初审
    
    使用场景：
    - 视频被举报后，管理员可以重新触发AI审核
    - 审核结果会更新到 review_score, review_status, review_report 字段
    - 视频状态会根据审核结果自动更新
    """
    from app.services.ai.video_review_service import video_review_service
    from app.repositories.upload_repository import UploadSessionRepository
    import os
    from app.core.config import settings
    
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


@router.post("/videos/{video_id}/review-frames", summary="仅审核视频帧（Moondream）")
async def review_frames_only(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员仅触发视频帧审核（使用 Moondream）
    
    使用场景：
    - 仅需要重新审核视频帧时使用
    - 不会审核字幕
    """
    from app.services.ai.video_review_service import video_review_service
    from app.repositories.upload_repository import UploadSessionRepository
    import os
    from app.core.config import settings
    
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


@router.post("/videos/{video_id}/review-subtitle", summary="仅审核字幕（qwen2.5:0.5b-instruct）")
async def review_subtitle_only(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员仅触发字幕审核（使用 qwen2.5:0.5b-instruct）
    
    使用场景：
    - 仅需要重新审核字幕时使用
    - 不会审核视频帧
    
    注意：字幕文件可能被重命名，但文件名开头包含视频ID，会根据视频ID匹配字幕文件
    """
    from app.services.ai.video_review_service import video_review_service
    import os
    from app.core.config import settings
    from pathlib import Path
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    
    # 根据视频ID查找字幕文件（字幕文件可能被重命名，但开头包含视频ID）
    subtitle_path = None
    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    
    if os.path.exists(subtitle_dir):
        # 查找以 {video_id}_ 开头的字幕文件
        subtitle_files = list(Path(subtitle_dir).glob(f"{video_id}_*"))
        if subtitle_files:
            # 使用第一个匹配的文件
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
    return {
        "message": "字幕审核任务已启动（qwen2.5:0.5b-instruct），请稍后查看审核结果",
        "video_id": video_id
    }


@router.get("/videos/{video_id}/original", summary="获取原始视频文件 URL（用于人工审核）")
async def get_original_video_url(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    获取原始视频文件的访问 URL（用于管理员人工审核）
    
    返回原始视频文件路径，管理员可以直接下载或在线查看
    """
    from app.repositories.upload_repository import UploadSessionRepository
    import os
    from app.core.config import settings
    
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
    
    # 返回文件路径（前端可以通过 /videos/originals/ 访问，因为静态文件挂载在 /videos）
    # 注意：静态文件挂载在 /videos，所以路径应该是 /videos/originals/{file_name}
    # 文件名格式：{file_hash}_{file_name}，但显示时只显示原始文件名
    stored_file_name = f"{upload_session.file_hash}_{upload_session.file_name}"
    file_url = f"/videos/originals/{stored_file_name}"
    
    # 获取视频标题，用于显示（原始文件名可能与标题相似）
    display_name = video.title if video.title else upload_session.file_name
    
    return {
        "video_id": video_id,
        "file_path": input_path,
        "file_url": file_url,
        "file_name": upload_session.file_name,  # 原始文件名（不含哈希）
        "display_name": display_name,  # 显示名称（视频标题）
        "stored_file_name": stored_file_name,  # 存储的文件名（含哈希）
        "file_size": os.path.getsize(input_path) if os.path.exists(input_path) else 0
    }


@router.get("/videos/{video_id}/subtitle-content", summary="获取字幕内容（用于人工审核）")
async def get_subtitle_content(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    获取字幕文件内容（用于管理员人工审核）
    
    返回字幕文件的完整内容，支持 SRT/VTT/JSON/ASS 格式
    """
    from app.services.video.subtitle_parser import SubtitleParser
    import os
    from app.core.config import settings
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    
    # 根据视频ID查找字幕文件（字幕文件可能被重命名，但开头包含视频ID）
    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    full_path = None
    
    if os.path.exists(subtitle_dir):
        # 查找以 {video_id}_ 开头的字幕文件
        from pathlib import Path
        subtitle_files = list(Path(subtitle_dir).glob(f"{video_id}_*"))
        if subtitle_files:
            # 使用第一个匹配的文件
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
            "parsed_subtitles": subtitles,  # 解析后的字幕列表
            "raw_content": raw_content,  # 原始文件内容
            "total_entries": len(subtitles)
        }
    except Exception as e:
        logger.error(f"读取字幕文件失败: {e}", exc_info=True)
        raise HTTPException(500, f"读取字幕文件失败: {str(e)}")


# =========================
# 用户管理
# =========================

@router.get("/users", response_model=UserListResponse, summary="获取用户列表")
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    query = db.query(User)

    if keyword:
        query = query.filter(
            (User.username.like(f"%{keyword}%")) |
            (User.nickname.like(f"%{keyword}%"))
        )

    total = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(desc(User.created_at)).offset(offset).limit(page_size).all()

    return {
        "items": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


@router.post("/users/{user_id}/ban", response_model=MessageResponse, summary="封禁用户")
async def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    if user_id == admin.id:
        raise HTTPException(400, "不能封禁自己")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    user.status = 0
    db.commit()
    return {"message": f"用户 {user.username} 已被封禁"}


@router.post("/users/{user_id}/unban", response_model=MessageResponse, summary="解封用户")
async def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    user.status = 1
    db.commit()
    return {"message": f"用户 {user.username} 已解封"}


# =========================
# 举报管理
# =========================

@router.get("/reports", response_model=ReportListResponse, summary="获取举报列表")
async def get_reports(
    status: int = Query(0, description="0=待处理,1=已处理,2=已忽略"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    # 调用 Service 层获取举报列表
    from app.services.admin.admin_service import AdminService
    
    reports, total = AdminService.get_reports(db, status, page, page_size)
    
    return {
        "items": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


@router.post("/reports/{report_id}/handle", response_model=MessageResponse, summary="处理举报")
async def handle_report(
    data: ReportHandleRequest,
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    # 调用 Service 层处理举报逻辑
    from app.services.admin.admin_service import AdminService
    
    AdminService.handle_report(
        db, report_id, data.action, admin.id, data.admin_note
    )
    
    return {"message": "举报已处理"}


# =========================
# 数据统计
# =========================

@router.get("/statistics/overview", response_model=StatsOverviewResponse, summary="统计概览")
async def stats_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "total_users": db.query(User).count(),
        "new_users_today": db.query(User).filter(User.created_at >= today).count(),
        "total_videos": db.query(Video).filter(Video.status == 2).count(),
        "new_videos_today": db.query(Video).filter(Video.status == 2, Video.created_at >= today).count(),
        "total_reports_pending": db.query(Report).filter(Report.status == 0).count()
    }


@router.get("/statistics/trends", summary="趋势分析")
async def stats_trends(
    days: int = Query(7, le=30),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    users = db.query(User.created_at).filter(User.created_at >= start).all()
    videos = db.query(Video.created_at).filter(Video.created_at >= start).all()

    date_map = {
        (start + timedelta(days=i)).strftime("%Y-%m-%d"): {"user": 0, "video": 0}
        for i in range(days)
    }

    for u in users:
        d = u.created_at.strftime("%Y-%m-%d")
        if d in date_map:
            date_map[d]["user"] += 1

    for v in videos:
        d = v.created_at.strftime("%Y-%m-%d")
        if d in date_map:
            date_map[d]["video"] += 1

    return [
        {
            "date": d,
            "user_count": date_map[d]["user"],
            "video_count": date_map[d]["video"]
        }
        for d in sorted(date_map.keys())
    ]


@router.get("/statistics/categories", response_model=List[CategoryStatItem], summary="分类分布")
async def category_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    results = (
        db.query(Category.name, func.count(Video.id))
        .join(Video, Video.category_id == Category.id)
        .filter(Video.status == 2)
        .group_by(Category.id)
        .all()
    )
    return [{"name": name, "count": count} for name, count in results]



# =========================
# AI反馈式自我纠错管理
# =========================

from app.models.ai_correction import AiCorrection
from app.models.ai_prompt_version import AiPromptVersion
from app.services.ai.self_correction_service import self_correction_service
from pydantic import BaseModel

# Schema定义
class CorrectionCreateRequest(BaseModel):
    """创建修正记录请求"""
    content: str
    content_type: str  # "comment" 或 "danmaku"
    original_result: dict
    corrected_result: dict
    correction_reason: str


class CorrectionResponse(BaseModel):
    """修正记录响应"""
    id: int
    content: str
    content_type: str
    original_result: dict
    corrected_result: dict
    correction_reason: str
    corrected_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ErrorAnalysisRequest(BaseModel):
    """错误分析请求"""
    days: int = 7
    content_type: Optional[str] = None  # "comment", "danmaku" 或 None


class PromptUpdateRequest(BaseModel):
    """Prompt更新请求"""
    prompt_type: str  # "COMMENT" 或 "DANMAKU"
    new_prompt: str
    update_reason: str

class PromptRollbackRequest(BaseModel):
    """Prompt 回滚请求"""
    version_id: int

@router.post("/ai/corrections", response_model=CorrectionResponse, summary="提交AI修正记录")
async def create_correction(
    correction_in: CorrectionCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员提交AI分析修正记录"""
    try:
        correction = AiCorrection(
            content=correction_in.content,
            content_type=correction_in.content_type,
            original_result=correction_in.original_result,
            corrected_result=correction_in.corrected_result,
            correction_reason=correction_in.correction_reason,
            corrected_by=current_admin.id
        )
        
        db.add(correction)
        db.commit()
        db.refresh(correction)
        
        logger.info(f"管理员 {current_admin.username} 提交了AI修正记录: {correction.id}")
        
        return correction
        
    except Exception as e:
        logger.error(f"创建修正记录失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="创建修正记录失败")

@router.post("/ai/correct", response_model=CorrectionResponse, summary="提交AI修正记录 (Frontend Alias)")
async def submit_correction(
    correction_in: CorrectionCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Frontend alias for create_correction"""
    return await create_correction(correction_in, current_admin, db)


@router.get("/ai/corrections", summary="获取修正记录列表")
async def get_corrections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    content_type: Optional[str] = Query(None, description="内容类型过滤"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """获取AI修正记录列表"""
    try:
        query = db.query(AiCorrection)
        
        if content_type:
            query = query.filter(AiCorrection.content_type == content_type)
        
        total = query.count()
        offset = (page - 1) * page_size
        
        corrections = (
            query.order_by(AiCorrection.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        return {
            "items": corrections,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size)
        }
        
    except Exception as e:
        logger.error(f"获取修正记录失败: {e}")
        raise HTTPException(status_code=500, detail="获取修正记录失败")


@router.post("/ai/self-correction/analyze", summary="触发自我纠错分析")
async def trigger_self_correction_analysis(
    request: ErrorAnalysisRequest,
    current_admin: User = Depends(get_current_admin)
):
    """触发AI自我纠错分析"""
    try:
        logger.info(f"管理员 {current_admin.username} 触发自我纠错分析")
        
        result = await self_correction_service.analyze_errors(
            days=request.days,
            content_type=request.content_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"自我纠错分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/ai/self-correction/update-prompt", response_model=MessageResponse, summary="更新System Prompt")
async def update_system_prompt(
    request: PromptUpdateRequest,
    current_admin: User = Depends(get_current_admin)
):
    """应用优化建议，更新System Prompt"""
    try:
        success = await self_correction_service.update_system_prompt(
            prompt_type=request.prompt_type,
            new_prompt=request.new_prompt,
            update_reason=request.update_reason,
            updated_by=current_admin.id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Prompt更新失败")
        
        logger.info(f"管理员 {current_admin.username} 更新了 {request.prompt_type} Prompt")
        
        return MessageResponse(
            message=f"System Prompt已更新并记录版本历史。注意：需要手动更新prompts.py文件以生效。"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新System Prompt失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/ai/prompt-versions", summary="获取Prompt版本历史")
async def get_prompt_versions(
    prompt_type: Optional[str] = Query(None, description="Prompt类型过滤"),
    limit: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin)
):
    """查询Prompt版本历史"""
    try:
        versions = self_correction_service.get_prompt_history(
            prompt_type=prompt_type,
            limit=limit
        )
        
        return {
            "items": versions,
            "total": len(versions)
        }
        
    except Exception as e:
        logger.error(f"获取Prompt版本历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取版本历史失败")

@router.post("/ai/prompts/rollback", summary="回滚Prompt版本")
async def rollback_prompt(
    request: PromptRollbackRequest,
    current_admin: User = Depends(get_current_admin)
):
    """回滚到指定Prompt版本"""
    try:
        success = await self_correction_service.rollback_prompt(
            version_id=request.version_id,
            rollback_by=current_admin.id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="版本不存在或回滚失败")
        
        logger.info(
            f"[Admin] 管理员 {current_admin.username} 回滚Prompt到版本 {request.version_id}"
        )
        
        return {"message": "Prompt 已回滚"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] 回滚Prompt失败: {e}")
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


@router.get("/ai/config", summary="获取AI系统配置")
async def get_ai_config(
    current_admin: User = Depends(get_current_admin)
):
    """获取AI系统当前配置"""
    from app.core.config import settings
    
    return {
        "local_llm": {
            "enabled": settings.LOCAL_LLM_ENABLED,
            "model": settings.LOCAL_LLM_MODEL,
            "threshold_high": settings.LOCAL_LLM_THRESHOLD_HIGH,
            "threshold_low": settings.LOCAL_LLM_THRESHOLD_LOW
        },
        "multi_agent": {
            "enabled": settings.MULTI_AGENT_ENABLED,
            "conflict_threshold": settings.MULTI_AGENT_CONFLICT_THRESHOLD
        },
        "self_correction": {
            "enabled": settings.SELF_CORRECTION_ENABLED,
            "min_samples": settings.SELF_CORRECTION_MIN_SAMPLES,
            "auto_update": settings.SELF_CORRECTION_AUTO_UPDATE,
            "analysis_days": settings.SELF_CORRECTION_ANALYSIS_DAYS
        }
    }