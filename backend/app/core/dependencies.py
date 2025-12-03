"""
FastAPI 依赖注入工具
类似 Spring 的 @Autowired 依赖注入
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import Optional

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import settings

# HTTP Bearer 认证方案
# 类似 Spring Security 的 BearerTokenAuthenticationFilter
security = HTTPBearer()

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
    
    注意：这个函数会在任务 2 中完善实现
    """
    # TODO: 在任务 2 中实现 JWT 验证逻辑
    # 1. 从 credentials.credentials 获取 token
    # 2. 验证 token 签名和过期时间
    # 3. 检查 Redis 黑名单
    # 4. 从数据库查询用户
    # 5. 返回用户对象
    pass

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
    """
    # TODO: 在任务 2 中实现封禁检查
    # if current_user.status == 0:
    #     raise HTTPException(status_code=403, detail="用户已被封禁")
    # return current_user
    pass

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
    """
    # TODO: 在任务 2 中实现管理员权限检查
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="需要管理员权限")
    # return current_user
    pass
