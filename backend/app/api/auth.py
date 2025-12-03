"""
用户认证 API

这个文件的作用：
1. 用户注册（POST /register）
2. 用户登录（POST /login）
3. 用户登出（POST /logout）

类比 Java：
    相当于 Spring Boot 的 AuthController
    
需求：1.1, 1.2, 1.3, 1.4, 1.5
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    MessageResponse
)

# 创建 HTTPBearer 实例（用于获取令牌）
security = HTTPBearer()

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    类比 Java：
        @PostMapping("/register")
        public ResponseEntity<UserVO> register(@RequestBody @Valid UserRegisterDTO userDTO) {
            // 检查用户名是否已存在
            // 创建用户
            // 返回用户信息
        }
    
    流程：
    1. 检查用户名是否已存在
    2. 对密码进行哈希加密
    3. 创建用户记录
    4. 返回用户信息
    
    需求：1.1, 1.2
    
    为什么这样写：
        - 用户名必须唯一（数据库有唯一索引）
        - 密码必须哈希存储（安全性）
        - 返回 201 Created 状态码（RESTful 规范）
    """
    # 1. 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 2. 创建新用户
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),  # 密码哈希
        nickname=user_data.nickname,
        role="user",  # 默认角色
        status=1  # 默认状态：正常
    )
    
    # 3. 保存到数据库
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # 刷新以获取自增 ID
    
    # 4. 返回用户信息（不包含密码哈希）
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    类比 Java：
        @PostMapping("/login")
        public ResponseEntity<TokenDTO> login(@RequestBody @Valid UserLoginDTO loginDTO) {
            // 验证用户名和密码
            // 生成 JWT 令牌
            // 更新最后登录时间
            // 返回令牌
        }
    
    流程：
    1. 查询用户
    2. 验证密码
    3. 检查用户状态（是否被封禁）
    4. 生成 JWT 令牌
    5. 更新最后登录时间
    6. 返回令牌
    
    需求：1.3, 1.4
    
    为什么这样写：
        - 密码验证使用 bcrypt.verify()（安全）
        - JWT 令牌包含用户名和过期时间
        - 更新最后登录时间（用于统计）
    """
    # 1. 查询用户
    user = db.query(User).filter(User.username == login_data.username).first()
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
    
    # 6. 返回令牌
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """
    用户登出
    
    类比 Java：
        @PostMapping("/logout")
        public ResponseEntity<MessageDTO> logout(@AuthenticationPrincipal User user) {
            // 将令牌加入黑名单
            // 返回成功消息
        }
    
    流程：
    1. 验证用户身份（通过 get_current_user）
    2. 从请求头获取 JWT 令牌
    3. 将令牌加入 Redis 黑名单
    4. 返回成功消息
    
    需求：1.5
    
    为什么这样写：
        - JWT 是无状态的，无法直接"删除"令牌
        - 通过 Redis 黑名单实现令牌失效
        - 黑名单中的令牌在验证时会被拒绝
        - 设置过期时间，避免黑名单无限增长
    """
    from app.core.config import settings
    
    # 获取 Redis 客户端
    redis_client = get_redis()
    
    # 获取令牌字符串
    token = credentials.credentials
    
    # 将令牌加入黑名单
    # 使用 Redis Set 数据结构
    redis_client.sadd("jwt_blacklist", token)
    
    # 设置过期时间（与 JWT 令牌过期时间一致）
    # 这样过期的令牌会自动从黑名单中移除
    redis_client.expire("jwt_blacklist", settings.JWT_EXPIRE_MINUTES * 60)
    
    return MessageResponse(message="登出成功")
