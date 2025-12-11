"""
Redis 操作服务
需求：18.1-18.6

这个服务封装了所有 Redis 操作，相当于 Java 的 RedisService
主要功能：
1. 播放量缓存（Write-Back 策略）
2. 点赞缓存（Set 数据结构）
3. 上传进度缓存（BitMap）
4. JWT 黑名单
5. 热数据缓存
"""
from typing import List, Optional
import json
import logging

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

class RedisService:
    """Redis 操作封装"""
    
    def __init__(self):
        """初始化 Redis 客户端"""
        self.redis = get_redis()
    
    # ==================== 播放量缓存 (Write-Back) ====================
    # 属性 28：写缓存优先策略
    # 验证需求：18.1
    
    def increment_view_count(self, video_id: int) -> int:
        """
        增加播放量（先写 Redis）
        
        Write-Back 策略：
        1. 先增加 Redis 中的计数
        2. 定时任务会将 Redis 数据同步到 MySQL
        
        Args:
            video_id: 视频ID
            
        Returns:
            int: 增加后的播放量
            
        需求：18.1（写缓存优先策略）
        """
        key = f"video:view_count:{video_id}"
        try:
            # 使用 INCR 原子操作增加计数
            new_count = self.redis.incr(key)
            
            # 设置过期时间（7天），防止 Redis 内存溢出
            # 定时任务会在过期前同步到 MySQL
            self.redis.expire(key, 7 * 24 * 3600)
            
            logger.info(f"视频 {video_id} 播放量增加，当前 Redis 计数：{new_count}")
            return new_count
        except Exception as e:
            logger.error(f"Redis 增加播放量失败：{e}")
            # Redis 失败不影响主流程，返回 0
            return 0

    def get_view_count_from_cache(self, video_id: int) -> Optional[int]:
        """
        从 Redis 获取播放量
        
        Args:
            video_id: 视频ID
            
        Returns:
            Optional[int]: 播放量，如果不存在返回 None
        """
        key = f"video:view_count:{video_id}"
        try:
            count = self.redis.get(key)
            return int(count) if count else None
        except Exception as e:
            logger.error(f"Redis 获取播放量失败：{e}")
            return None

    def sync_view_count_to_db(self, video_id: int, db_session) -> bool:
        """
        将 Redis 中的播放量同步到 MySQL
        
        这个方法会被定时任务调用
        
        Args:
            video_id: 视频ID
            db_session: 数据库会话
            
        Returns:
            bool: 是否同步成功
            
        需求：18.2（Redis 到 MySQL 同步）
        """
        from app.models.video import Video
        
        key = f"video:view_count:{video_id}"
        try:
            # 获取 Redis 中的计数
            redis_count = self.redis.get(key)
            if not redis_count:
                return False
            
            redis_count = int(redis_count)
            
            # 更新数据库
            video = db_session.query(Video).filter(Video.id == video_id).first()
            if video:
                video.view_count = redis_count
                db_session.commit()
                logger.info(f"视频 {video_id} 播放量已同步到数据库：{redis_count}")
                return True
            else:
                logger.warning(f"视频 {video_id} 不存在，无法同步播放量")
                return False
        except Exception as e:
            logger.error(f"同步播放量到数据库失败：{e}")
            db_session.rollback()
            return False
    
    # ==================== 点赞缓存 ====================
    
    async def add_like(self, user_id: int, target_id: int, target_type: str):
        """添加点赞"""
        # TODO: 实现点赞添加
        pass
    
    async def remove_like(self, user_id: int, target_id: int, target_type: str):
        """取消点赞"""
        # TODO: 实现点赞取消
        pass
    
    # ==================== 上传进度缓存 (BitMap) ====================
    # 需求：18.3（上传进度 BitMap 缓存）
    
    def set_chunk_uploaded(self, file_hash: str, chunk_index: int) -> bool:
        """
        标记分片已上传（使用 BitMap）
        
        Args:
            file_hash: 文件哈希
            chunk_index: 分片索引
            
        Returns:
            bool: 是否标记成功
            
        需求：18.3（上传进度 BitMap 缓存）
        """
        redis_key = f"upload:{file_hash}"
        try:
            # 使用 setbit 标记分片已上传（1 bit = 1 个分片）
            self.redis.setbit(redis_key, chunk_index, 1)
            
            # 设置过期时间（7天）
            self.redis.expire(redis_key, 7 * 24 * 3600)
            
            logger.debug(f"分片标记成功：{file_hash} - chunk {chunk_index}")
            return True
        except Exception as e:
            logger.error(f"Redis 标记分片失败：{e}")
            return False
    
    def get_uploaded_chunks(self, file_hash: str, total_chunks: int) -> List[int]:
        """
        获取已上传分片列表（从 BitMap 读取）
        
        Args:
            file_hash: 文件哈希
            total_chunks: 总分片数
            
        Returns:
            List[int]: 已上传分片索引列表
            
        需求：18.3（上传进度 BitMap 缓存）
        """
        redis_key = f"upload:{file_hash}"
        try:
            uploaded = []
            for i in range(total_chunks):
                if self.redis.getbit(redis_key, i):
                    uploaded.append(i)
            return uploaded
        except Exception as e:
            logger.error(f"Redis 获取分片列表失败：{e}")
            return []
    
    def init_upload_bitmap(self, file_hash: str) -> bool:
        """
        初始化上传 BitMap
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            bool: 是否初始化成功
        """
        redis_key = f"upload:{file_hash}"
        try:
            # 设置过期时间（7天）
            self.redis.expire(redis_key, 7 * 24 * 3600)
            logger.info(f"Redis BitMap 初始化成功：{redis_key}")
            return True
        except Exception as e:
            logger.error(f"Redis BitMap 初始化失败：{e}")
            return False
    
    # ==================== Token 黑名单 ====================
    # 需求：18.5（JWT 黑名单缓存）
    
    def blacklist_token(self, token: str, expires_in: int) -> bool:
        """
        将令牌加入黑名单
        
        Args:
            token: JWT 令牌字符串
            expires_in: 过期时间（秒）
            
        Returns:
            bool: 是否加入成功
            
        需求：18.5（JWT 黑名单缓存）
        """
        try:
            # 使用 Redis Set 存储黑名单令牌
            self.redis.sadd("jwt_blacklist", token)
            
            # 设置过期时间（与 JWT 令牌过期时间一致）
            self.redis.expire("jwt_blacklist", expires_in)
            
            logger.info(f"令牌已加入黑名单，过期时间：{expires_in} 秒")
            return True
        except Exception as e:
            logger.error(f"Redis 加入黑名单失败：{e}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        检查令牌是否在黑名单
        
        Args:
            token: JWT 令牌字符串
            
        Returns:
            bool: 如果令牌在黑名单中返回 True
            
        需求：18.5（JWT 黑名单缓存）
        """
        try:
            return bool(self.redis.sismember("jwt_blacklist", token))
        except Exception as e:
            logger.error(f"Redis 检查黑名单失败：{e}")
            # Redis 失败时返回 False（允许访问，避免 Redis 故障导致系统不可用）
            return False
    
    # ==================== 热数据缓存 ====================
    
    async def cache_hot_data(self, key: str, data: dict, ttl: int = 300):
        """缓存热门数据（TTL 300秒）"""
        # TODO: 实现数据缓存
        pass
    
    async def get_cached_data(self, key: str) -> Optional[dict]:
        """获取缓存数据"""
        # TODO: 实现缓存读取
        pass



    # ==================== 弹幕 Pub/Sub ====================
    
    async def publish_danmaku(self, video_id: int, message: dict) -> int:
        """
        发布弹幕消息到 Redis 频道
        
        Args:
            video_id: 视频 ID
            message: 消息字典
            
        Returns:
            int: 接收到消息的订阅者数量
        """
        import redis.asyncio as aioredis
        from app.core.config import settings
        
        # 创建临时异步连接用于发布（或者复用全局异步连接）
        # 注意：这里假设配置中有 REDIS_URL，或者手动拼接
        redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        
        client = await aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        try:
            channel = f"danmaku:video:{video_id}"
            # 发布 JSON 字符串
            result = await client.publish(channel, json.dumps(message))
            logger.debug(f"已发布弹幕到频道 {channel}: {message}")
            return result
        except Exception as e:
            logger.error(f"Redis 发布弹幕失败: {e}")
            return 0
        finally:
            await client.close()

