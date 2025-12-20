"""
管理后台 API
功能：
1. 视频管理（列表、审核、封禁、恢复）
2. 用户管理（列表、封禁、解封）
3. 举报处理（视频 / 评论 / 弹幕）
4. 数据统计（概览、趋势、分类分布）
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from pydantic import BaseModel
from datetime import datetime, timedelta
import math

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.video import Video, Category
from app.models.user import User
from app.models.report import Report
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.schemas.user import UserResponse, MessageResponse
from app.schemas.video import VideoListResponse
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
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")

    video.status = 2  # 已发布
    db.commit()
    return {"message": "视频已通过审核"}


@router.post("/videos/{video_id}/reject", response_model=MessageResponse, summary="拒绝视频审核")
async def reject_video(
    video_id: int = Path(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")

    video.status = 3  # 拒绝 / 封禁
    db.commit()
    return {"message": "视频已被拒绝"}


# =========================
# 视频管理
# =========================

@router.get("/videos/manage", response_model=VideoListResponse, summary="视频管理列表")
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

    return {
        "items": videos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


@router.post("/videos/{video_id}/ban", response_model=MessageResponse, summary="封禁视频")
async def ban_video(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")

    video.status = 3
    db.commit()
    return {"message": "视频已封禁"}


@router.post("/videos/{video_id}/restore", response_model=MessageResponse, summary="恢复视频")
async def restore_video(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")

    video.status = 2
    db.commit()
    return {"message": "视频已恢复发布"}


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
    query = db.query(Report).filter(Report.status == status)
    total = query.count()
    offset = (page - 1) * page_size

    reports = (
        query.options(joinedload(Report.reporter))
        .order_by(desc(Report.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

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
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "举报不存在")

    if data.action == "delete_target":
        if report.target_type == "VIDEO":
            video = db.query(Video).filter(Video.id == report.target_id).first()
            if video:
                video.status = 4
        elif report.target_type == "COMMENT":
            comment = db.query(Comment).filter(Comment.id == report.target_id).first()
            if comment:
                comment.is_deleted = True
        elif report.target_type == "DANMAKU":
            danmaku = db.query(Danmaku).filter(Danmaku.id == report.target_id).first()
            if danmaku:
                danmaku.is_deleted = True

        report.status = 1
        report.admin_note = data.admin_note or "管理员删除了违规内容"

    elif data.action == "ignore":
        report.status = 2
        report.admin_note = data.admin_note or "管理员判定无违规"
    else:
        raise HTTPException(400, "无效操作")

    report.handler_id = admin.id
    report.handled_at = datetime.utcnow()
    db.commit()
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
# AI反馈式自我纠错管理 (新增)
# =========================

from app.models.ai_correction import AICorrection, AIPromptVersion
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


@router.post("/ai/corrections", response_model=CorrectionResponse, summary="提交AI修正记录")
async def create_correction(
    correction_in: CorrectionCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员提交AI分析修正记录"""
    try:
        correction = AICorrection(
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
        query = db.query(AICorrection)
        
        if content_type:
            query = query.filter(AICorrection.content_type == content_type)
        
        total = query.count()
        offset = (page - 1) * page_size
        
        corrections = (
            query.order_by(AICorrection.created_at.desc())
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
        versions = self_correction_service.get_prompt_versions(
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
