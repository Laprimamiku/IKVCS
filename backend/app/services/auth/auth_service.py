"""
认证服务
职责：处理用户登录、注册、登出等认证相关业务逻辑
"""
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status

from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.schemas.user import UserRegisterRequest, UserLoginRequest
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.exceptions import ValidationException


class AuthService:
    """认证服务"""
    
    @staticmethod
    def register_user(db: Session, user_data: UserRegisterRequest) -> User:
        """
        用户注册
        
        Args:
            db: 数据库会话
            user_data: 注册数据
            
        Returns:
            User: 创建的用户对象
            
        Raises:
            ValidationException: 用户名已存在
        """
        # 1. 检查用户名是否已存在
        existing_user = UserRepository.get_by_username(db, user_data.username)
        if existing_user:
            raise ValidationException(message="用户名已存在")
        
        # 2. 创建新用户
        new_user = User(
            username=user_data.username,
            password_hash=get_password_hash(user_data.password),
            nickname=user_data.nickname,
            role="user",
            status=1
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def login_user(db: Session, login_data: UserLoginRequest) -> tuple[str, User]:
        """
        用户登录
        
        Args:
            db: 数据库会话
            login_data: 登录数据
            
        Returns:
            tuple[str, User]: (JWT令牌, 用户对象)
            
        Raises:
            HTTPException: 用户名或密码错误，或用户被封禁
        """
        # 1. 查询用户
        user = UserRepository.get_by_username(db, login_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 2. 验证密码
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 3. 检查用户状态
        if user.status == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被封禁，无法登录"
            )
        
        # 4. 生成 JWT 令牌
        access_token = create_access_token(data={"sub": user.username})
        
        # 5. 更新最后登录时间
        user.last_login_time = datetime.utcnow()
        db.commit()
        
        return access_token, user




















