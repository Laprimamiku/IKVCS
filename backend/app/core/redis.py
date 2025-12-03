"""
Redis 连接配置

这个文件的作用：
1. 创建 Redis 连接池 - 相当于 Java 的 JedisPool
2. 提供 Redis 客户端获取函数 - 相当于 Spring 的 RedisTemplate

需求：18.1-18.6（Redis 缓存策略）
"""
import redis
from typing import Optional

from app.core.config import settings

# 创建 Redis 连接池
# decode_responses=True: 自动将字节转为字符串（方便使用）
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    decode_responses=True,  # 自动解码为字符串
    max_connections=50,     # 最大连接数
    socket_connect_timeout=5,  # 连接超时 5 秒
    socket_timeout=5        # 读写超时 5 秒
)

def get_redis() -> redis.Redis:
    """
    获取 Redis 客户端
    
    这个函数返回一个 Redis 客户端实例
    相当于 Spring 的 RedisTemplate
    
    使用方式：
    redis_client = get_redis()
    redis_client.set("key", "value")
    value = redis_client.get("key")
    """
    return redis.Redis(connection_pool=redis_pool)

# 全局 Redis 客户端实例（单例模式）
redis_client = get_redis()
