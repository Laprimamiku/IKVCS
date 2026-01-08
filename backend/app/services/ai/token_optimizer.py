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
        判断是否应该处理内容（动态采样策略）
        
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
        budget_ok = await self._check_budget()
        if not budget_ok:
            logger.warning("Token预算已耗尽，跳过处理")
            return False
        
        # 内容长度过短，跳过（可能是无意义内容）
        if len(content.strip()) < 5:
            return False
        
        # 动态计算采样率
        dynamic_rate = self._calculate_dynamic_sampling_rate(content, priority, budget_ok)
        
        # 采样策略：根据内容哈希决定是否处理
        content_hash = hashlib.md5(content.encode()).hexdigest()
        hash_int = int(content_hash[:8], 16)
        
        # 使用动态采样率
        return (hash_int % 100) < (dynamic_rate * 100)
    
    def _calculate_dynamic_sampling_rate(self, content: str, priority: str, budget_ok: bool) -> float:
        """
        动态计算采样率
        
        策略：
        1. 根据预算使用率调整
        2. 根据内容特征调整（长度、关键词）
        3. 根据优先级调整
        """
        base_rate = self.sampling_rate
        
        # 获取预算使用率
        budget_status = self.get_budget_status()
        daily_usage = budget_status.get("daily", {}).get("usage_rate", 0.0)
        hourly_usage = budget_status.get("hourly", {}).get("usage_rate", 0.0)
        max_usage = max(daily_usage, hourly_usage)
        
        # 根据预算使用率调整
        if max_usage > 0.8:
            base_rate *= 0.5  # 预算紧张时降低采样率
        elif max_usage > 0.6:
            base_rate *= 0.7
        elif max_usage < 0.3:
            base_rate *= 1.2  # 预算充足时提高采样率
        
        # 根据内容长度调整（长文本更重要）
        content_len = len(content.strip())
        if content_len > 50:
            base_rate *= 1.3
        elif content_len > 100:
            base_rate *= 1.5
        
        # 根据优先级调整
        if priority == "low":
            base_rate *= 0.5  # 低优先级降低采样率
        elif priority == "normal":
            base_rate *= 1.0  # 正常优先级保持
        
        # 检查关键词（重要内容提高采样率）
        important_keywords = ['重要', '紧急', '违规', '举报', '敏感']
        if any(keyword in content for keyword in important_keywords):
            base_rate *= 1.5
        
        # 限制在合理范围内
        return min(1.0, max(0.1, base_rate))
    
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
        
        # 使用Prompt压缩器进行优化
        try:
            from app.services.ai.prompt_compressor import prompt_compressor
            
            # 根据预算使用率选择压缩策略
            budget_status = self.get_budget_status()
            daily_usage = budget_status.get("daily", {}).get("usage_rate", 0.0)
            
            if daily_usage > 0.8:
                strategy = "aggressive"  # 预算紧张时使用激进压缩
            elif daily_usage > 0.5:
                strategy = "moderate"  # 预算中等时使用中等压缩
            else:
                strategy = "conservative"  # 预算充足时使用保守压缩
            
            compressed = prompt_compressor.compress_prompt(system_prompt, strategy)
            
            # 记录压缩效果
            savings = prompt_compressor.estimate_token_savings(system_prompt, compressed)
            if savings > 0.1:  # 节省超过10%时记录
                logger.debug(f"Prompt压缩: 节省约{savings*100:.1f}% Token")
            
            return compressed
            
        except ImportError:
            # 如果压缩器不可用，使用原有简单优化
            logger.warning("Prompt压缩器不可用，使用简单优化")
            return self._simple_prompt_optimize(system_prompt)
        except Exception as e:
            logger.error(f"Prompt优化失败: {e}", exc_info=True)
            return system_prompt
    
    def _simple_prompt_optimize(self, system_prompt: str) -> str:
        """简单的Prompt优化（回退方案）"""
        import re
        optimized = system_prompt
        
        # 压缩JSON格式要求
        json_format = '{"score":0-100,"category":"类别","label":"标签","reason":"简短原因","confidence":0.0-1.0}'
        
        # 替换冗长的JSON格式说明
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
        """处理批量队列 - 实现真正的批量调用优化"""
        if not self._batch_queue:
            return
        
        batch = self._batch_queue.copy()
        self._batch_queue.clear()
        
        logger.info(f"开始批处理 {len(batch)} 个内容")
        
        # 按内容类型分组，实现批量调用
        danmakus = [item for item in batch if item['content_type'] == 'danmaku']
        comments = [item for item in batch if item['content_type'] == 'comment']
        
        # 批量处理弹幕
        if danmakus:
            await self._batch_process_items(danmakus, 'danmaku')
        
        # 批量处理评论
        if comments:
            await self._batch_process_items(comments, 'comment')
    
    async def _batch_process_items(self, items: List[Dict[str, Any]], content_type: str):
        """
        批量处理同一类型的内容
        
        优化策略：
        1. 合并多个内容为一个LLM请求（如果API支持）
        2. 或使用批量API调用减少网络开销
        3. 记录批量处理的统计信息
        """
        try:
            # 统计批量处理信息
            total_chars = sum(len(item['content']) for item in items)
            optimized_chars = sum(len(self.optimize_content_for_llm(item['content'], content_type)) for item in items)
            chars_saved = total_chars - optimized_chars
            
            # 记录统计信息到Redis
            stats_key = "token_optimizer:stats"
            await redis_service.async_redis.hincrby(stats_key, "batch_processed", len(items))
            await redis_service.async_redis.hincrby(stats_key, "total_tokens_saved", chars_saved)
            await redis_service.async_redis.hset(stats_key, "last_updated", datetime.utcnow().isoformat())
            
            logger.info(f"批量处理 {len(items)} 个{content_type}，节省字符: {chars_saved}")
            
            # 注意：实际的LLM批量调用由 llm_service 的队列机制处理
            # 这里主要负责统计和优化记录
            
        except Exception as e:
            logger.error(f"批量处理失败: {e}", exc_info=True)
    
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
        """
        记录云端调用成本埋点：
        - token_budget:* 按“次数”计数（用于预算/采样策略，与 CLOUD_*_BUDGET_CALLS 匹配）
        - token_usage_est:* 按“估算 token”累加（仅用于测试/评估对比）
        """
        try:
            now = datetime.utcnow()
            day = now.strftime("%Y%m%d")
            hour = now.strftime("%Y%m%d%H")

            call_daily_key = f"token_budget:daily:{day}"
            call_hourly_key = f"token_budget:hourly:{hour}"
            token_daily_key = f"token_usage_est:daily:{day}"
            token_hourly_key = f"token_usage_est:hourly:{hour}"

            est_tokens = int(tokens_used or 0)
            if est_tokens < 0:
                est_tokens = 0
            
            # 1) 次数统计
            await redis_service.async_redis.incr(call_daily_key)
            await redis_service.async_redis.incr(call_hourly_key)

            # 2) token 估算（可选）
            if est_tokens:
                await redis_service.async_redis.incrby(token_daily_key, est_tokens)
                await redis_service.async_redis.incrby(token_hourly_key, est_tokens)
            
            # 设置过期时间
            await redis_service.async_redis.expire(call_daily_key, 86400)  # 24小时
            await redis_service.async_redis.expire(call_hourly_key, 3600)   # 1小时
            await redis_service.async_redis.expire(token_daily_key, 86400)
            await redis_service.async_redis.expire(token_hourly_key, 3600)
            
            # 更新内存计数（按次数，与 *_BUDGET_CALLS 匹配）
            self.budget.current_daily += 1
            self.budget.current_hourly += 1
            
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
            
            # 获取预算状态
            budget_status = self.get_budget_status()
            
            return {
                "total_processed": int(stats_data.get("total_processed", 0)),
                "total_skipped": int(stats_data.get("total_skipped", 0)),
                "total_tokens_saved": int(stats_data.get("total_tokens_saved", 0)),
                "batch_processed": int(stats_data.get("batch_processed", 0)),
                "average_content_reduction": float(stats_data.get("avg_reduction", 0.0)),
                "last_updated": stats_data.get("last_updated", "未知"),
                "budget_status": budget_status,
                "sampling_rate": self.sampling_rate,
                "enabled": self.enabled
            }
        except Exception as e:
            logger.error(f"获取优化统计失败: {e}")
            return {}
    
    async def record_processed(self, skipped: bool = False):
        """记录处理统计"""
        try:
            stats_key = "token_optimizer:stats"
            if skipped:
                await redis_service.async_redis.hincrby(stats_key, "total_skipped", 1)
            else:
                await redis_service.async_redis.hincrby(stats_key, "total_processed", 1)
        except Exception as e:
            logger.error(f"记录处理统计失败: {e}")


# 全局实例
token_optimizer = TokenOptimizer()
