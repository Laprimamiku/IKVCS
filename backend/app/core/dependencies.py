"""
FastAPI 依赖注入工具
类似 Spring 的 @Autowired 依赖注入
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import Optional, TYPE_CHECKING

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import settings

if TYPE_CHECKING:
    from app.models.user import User

# HTTP Bearer 认证方案
# 类似 Spring Security 的 BearerTokenAuthenticationFilter
security = HTTPBearer()


def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    从请求头获取 JWT 令牌
    
    这是一个辅助函数，用于在需要访问令牌本身的地方使用
    例如：logout 时需要将令牌加入黑名单
    
    使用方式：
    @router.post("/logout")
    def logout(token: str = Depends(get_token_from_request)):
        # 将 token 加入黑名单
        pass
    """
    return credentials.credentials

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    获取当前登录用户（JWT 认证）
    
    类似 Spring Security 的 @AuthenticationPrincipal
    
    使用方式：
    @router.get("/users/me")
    def get_me(current_user = Depends(get_current_user)):
        return current_user
    
    流程：
    1. 从请求头获取 JWT 令牌
    2. 验证令牌签名和过期时间
    3. 检查 Redis 黑名单（登出的令牌）
    4. 从数据库查询用户
    5. 返回用户对象
    
    为什么这样写：
        这是一个依赖注入函数，会在每个需要认证的路由中自动执行
        如果认证失败，会抛出 401 异常，阻止访问
    """
    from app.models.user import User
    from app.core.security import decode_access_token
    
    # 1. 获取 JWT 令牌
    token = credentials.credentials
    
    # 2. 解码令牌
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. 检查 Redis 黑名单（登出的令牌）
    redis_client = get_redis()
    if redis_client.sismember("jwt_blacklist", token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 4. 从令牌中获取用户名
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 5. 从数据库查询用户
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    获取当前活跃用户（检查封禁状态）
    
    类似 Spring Security 的自定义 UserDetailsChecker
    
    使用方式：
    @router.get("/videos")
    def get_videos(current_user = Depends(get_current_active_user)):
        return videos
    
    为什么需要这个函数：
        有些接口需要检查用户是否被封禁
        被封禁的用户（status=0）不能访问这些接口
    """
    if current_user.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被封禁，无法访问"
        )
    return current_user


def get_current_admin(
    current_user = Depends(get_current_active_user)
):
    """
    获取当前管理员用户（检查管理员权限）
    
    类似 Spring Security 的 @PreAuthorize("hasRole('ADMIN')")
    
    使用方式：
    @router.get("/admin/users")
    def get_all_users(admin = Depends(get_current_admin)):
        return users
    
    为什么需要这个函数：
        管理后台的接口只能管理员访问
        普通用户（role='user'）会被拒绝
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional["User"]:
    """
    获取当前用户（可选，未登录返回 None）
    
    用于公开接口，支持登录和未登录用户
    """
    from app.models.user import User
    from app.core.security import decode_access_token
    
    # 尝试从请求头获取 token
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    
    # 解码令牌
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    # 检查 Redis 黑名单
    redis_client = get_redis()
    if redis_client.sismember("jwt_blacklist", token):
        return None
    
    # 获取用户名
    username: str = payload.get("sub")
    if username is None:
        return None
    
    # 查询用户
    user = db.query(User).filter(User.username == username).first()
    return user