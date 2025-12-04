"""
安全相关功能：JWT 令牌、密码哈希

这个文件的作用：
1. 密码哈希（bcrypt）- 相当于 Spring Security 的 BCryptPasswordEncoder
2. JWT 令牌生成和验证 - 相当于 Spring Security 的 JwtTokenProvider

需求：1.3, 1.5
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 密码哈希上下文
# schemes=["bcrypt"]: 使用 bcrypt 算法
# deprecated="auto": 自动处理旧版本的哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    参数：
        plain_password: 用户输入的明文密码（如：123456）
        hashed_password: 数据库中存储的哈希密码（如：$2b$12$...）
    
    返回：
        True: 密码正确
        False: 密码错误
    
    类比 Java：
        相当于 BCryptPasswordEncoder.matches(rawPassword, encodedPassword)
    
    为什么这样写：
        bcrypt 是单向加密，不能解密
        只能通过 verify 方法比对明文和哈希是否匹配
    
    容易踩坑点：
        如果 hashed_password 不是有效的 bcrypt 哈希（如明文密码），
        pwd_context.verify() 会抛出异常，导致 500 错误
        所以需要捕获异常并返回 False
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # 如果密码哈希格式无效（如明文密码），返回 False
        # 这样可以避免 500 错误，返回友好的 401 错误
        import logging
        logging.error(f"密码验证失败：{e}")
        return False


def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    参数：
        password: 明文密码（如：123456）
    
    返回：
        哈希后的密码（如：$2b$12$KIXxJ...）
    
    类比 Java：
        相当于 BCryptPasswordEncoder.encode(rawPassword)
    
    为什么这样写：
        每次调用都会生成不同的哈希（加盐）
        即使两个用户密码相同，哈希结果也不同
        这样即使数据库泄露，也无法通过哈希反推密码
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌
    
    参数：
        data: 要编码到令牌中的数据（通常是 {"sub": "username"}）
        expires_delta: 过期时间（可选，默认使用配置中的时间）
    
    返回：
        JWT 令牌字符串（如：eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...）
    
    类比 Java：
        相当于 Jwts.builder()
            .setSubject(username)
            .setExpiration(expiration)
            .signWith(key)
            .compact()
    
    为什么这样写：
        JWT 令牌包含用户信息和过期时间
        客户端每次请求都携带这个令牌
        服务器验证令牌，无需查询数据库
    """
    # 复制数据（避免修改原始数据）
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 默认过期时间：从配置读取（24 小时）
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    # 添加过期时间到令牌数据
    to_encode.update({"exp": expire})
    
    # 生成 JWT 令牌
    # settings.JWT_SECRET_KEY: 密钥（用于签名）
    # settings.JWT_ALGORITHM: 算法（HS256）
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码 JWT 访问令牌
    
    参数：
        token: JWT 令牌字符串
    
    返回：
        解码后的数据（如：{"sub": "username", "exp": 1234567890}）
        如果令牌无效或过期，返回 None
    
    类比 Java：
        相当于 Jwts.parserBuilder()
            .setSigningKey(key)
            .build()
            .parseClaimsJws(token)
            .getBody()
    
    为什么这样写：
        验证令牌的签名和过期时间
        如果验证失败，返回 None（而不是抛出异常）
        调用方可以根据返回值判断令牌是否有效
    """
    try:
        # 解码 JWT 令牌
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        # 令牌无效或过期
        return None