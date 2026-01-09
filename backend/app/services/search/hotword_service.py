"""
热词管理服务

使用 Redis 存储和管理搜索热词
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.services.cache.redis_service import redis_service

logger = logging.getLogger(__name__)


class HotwordService:
    """热词管理服务"""
    
    # Redis Key 前缀
    HOTWORD_KEY_PREFIX = "search:hotword:"
    HOTWORD_COUNT_KEY = "search:hotword:count"
    HOTWORD_TTL = 7 * 24 * 3600  # 7天过期
    
    @classmethod
    def record_search(cls, keyword: str):
        """
        记录搜索关键词
        
        Args:
            keyword: 搜索关键词
        """
        if not keyword or len(keyword.strip()) == 0:
            return
        
        keyword = keyword.strip()
        
        try:
            # 使用有序集合存储热词，score 为搜索次数
            key = f"{cls.HOTWORD_KEY_PREFIX}{keyword}"
            redis_service.redis.incr(key)
            redis_service.redis.expire(key, cls.HOTWORD_TTL)
            
            # 记录到热词集合
            redis_service.redis.zincrby(cls.HOTWORD_COUNT_KEY, 1, keyword)
            redis_service.redis.expire(cls.HOTWORD_COUNT_KEY, cls.HOTWORD_TTL)
        except Exception as e:
            logger.error(f"记录搜索热词失败: {e}")
    
    @classmethod
    def get_hotwords(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热词榜
        
        Args:
            limit: 返回数量
            
        Returns:
            List[Dict]: [{"keyword": str, "count": int}, ...]
        """
        try:
            # 从有序集合获取 top N
            results = redis_service.redis.zrevrange(
                cls.HOTWORD_COUNT_KEY, 0, limit - 1, withscores=True
            )
            
            hotwords = []
            for keyword_bytes, score in results:
                keyword = keyword_bytes.decode('utf-8') if isinstance(keyword_bytes, bytes) else keyword_bytes
                hotwords.append({
                    "keyword": keyword,
                    "count": int(score)
                })
            
            return hotwords
        except Exception as e:
            logger.error(f"获取热词榜失败: {e}")
            return []
    
    @classmethod
    def get_suggestions(cls, prefix: str, limit: int = 10) -> List[str]:
        """
        获取前缀建议（从热词和标题前缀生成）
        
        Args:
            prefix: 前缀字符串
            limit: 返回数量
            
        Returns:
            List[str]: 建议列表
        """
        if not prefix or len(prefix.strip()) == 0:
            return []
        
        prefix = prefix.strip().lower()
        suggestions = []
        
        try:
            # 1. 从热词中匹配前缀
            all_hotwords = redis_service.redis.zrevrange(
                cls.HOTWORD_COUNT_KEY, 0, 100, withscores=False
            )
            
            for keyword_bytes in all_hotwords:
                keyword = keyword_bytes.decode('utf-8') if isinstance(keyword_bytes, bytes) else keyword_bytes
                if keyword.lower().startswith(prefix) and keyword not in suggestions:
                    suggestions.append(keyword)
                    if len(suggestions) >= limit:
                        break
            
            return suggestions[:limit]
        except Exception as e:
            logger.error(f"获取搜索建议失败: {e}")
            return []

