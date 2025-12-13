"""
Redis 操作服务 (修复版)
修复了当密码为空时的连接字符串问题
"""
from typing import List, Optional
import json
import logging

import redis.asyncio as aioredis  # 异步库
from redis import Redis           # 同步库

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Redis 操作封装"""

    def __init__(self):
        """初始化 Redis 客户端"""
        # 1. 构造通用连接参数
        redis_kwargs = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "decode_responses": True,
            "encoding": "utf-8"
        }

        # 只有当密码存在时才加入
        if settings.REDIS_PASSWORD:
            redis_kwargs["password"] = settings.REDIS_PASSWORD

        # 2. 同步客户端（播放量 / BitMap / 黑名单）
        self.redis = Redis(**redis_kwargs)

        # 3. 异步客户端（点赞 / 弹幕等高并发场景）
        self.async_redis = aioredis.Redis(**redis_kwargs)

        logger.info(f"Redis 服务已初始化 (Host: {settings.REDIS_HOST})")

    # ==================== 播放量缓存 ====================

    def increment_view_count(self, video_id: int) -> int:
        key = f"video:view_count:{video_id}"
        try:
            new_count = self.redis.incr(key)
            self.redis.expire(key, 7 * 24 * 3600)
            return new_count
        except Exception as e:
            logger.error(f"Redis 增加播放量失败：{e}")
            return 0

    def get_view_count_from_cache(self, video_id: int) -> Optional[int]:
        key = f"video:view_count:{video_id}"
        try:
            count = self.redis.get(key)
            return int(count) if count else None
        except Exception as e:
            logger.error(f"Redis 获取播放量失败：{e}")
            return None

    def sync_view_count_to_db(self, video_id: int, db_session) -> bool:
        from app.models.video import Video

        key = f"video:view_count:{video_id}"
        try:
            redis_count = self.redis.get(key)
            if not redis_count:
                return False

            video = db_session.query(Video).filter(Video.id == video_id).first()
            if not video:
                return False

            video.view_count = int(redis_count)
            db_session.commit()
            return True
        except Exception as e:
            logger.error(f"同步播放量失败：{e}")
            db_session.rollback()
            return False

    # ==================== 点赞缓存 (Async + Dirty 标记) ====================

    def _get_like_key(self, target_type: str, target_id: int) -> str:
        return f"likes:{target_type}:{target_id}"

    async def _mark_dirty(self, target_type: str, target_id: int):
        """
        标记点赞数据为脏数据
        用于后续定时任务同步到数据库
        示例值：video:15
        """
        try:
            await self.async_redis.sadd("likes:dirty", f"{target_type}:{target_id}")
        except Exception as e:
            logger.error(f"Redis 标记脏数据失败: {e}")

    async def add_like(self, user_id: int, target_type: str, target_id: int):
        """
        点赞（Set 原子操作）
        无论是否新点赞，都需要标记脏数据
        """
        try:
            key = self._get_like_key(target_type, target_id)
            result = await self.async_redis.sadd(key, user_id)

            # 标记为脏数据
            await self._mark_dirty(target_type, target_id)
            return result
        except Exception as e:
            logger.error(f"Redis 添加点赞失败: {e}")
            return 0

    async def remove_like(self, user_id: int, target_type: str, target_id: int):
        """
        取消点赞
        即使 key 被删空，也必须标记脏数据
        """
        try:
            key = self._get_like_key(target_type, target_id)
            result = await self.async_redis.srem(key, user_id)

            # 同样标记脏数据
            await self._mark_dirty(target_type, target_id)
            return result
        except Exception as e:
            logger.error(f"Redis 取消点赞失败: {e}")
            return 0

    async def get_like_count(self, target_type: str, target_id: int) -> int:
        try:
            key = self._get_like_key(target_type, target_id)
            return await self.async_redis.scard(key)
        except Exception as e:
            logger.error(f"Redis 获取点赞数失败: {e}")
            return 0

    async def is_liked(self, user_id: int, target_type: str, target_id: int) -> bool:
        try:
            key = self._get_like_key(target_type, target_id)
            return await self.async_redis.sismember(key, user_id)
        except Exception as e:
            logger.error(f"Redis 检查点赞失败: {e}")
            return False

    # ==================== 弹幕发布 ====================

    async def publish_danmaku(self, video_id: int, message: dict) -> int:
        try:
            channel = f"danmaku:video:{video_id}"
            return await self.async_redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Redis 发布弹幕失败: {e}")
            return 0

    # ==================== 上传进度 BitMap ====================

    def set_chunk_uploaded(self, file_hash: str, chunk_index: int) -> bool:
        key = f"upload:{file_hash}"
        try:
            self.redis.setbit(key, chunk_index, 1)
            self.redis.expire(key, 7 * 24 * 3600)
            return True
        except Exception:
            return False

    def get_uploaded_chunks(self, file_hash: str, total_chunks: int) -> List[int]:
        key = f"upload:{file_hash}"
        try:
            return [i for i in range(total_chunks) if self.redis.getbit(key, i)]
        except Exception:
            return []

    def init_upload_bitmap(self, file_hash: str) -> bool:
        try:
            self.redis.expire(f"upload:{file_hash}", 7 * 24 * 3600)
            return True
        except Exception:
            return False

    # ==================== JWT 黑名单 ====================

    def blacklist_token(self, token: str, expires_in: int) -> bool:
        try:
            self.redis.sadd("jwt_blacklist", token)
            self.redis.expire("jwt_blacklist", expires_in)
            return True
        except Exception:
            return False

    def is_token_blacklisted(self, token: str) -> bool:
        try:
            return bool(self.redis.sismember("jwt_blacklist", token))
        except Exception:
            return False


# 全局单例
redis_service = RedisService()
