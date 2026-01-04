"""
用户服务层
封装用户相关的业务逻辑
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from pathlib import Path
import os
import uuid

from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.schemas.user import UserUpdateRequest
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundException


class UserService:
    """用户服务"""
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """
        根据用户ID获取用户信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            User: 用户对象
            
        Raises:
            ResourceNotFoundException: 用户不存在
        """
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise ResourceNotFoundException(resource="用户", resource_id=user_id)
        return user
    
    @staticmethod
    def update_user_info(
        db: Session,
        user: User,
        user_update: UserUpdateRequest
    ) -> User:
        """
        更新用户信息
        
        Args:
            db: 数据库会话
            user: 当前用户对象
            user_update: 更新数据
            
        Returns:
            User: 更新后的用户对象
        """
        # 更新字段（只更新非 None 的字段）
        update_data = {}
        if user_update.nickname is not None:
            update_data["nickname"] = user_update.nickname
        if user_update.intro is not None:
            update_data["intro"] = user_update.intro
        
        if update_data:
            UserRepository.update(db, user.id, update_data)
            db.refresh(user)
        
        return user
    
    @staticmethod
    async def upload_avatar(
        db: Session,
        user: User,
        file: UploadFile
    ) -> str:
        """
        上传用户头像
        
        Args:
            db: 数据库会话
            user: 当前用户对象
            file: 上传的文件
            
        Returns:
            str: 头像访问路径
            
        Raises:
            HTTPException: 文件类型或大小不符合要求
        """
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
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
        
        # 确保上传目录存在
        avatar_upload_dir = Path(settings.UPLOAD_AVATAR_DIR)
        avatar_upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名
        file_ext = os.path.splitext(file.filename or "")[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = avatar_upload_dir / unique_filename
        
        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # 更新用户头像 URL（返回完整的访问路径）
        avatar_url = f"/uploads/avatars/{unique_filename}"
        UserRepository.update(db, user.id, {"avatar": avatar_url})
        db.refresh(user)
        
        return avatar_url




















