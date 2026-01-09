"""
用户管理 API（管理员）
功能：用户列表、封禁、解封
"""
import math
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.schemas.user import UserResponse, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=UserListResponse, summary="获取用户列表")
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取用户列表（支持关键词搜索）"""
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


@router.post("/{user_id}/ban", response_model=MessageResponse, summary="封禁用户")
async def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """封禁用户"""
    if user_id == admin.id:
        raise HTTPException(400, "不能封禁自己")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    user.status = 0
    db.commit()
    return {"message": f"用户 {user.username} 已被封禁"}


@router.post("/{user_id}/unban", response_model=MessageResponse, summary="解封用户")
async def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """解封用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    user.status = 1
    db.commit()
    return {"message": f"用户 {user.username} 已解封"}


class UserDetailResponse(UserResponse):
    """用户详情响应（包含行为统计）"""
    video_count: int = 0  # 上传视频数
    watch_count: int = 0  # 观看视频数
    like_count: int = 0  # 点赞数
    collect_count: int = 0  # 收藏数
    comment_count: int = 0  # 评论数


@router.get("/{user_id}", response_model=UserDetailResponse, summary="获取用户详情")
async def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取用户详情（包含行为统计）"""
    from app.models.video import Video
    from app.models.watch_history import WatchHistory
    from app.models.interaction import UserLike, UserCollection
    from app.models.comment import Comment
    from sqlalchemy import func
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    
    # 统计用户行为
    video_count = db.query(func.count(Video.id)).filter(Video.uploader_id == user_id).scalar() or 0
    watch_count = db.query(func.count(WatchHistory.id)).filter(WatchHistory.user_id == user_id).scalar() or 0
    like_count = db.query(func.count(UserLike.id)).filter(UserLike.user_id == user_id).scalar() or 0
    collect_count = db.query(func.count(UserCollection.id)).filter(UserCollection.user_id == user_id).scalar() or 0
    comment_count = db.query(func.count(Comment.id)).filter(Comment.user_id == user_id).scalar() or 0
    
    # 构建响应
    user_dict = {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "avatar": user.avatar,
        "status": user.status,
        "created_at": user.created_at,
        "video_count": video_count,
        "watch_count": watch_count,
        "like_count": like_count,
        "collect_count": collect_count,
        "comment_count": comment_count
    }
    
    return UserDetailResponse(**user_dict)

