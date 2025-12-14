# backend/app/api/interactions.py

# [修改 1] 引入 status
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.interaction import UserLike, UserCollection
from app.models.video import Video

# [修改 2] 引入 ReportCreate
from app.schemas.interaction import (
    LikeCreate, LikeStatus, 
    CollectionCreate, CollectionStatus, CollectionResponse,
    ReportCreate 
)
# [修改 3] 引入 MessageResponse (通常在 user schema 中)
from app.schemas.user import MessageResponse

from app.services.cache.redis_service import redis_service

# [修改 4] 引入 ReportRepository
from app.repositories.report_repository import ReportRepository

router = APIRouter()

# ==================== 第一步：点赞功能 (Redis + 异步同步) ====================

@router.post("/likes", response_model=LikeStatus)
async def like_target(
    like_in: LikeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """点赞"""
    # 1. 写入 Redis
    await redis_service.add_like(current_user.id, like_in.target_type, like_in.target_id)
    
    # 2. 获取最新数量
    count = await redis_service.get_like_count(like_in.target_type, like_in.target_id)
    
    return {"is_liked": True, "like_count": count}

@router.delete("/likes", response_model=LikeStatus)
async def unlike_target(
    target_id: int,
    target_type: str, 
    current_user: User = Depends(get_current_user)
):
    """取消点赞"""
    # 1. 移除 Redis
    await redis_service.remove_like(current_user.id, target_type, target_id)
    
    # 2. 获取最新数量
    count = await redis_service.get_like_count(target_type, target_id)
    
    return {"is_liked": False, "like_count": count}


# ==================== 第二步：收藏功能 (直接读写 DB) ====================

@router.post("/collections", response_model=CollectionStatus)
def collect_video(
    data: CollectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """收藏视频"""
    # 1. 查重
    exists = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id,
        UserCollection.video_id == data.video_id
    ).first()
    
    if exists:
        return {"is_collected": True}
        
    # 2. 创建记录
    new_collection = UserCollection(user_id=current_user.id, video_id=data.video_id)
    db.add(new_collection)
    
    # 3. 同步增加视频收藏数
    db.query(Video).filter(Video.id == data.video_id).update(
        {Video.collect_count: Video.collect_count + 1}
    )
    
    db.commit()
    return {"is_collected": True}

@router.delete("/collections", response_model=CollectionStatus)
def uncollect_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消收藏"""
    record = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id,
        UserCollection.video_id == video_id
    ).first()
    
    if record:
        db.delete(record)
        # 同步减少视频收藏数
        db.query(Video).filter(Video.id == video_id).update(
            {Video.collect_count: Video.collect_count - 1}
        )
        db.commit()
        
    return {"is_collected": False}

@router.get("/collections", response_model=List[CollectionResponse])
def get_my_collections(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的收藏列表"""
    skip = (page - 1) * page_size
    
    collections = db.query(UserCollection)\
        .filter(UserCollection.user_id == current_user.id)\
        .order_by(UserCollection.created_at.desc())\
        .offset(skip).limit(page_size).all()
        
    return collections

# ==================== 第三步：举报功能 (新增) ====================

@router.post("/reports", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, summary="提交举报")
def create_report(
    report_in: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    提交举报信息
    
    举报对象可以是：
    - VIDEO: 视频
    - COMMENT: 评论
    - DANMAKU: 弹幕
    
    提交后会进入管理员后台待处理队列
    """
    # 1. 检查是否重复举报（可选）
    if ReportRepository.exists(db, current_user.id, report_in.target_type, report_in.target_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="您已经举报过该内容，请耐心等待管理员处理"
        )

    # 2. 验证目标是否存在（可选，为了性能可以跳过，交给管理员审核时发现）
    # 如果要验证，需要根据 target_type 查询不同的表
    
    # 3. 创建举报记录
    ReportRepository.create(db, report_in, current_user.id)
    
    return MessageResponse(message="举报提交成功，我们会尽快处理")