"""
安全相关功能：JWT 令牌、密码哈希
需求：1.3, 1.5
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# TODO: 从 config 导入配置
# from app.core.config import settings

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # TODO: 实现密码验证
    pass

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # TODO: 实现密码哈希
    pass

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌"""
    # TODO: 实现 JWT 令牌生成
    pass

def decode_access_token(token: str) -> dict:
    """解码 JWT 访问令牌"""
    # TODO: 实现 JWT 令牌解码
    pass