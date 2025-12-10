"""
用户 Repository
提供用户相关的数据访问方法
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.core.repository import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository):
    """用户 Repository"""
    model = User
    
    @classmethod
    def get_by_username(
        cls,
        db: Session,
        username: str
    ) -> Optional[User]:
        """
        根据用户名查询用户
        
        Args:
            db: 数据库会话
            username: 用户名
            
        Returns:
            Optional[User]: 用户对象，不存在返回None
        """
        return db.query(User).filter(User.username == username).first()
    
    @classmethod
    def get_by_email(
        cls,
        db: Session,
        email: str
    ) -> Optional[User]:
        """
        根据邮箱查询用户
        
        Args:
            db: 数据库会话
            email: 邮箱
            
        Returns:
            Optional[User]: 用户对象，不存在返回None
        """
        return db.query(User).filter(User.email == email).first()
    
    @classmethod
    def username_exists(
        cls,
        db: Session,
        username: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查用户名是否存在
        
        Args:
            db: 数据库会话
            username: 用户名
            exclude_id: 排除的用户ID（用于更新时检查）
            
        Returns:
            bool: 是否存在
        """
        query = db.query(User).filter(User.username == username)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None
    
    @classmethod
    def email_exists(
        cls,
        db: Session,
        email: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查邮箱是否存在
        
        Args:
            db: 数据库会话
            email: 邮箱
            exclude_id: 排除的用户ID（用于更新时检查）
            
        Returns:
            bool: 是否存在
        """
        query = db.query(User).filter(User.email == email)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None

