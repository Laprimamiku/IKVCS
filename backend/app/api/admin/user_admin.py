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

