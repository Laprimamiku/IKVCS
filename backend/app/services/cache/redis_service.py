"""
Redis 操作服务 (修复版)
修复了当密码为空时的连接字符串问题
"""
from typing import List, Optional
import json
import logging
from datetime import datetime

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

    async def incr_metric(self, metric: str, expire_seconds: int = 86400) -> None:
        """
        增加一个 AI 量化计数，按日分片保存，默认保留 1 天。
        用于成本/命中/降级等埋点。
        """
        try:
            date_key = datetime.utcnow().strftime("%Y%m%d")
            key = f"ai:metrics:{date_key}:{metric}"
            await self.async_redis.incr(key)
            await self.async_redis.expire(key, expire_seconds)
        except Exception as e:
            logger.debug(f"Redis 计量增量失败: {metric} - {e}")

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

    # ==================== 向量相似度缓存（语义层） ====================

    async def search_similar_vector(
        self,
        cache_key_prefix: str,
        embedding: list,
        threshold: Optional[float] = None,
    ) -> Optional[str]:
        """
        语义缓存 - 简化版相似度查询

        设计说明：
        1. 当前阶段假设还没有专门的向量数据库（如 Redis Vector / PGVector）
           因此采用「退化实现」：把 embedding 直接序列化后作为 Key 存入 Redis。
        2. 由于 embedding 维度较高且为浮点数，我们会对其做「粗量化」处理：
           - 将每个维度保留较少小数位（从配置读取）
           - 只截取前 N 维参与 Key 计算，降低 Key 长度（从配置读取）
        3. 这样可以近似达到「相同 / 极相近」向量命中缓存的效果，
           在无向量检索引擎的前提下，起到成本较低的语义去重作用。

        参数：
        - cache_key_prefix: 业务前缀，例如 "ai:semcache:danmaku" / "ai:semcache:comment"
        - embedding: 当前文本的向量表示（List[float]）
        - threshold: 语义相似阈值（保留参数，方便未来接入真实向量检索，默认从配置读取）

        返回：
        - 命中缓存时返回对应的 JSON 字符串（由上层自行反序列化）
        - 未命中或异常时返回 None
        """
        # 1. 防御性检查
        if not embedding:
            return None

        try:
            # 2. 从配置读取向量维度数和量化精度
            max_dim = settings.AI_VECTOR_DIMENSION
            precision = settings.AI_VECTOR_QUANTIZATION_PRECISION

            # 只取前 N 维，避免 Key 过长
            dim = min(len(embedding), max_dim)
            head = embedding[:dim]

            # 3. 粗量化：每个维度保留 3 位小数，并转为字符串
            #    这样可以一定程度上“容忍”极小的数值抖动
            quantized = [f"{x:.{precision}f}" for x in head]

            # 4. 组合成一个稳定的 Key 片段
            #    示例: ai:semcache:danmaku:0.123_0.456_...
            vector_key = "_".join(quantized)
            key = f"{cache_key_prefix}:{vector_key}"

            # 5. 直接使用 Redis String 存储分析结果 JSON
            cached = await self.async_redis.get(key)
            if cached:
                # 命中缓存：直接返回结果字符串，由上层解析
                return cached

            # 未命中：返回 None，由上层决定是否写入
            return None
        except Exception as e:
            # 出现任何异常时，只打印日志，不影响主流程
            logger.error(f"Redis 向量语义缓存查询失败: {e}")
            return None

    # ==================== 查询缓存 ====================
    
    def get_query_cache(self, cache_key: str) -> Optional[str]:
        """
        获取查询缓存
        
        Args:
            cache_key: 缓存键
            
        Returns:
            Optional[str]: 缓存的JSON字符串，未命中返回None
        """
        try:
            return self.redis.get(cache_key)
        except Exception as e:
            logger.error(f"Redis 获取查询缓存失败：{e}")
            return None
    
    def set_query_cache(self, cache_key: str, data: str, ttl: int = 300) -> bool:
        """
        设置查询缓存
        
        Args:
            cache_key: 缓存键
            data: 要缓存的数据（JSON字符串）
            ttl: 过期时间（秒），默认5分钟
            
        Returns:
            bool: 是否成功
        """
        try:
            self.redis.setex(cache_key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"Redis 设置查询缓存失败：{e}")
            return False
    
    def delete_query_cache(self, pattern: str) -> int:
        """
        删除匹配模式的缓存（用于缓存失效）
        
        Args:
            pattern: 缓存键模式（支持通配符，如 "video:list:*"）
            
        Returns:
            int: 删除的缓存数量
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis 删除查询缓存失败：{e}")
            return 0
    
    def invalidate_video_cache(self, video_id: Optional[int] = None) -> int:
        """
        失效视频相关缓存
        
        Args:
            video_id: 视频ID，如果为None则失效所有视频缓存
            
        Returns:
            int: 删除的缓存数量
        """
        if video_id:
            # 失效特定视频的缓存
            patterns = [
                f"video:detail:{video_id}",
                f"video:list:*",  # 列表缓存也需要失效（因为可能包含该视频）
                f"video:count:*",  # 总数缓存也需要失效
            ]
        else:
            # 失效所有视频缓存
            patterns = [
                "video:detail:*",
                "video:list:*",
                "video:count:*",
            ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.delete_query_cache(pattern)
        
        return total_deleted
    
    def get_count_cache(self, cache_key: str) -> Optional[int]:
        """
        获取计数缓存
        
        Args:
            cache_key: 缓存键
            
        Returns:
            Optional[int]: 缓存的计数值，未命中返回None
        """
        try:
            count = self.redis.get(cache_key)
            return int(count) if count else None
        except Exception as e:
            logger.error(f"Redis 获取计数缓存失败：{e}")
            return None
    
    def set_count_cache(self, cache_key: str, count: int, ttl: int = 300) -> bool:
        """
        设置计数缓存
        
        Args:
            cache_key: 缓存键
            count: 计数值
            ttl: 过期时间（秒），默认5分钟
            
        Returns:
            bool: 是否成功
        """
        try:
            self.redis.setex(cache_key, ttl, str(count))
            return True
        except Exception as e:
            logger.error(f"Redis 设置计数缓存失败：{e}")
            return False

    async def save_vector_result(
        self,
        cache_key_prefix: str,
        embedding: list,
        result_json: str,
        ttl: Optional[int] = None,
    ) -> None:
        """
        保存语义缓存结果（与 search_similar_vector 对应）

        说明：
        - 与 `search_similar_vector` 使用相同的量化策略构造 Key
        - TTL 从配置读取（settings.AI_SEMANTIC_CACHE_TTL），默认7天
        """
        if not embedding:
            return

        try:
            # 从配置读取参数
            max_dim = settings.AI_VECTOR_DIMENSION
            precision = settings.AI_VECTOR_QUANTIZATION_PRECISION
            cache_ttl = ttl if ttl is not None else settings.AI_SEMANTIC_CACHE_TTL

            dim = min(len(embedding), max_dim)
            head = embedding[:dim]
            quantized = [f"{x:.{precision}f}" for x in head]
            vector_key = "_".join(quantized)
            key = f"{cache_key_prefix}:{vector_key}"

            await self.async_redis.setex(key, cache_ttl, result_json)
        except Exception as e:
            logger.error(f"Redis 向量语义缓存写入失败: {e}")


# 全局单例
redis_service = RedisService()
