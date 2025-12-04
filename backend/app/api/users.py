"""
用户信息管理 API
需求：2.1, 2.2, 2.3
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import os
import uuid
from pathlib import Path

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest, MessageResponse

router = APIRouter()

# 头像上传目录
AVATAR_UPLOAD_DIR = Path("uploads/avatars")
AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户信息
    
    需求：2.1 - 当用户请求个人信息时，系统应当返回当前用户的昵称、头像、简介等信息
    
    流程：
    1. 通过 JWT 令牌验证用户身份（get_current_user 依赖）
    2. 返回用户信息
    
    返回：
    - 用户完整信息（不包含密码哈希）
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user_info(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    
    需求：2.2 - 当用户更新个人信息时，系统应当验证数据格式并保存更改
    
    流程：
    1. 验证用户身份和状态
    2. 更新用户信息（只更新提供的字段）
    3. 保存到数据库
    4. 返回更新后的用户信息
    
    参数：
    - nickname: 昵称（可选）
    - intro: 个人简介（可选）
    
    返回：
    - 更新后的用户信息
    """
    # 更新字段（只更新非 None 的字段）
    if user_update.nickname is not None:
        current_user.nickname = user_update.nickname
    
    if user_update.intro is not None:
        current_user.intro = user_update.intro
    
    # 保存到数据库
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/me/avatar", response_model=dict)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    上传用户头像
    
    需求：2.2 - 实现头像上传功能
    
    流程：
    1. 验证文件类型（只允许图片）
    2. 验证文件大小（不超过 2MB）
    3. 生成唯一文件名
    4. 保存文件到服务器
    5. 更新用户头像 URL
    6. 返回头像 URL
    
    参数：
    - file: 图片文件
    
    返回：
    - avatar_url: 头像访问地址
    """
    # 验证文件类型
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能上传图片文件"
        )
    
    # 验证文件大小（2MB）
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片大小不能超过 2MB"
        )
    
    # 生成唯一文件名
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = AVATAR_UPLOAD_DIR / unique_filename
    
    # 保存文件
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # 更新用户头像 URL（返回完整的访问路径）
    avatar_url = f"/uploads/avatars/{unique_filename}"
    current_user.avatar = avatar_url
    db.commit()
    db.refresh(current_user)
    
    return {
        "avatar_url": avatar_url,
        "message": "头像上传成功"
    }


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定用户信息（他人主页）
    
    需求：2.3 - 当用户查看他人主页时，系统应当返回该用户的公开信息（不包含敏感数据）
    
    流程：
    1. 根据用户 ID 查询用户
    2. 返回用户公开信息
    
    参数：
    - user_id: 用户 ID
    
    返回：
    - 用户公开信息
    
    注意：
    - 不需要登录即可访问
    - 返回的信息不包含敏感数据（密码哈希等）
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user
