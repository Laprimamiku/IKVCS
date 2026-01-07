"""
Token节省优化服务 - 高杠杆策略实现

功能：
1. 内容预处理和截断
2. 批量处理减少API调用
3. 智能采样策略
4. 输出格式优化
5. 预算控制和熔断

针对硬件配置：i5-11260H/16GB/RTX 3050 4GB
"""

import asyncio
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.core.config import settings
from app.services.cache.redis_service import redis_service

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Token预算管理"""
    daily_limit: int
    hourly_limit: int
    current_daily: int = 0
    current_hourly: int = 0
    last_reset_hour: int = 0
    last_reset_day: int = 0


class TokenOptimizer:
    """Token节省优化器"""
    
    def __init__(self):
        self.enabled = getattr(settings, 'TOKEN_SAVE_ENABLED', True)
        self.content_max_length = getattr(settings, 'TOKEN_SAVE_CONTENT_MAX_LENGTH', 500)
        self.reason_max_length = getattr(settings, 'TOKEN_SAVE_REASON_MAX_LENGTH', 50)
        self.batch_size = getattr(settings, 'TOKEN_SAVE_BATCH_SIZE', 10)
        self.sampling_rate = getattr(settings, 'TOKEN_SAVE_SAMPLING_RATE', 0.3)
        
        # 预算控制
        self.budget = TokenBudget(
            daily_limit=getattr(settings, 'CLOUD_DAILY_BUDGET_CALLS', 1000),
            hourly_limit=getattr(settings, 'CLOUD_HOURLY_BUDGET_CALLS', 100)
        )
        
        # 批处理队列
        self._batch_queue: List[Dict[str, Any]] = []
        self._batch_lock = asyncio.Lock()
        
        logger.info(f"Token优化器初始化: enabled={self.enabled}, sampling_rate={self.sampling_rate}")
    
    async def should_process_content(self, content: str, content_type: str, priority: str = "normal") -> bool:
        """
        判断是否应该处理内容（智能采样策略）
        
        Args:
            content: 内容文本
            content_type: 内容类型
            priority: 优先级 (high/normal/low)
        
        Returns:
            bool: 是否应该处理
        """
        if not self.enabled:
            return True
        
        # 高优先级内容总是处理
        if priority == "high":
            return True
        
        # 检查预算限制
        if not await self._check_budget():
            logger.warning("Token预算已耗尽，跳过处理")
            return False
        
        # 内容长度过短，跳过（可能是无意义内容）
        if len(content.strip()) < 5:
            return False
        
        # 采样策略：根据内容哈希决定是否处理
        content_hash = hashlib.md5(content.encode()).hexdigest()
        hash_int = int(content_hash[:8], 16)
        
        # 低优先级内容按采样率处理
        if priority == "low":
            return (hash_int % 100) < (self.sampling_rate * 50)  # 降低采样率
        
        # 普通优先级内容按正常采样率处理
        return (hash_int % 100) < (self.sampling_rate * 100)
    
    def optimize_content_for_llm(self, content: str, content_type: str) -> str:
        """
        优化内容以减少Token消耗
        
        Args:
            content: 原始内容
            content_type: 内容类型
        
        Returns:
            str: 优化后的内容
        """
        if not self.enabled:
            return content
        
        # 1. 去除多余空白字符
        optimized = ' '.join(content.split())
        
        # 2. 长度截断（保留重要信息）
        if len(optimized) > self.content_max_length:
            # 智能截断：保留开头和结尾
            half_length = self.content_max_length // 2 - 10
            optimized = optimized[:half_length] + "..." + optimized[-half_length:]
        
        # 3. 移除重复字符（如多个感叹号）
        import re
        optimized = re.sub(r'([!?。，])\1{2,}', r'\1\1', optimized)
        
        # 4. 表情符号压缩
        optimized = re.sub(r'[😀-🙏]{3,}', '😊', optimized)
        
        return optimized
    
    def optimize_prompt_for_llm(self, system_prompt: str) -> str:
        """
        优化系统Prompt以减少Token消耗
        
        Args:
            system_prompt: 原始系统Prompt
        
        Returns:
            str: 优化后的Prompt
        """
        if not self.enabled:
            return system_prompt
        
        # 移除多余的示例和解释
        optimized = system_prompt
        
        # 压缩JSON格式要求
        json_format = '{"score":0-100,"category":"类别","label":"标签","reason":"简短原因","confidence":0.0-1.0}'
        
        # 替换冗长的JSON格式说明
        import re
        optimized = re.sub(
            r'返回格式.*?```json.*?```',
            f'返回JSON格式: {json_format}',
            optimized,
            flags=re.DOTALL
        )
        
        return optimized
    
    def optimize_llm_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化LLM响应以减少存储和传输成本
        
        Args:
            response: 原始响应
        
        Returns:
            Dict: 优化后的响应
        """
        if not self.enabled:
            return response
        
        optimized = response.copy()
        
        # 截断reason字段
        if 'reason' in optimized and len(optimized['reason']) > self.reason_max_length:
            optimized['reason'] = optimized['reason'][:self.reason_max_length] + "..."
        
        # 移除不必要的字段
        unnecessary_fields = ['raw_response', 'debug_info', 'model_version']
        for field in unnecessary_fields:
            optimized.pop(field, None)
        
        return optimized
    
    async def add_to_batch(self, content: str, content_type: str, callback_id: str) -> bool:
        """
        添加到批处理队列
        
        Args:
            content: 内容
            content_type: 类型
            callback_id: 回调ID
        
        Returns:
            bool: 是否成功添加
        """
        if not self.enabled:
            return False
        
        async with self._batch_lock:
            self._batch_queue.append({
                'content': content,
                'content_type': content_type,
                'callback_id': callback_id,
                'timestamp': datetime.utcnow()
            })
            
            # 队列满了或超时，触发批处理
            if len(self._batch_queue) >= self.batch_size:
                await self._process_batch()
                return True
        
        return False
    
    async def _process_batch(self):
        """处理批量队列"""
        if not self._batch_queue:
            return
        
        batch = self._batch_queue.copy()
        self._batch_queue.clear()
        
        logger.info(f"开始批处理 {len(batch)} 个内容")
        
        # 这里可以实现批量调用LLM的逻辑
        # 暂时记录日志
        for item in batch:
            logger.debug(f"批处理项目: {item['callback_id']}")
    
    async def _check_budget(self) -> bool:
        """检查Token预算是否充足"""
        try:
            now = datetime.utcnow()
            current_hour = now.hour
            current_day = now.day
            
            # 重置小时计数
            if current_hour != self.budget.last_reset_hour:
                self.budget.current_hourly = 0
                self.budget.last_reset_hour = current_hour
            
            # 重置日计数
            if current_day != self.budget.last_reset_day:
                self.budget.current_daily = 0
                self.budget.last_reset_day = current_day
            
            # 从Redis获取实际使用量
            daily_key = f"token_budget:daily:{now.strftime('%Y%m%d')}"
            hourly_key = f"token_budget:hourly:{now.strftime('%Y%m%d%H')}"
            
            daily_used = await redis_service.async_redis.get(daily_key) or 0
            hourly_used = await redis_service.async_redis.get(hourly_key) or 0
            
            self.budget.current_daily = int(daily_used)
            self.budget.current_hourly = int(hourly_used)
            
            # 检查是否超出限制
            if self.budget.current_daily >= self.budget.daily_limit:
                return False
            
            if self.budget.current_hourly >= self.budget.hourly_limit:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查Token预算失败: {e}")
            return True  # 出错时允许处理，避免阻塞
    
    async def record_token_usage(self, tokens_used: int):
        """记录Token使用量"""
        try:
            now = datetime.utcnow()
            daily_key = f"token_budget:daily:{now.strftime('%Y%m%d')}"
            hourly_key = f"token_budget:hourly:{now.strftime('%Y%m%d%H')}"
            
            # 增加使用量
            await redis_service.async_redis.incr(daily_key)
            await redis_service.async_redis.incr(hourly_key)
            
            # 设置过期时间
            await redis_service.async_redis.expire(daily_key, 86400)  # 24小时
            await redis_service.async_redis.expire(hourly_key, 3600)   # 1小时
            
            # 更新内存计数
            self.budget.current_daily += tokens_used
            self.budget.current_hourly += tokens_used
            
        except Exception as e:
            logger.error(f"记录Token使用量失败: {e}")
    
    def get_budget_status(self) -> Dict[str, Any]:
        """获取预算状态"""
        return {
            "daily": {
                "used": self.budget.current_daily,
                "limit": self.budget.daily_limit,
                "remaining": max(0, self.budget.daily_limit - self.budget.current_daily),
                "usage_rate": self.budget.current_daily / self.budget.daily_limit if self.budget.daily_limit > 0 else 0
            },
            "hourly": {
                "used": self.budget.current_hourly,
                "limit": self.budget.hourly_limit,
                "remaining": max(0, self.budget.hourly_limit - self.budget.current_hourly),
                "usage_rate": self.budget.current_hourly / self.budget.hourly_limit if self.budget.hourly_limit > 0 else 0
            },
            "enabled": self.enabled,
            "sampling_rate": self.sampling_rate
        }
    
    async def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        try:
            # 从Redis获取统计数据
            stats_key = "token_optimizer:stats"
            stats_data = await redis_service.async_redis.hgetall(stats_key)
            
            return {
                "total_processed": int(stats_data.get("total_processed", 0)),
                "total_skipped": int(stats_data.get("total_skipped", 0)),
                "total_tokens_saved": int(stats_data.get("total_tokens_saved", 0)),
                "batch_processed": int(stats_data.get("batch_processed", 0)),
                "average_content_reduction": float(stats_data.get("avg_reduction", 0.0)),
                "last_updated": stats_data.get("last_updated", "未知")
            }
        except Exception as e:
            logger.error(f"获取优化统计失败: {e}")
            return {}


# 全局实例
token_optimizer = TokenOptimizer()