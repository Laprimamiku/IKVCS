"""
LLM 智能分析服务 - 升级版
支持 APO (Automatic Prompt Optimization) + 模型注册表 + 策略编排

功能：
1. 弹幕 / 评论智能评分与分类
2. 规则预过滤，减少 LLM Token 消耗
3. 动态 Prompt（从数据库读取激活版本）
4. 结果结构化解析
5. Redis 精确缓存（MD5哈希）
6. 云端大模型 + 本地小模型协同（通过模型注册表）
7. 图像识别分析（云端模型）
8. 异步后台任务，直接更新数据库
9. 成本控制与预算管理

架构：
- Layer 1: 规则过滤
- Layer 1.5: 精确缓存（Redis）
- Layer 1.6: 语义缓存（可选）
- Layer 2: 本地/云端模型（通过模型注册表）
- Layer 3: 多智能体陪审团（可选）
"""

import asyncio
import httpx
import json
import logging
import hashlib
import random
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple, Set
from datetime import datetime

from app.core.config import settings
from app.core.types import AIContentAnalysisResult
from app.core.database import SessionLocal
from app.core.model_registry import model_registry
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.models.ai_prompt_version import AiPromptVersion
from app.services.ai.prompts import (
    DANMAKU_SYSTEM_PROMPT,
    COMMENT_SYSTEM_PROMPT,
    DANMAKU_SYSTEM_PROMPT_LOCAL,
    COMMENT_SYSTEM_PROMPT_LOCAL,
    DANMAKU_SYSTEM_PROMPT_CLOUD,
    COMMENT_SYSTEM_PROMPT_CLOUD
)
from app.services.cache.redis_service import redis_service
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now
from app.services.ai.embedding_service import embedding_service  # 允许返回 None，不影响主流程
from app.services.ai.local_model_service import local_model_service
from app.services.ai.token_optimizer import token_optimizer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _AnalysisQueueItem:
    content_type: str  # "danmaku" | "comment"
    item_id: int
    priority: str = "low"

# ==================== 多智能体延迟加载 ====================

_multi_agent_service = None


def _get_multi_agent_service():
    global _multi_agent_service
    if _multi_agent_service is None:
        try:
            from app.services.ai.multi_agent_service import multi_agent_service
            _multi_agent_service = multi_agent_service
        except ImportError as e:
            logger.debug(f"多智能体服务不可用: {e}")
            _multi_agent_service = None
    return _multi_agent_service


# ==================== LLM Service ====================

class LLMService:
    def __init__(self):
        # 运行模式
        self.mode = getattr(settings, "LLM_MODE", "hybrid").lower()
        
        # 成本控制
        self.cost_tracker = {}  # video_id -> {"calls": count, "chars": count}
        
        self.default_response: AIContentAnalysisResult = {
            "score": 60,
            "category": "普通",
            "label": "普通",
            "reason": "默认处理",
            "is_highlight": False,
            "is_inappropriate": False,
            "confidence": 0.5,
            "source": "default",
            "model_name": "default",
            "prompt_version_id": None,
            "decision_trace": []
        }

        # 高频短文本：队列批处理（降低云端 token + 避免 GPU/IO 峰值）
        def _as_bool(value: object, default: bool = False) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return bool(value)
            if isinstance(value, str):
                v = value.strip().lower()
                if v in {"1", "true", "t", "yes", "y", "on"}:
                    return True
                if v in {"0", "false", "f", "no", "n", "off"}:
                    return False
            return default

        def _as_int(value: object, default: int) -> int:
            if isinstance(value, bool):
                return default
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                v = value.strip()
                if not v:
                    return default
                try:
                    return int(float(v))
                except (TypeError, ValueError):
                    return default
            return default

        def _as_float(value: object, default: float) -> float:
            if isinstance(value, bool):
                return default
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                v = value.strip()
                if not v:
                    return default
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return default
            return default

        self.queue_enabled: bool = _as_bool(getattr(settings, "AI_ANALYSIS_QUEUE_ENABLED", False), False)
        self._analysis_queue_maxsize: int = _as_int(getattr(settings, "AI_ANALYSIS_QUEUE_MAXSIZE", 0), 0)
        self._analysis_queue: asyncio.Queue[_AnalysisQueueItem] = asyncio.Queue(maxsize=max(0, self._analysis_queue_maxsize))
        self._analysis_pending: Set[Tuple[str, int]] = set()
        self._analysis_workers: List[asyncio.Task] = []
        self._analysis_batch_size: int = max(1, _as_int(getattr(settings, "AI_ANALYSIS_BATCH_SIZE", 30), 30))
        batch_window_ms = _as_float(getattr(settings, "AI_ANALYSIS_BATCH_WINDOW_MS", 500), 500.0)
        self._analysis_batch_window_s: float = max(0.05, batch_window_ms / 1000.0)
        self._analysis_worker_count: int = max(1, _as_int(getattr(settings, "AI_ANALYSIS_QUEUE_WORKERS", 1), 1))
        
        # 记录当前配置
        logger.info(f"LLM Service 初始化完成:")
        logger.info(f"  LLM_MODE: {self.mode}")
        logger.info(f"  AI_ANALYSIS_QUEUE_ENABLED: {self.queue_enabled}")
        
        if self.mode != "off":
            available_models = model_registry.get_available_models()
            for model_type, config in available_models.items():
                logger.info(f"  {model_type}: {config.name} @ {config.base_url}")
        else:
            logger.info("  LLM_MODE=off，所有AI功能已禁用")

    # ==================== 工具方法 ====================

    def _get_content_hash(self, content: str, prompt_version_id: Optional[int] = None) -> str:
        """生成内容哈希，包含 Prompt 版本信息"""
        hash_input = content.strip()
        if prompt_version_id:
            hash_input += f"_v{prompt_version_id}"
        return hashlib.md5(hash_input.encode("utf-8")).hexdigest()

    def _normalize_for_dedup(self, content: str) -> str:
        """短文本去重用的轻量归一化（比 embedding 便宜）"""
        text = " ".join((content or "").split()).strip().lower()
        # 合并重复标点/表情符号，避免“哈哈哈哈”“!!!!!”造成去重失败
        text = re.sub(r"([!！?？。，,.…~～])\\1{1,}", r"\\1", text)
        text = re.sub(r"(哈)\\1{2,}", r"\\1\\1", text)
        return text[:300]

    def _semantic_threshold_for(self, content: str) -> float:
        """短文本更保守，避免语义缓存误命中"""
        base = getattr(settings, "AI_SEMANTIC_CACHE_THRESHOLD", 0.95)
        short = getattr(settings, "AI_SEMANTIC_CACHE_THRESHOLD_SHORT", base)
        return short if len(content) < 30 else base

    def _should_store_trace(self, result: AIContentAnalysisResult) -> bool:
        mode = (getattr(settings, "AI_ANALYSIS_TRACE_MODE", "risky") or "risky").lower()
        if mode == "none":
            return False
        if mode == "all":
            return True
        if mode == "sample":
            rate = float(getattr(settings, "AI_ANALYSIS_TRACE_SAMPLE_RATE", 0.05) or 0.0)
            return random.random() < max(0.0, min(1.0, rate))

        # risky（默认）：仅异常/低置信/低分写入，避免 DB/IO 写放大
        risk_score = int(getattr(settings, "AI_ANALYSIS_TRACE_RISK_SCORE", 55) or 55)
        low_conf = float(getattr(settings, "AI_ANALYSIS_TRACE_LOW_CONFIDENCE", 0.6) or 0.6)
        score = int(result.get("score", 60) or 60)
        conf = float(result.get("confidence", 0.5) or 0.5)
        if bool(result.get("is_inappropriate")):
            return True
        return score < risk_score or conf < low_conf

    async def start_analysis_queue(self) -> None:
        if not self.queue_enabled:
            return
        if self._analysis_workers:
            return
        for i in range(self._analysis_worker_count):
            self._analysis_workers.append(asyncio.create_task(self._analysis_worker_loop(i)))
        logger.info(
            "[AIQueue] started workers=%s batch_size=%s window_ms=%s maxsize=%s",
            self._analysis_worker_count,
            self._analysis_batch_size,
            int(self._analysis_batch_window_s * 1000),
            self._analysis_queue_maxsize,
        )

    async def stop_analysis_queue(self) -> None:
        if not self._analysis_workers:
            return
        for t in self._analysis_workers:
            t.cancel()
        await asyncio.gather(*self._analysis_workers, return_exceptions=True)
        self._analysis_workers.clear()
        logger.info("[AIQueue] stopped")

    async def enqueue_analysis(self, content_type: str, item_id: int, priority: str = "low") -> None:
        if not self.queue_enabled:
            return
        key = (content_type, int(item_id))
        if key in self._analysis_pending:
            return
        self._analysis_pending.add(key)
        try:
            self._analysis_queue.put_nowait(
                _AnalysisQueueItem(content_type=content_type, item_id=int(item_id), priority=priority)
            )
            logger.info(
                "[AIQueue] enqueued %s:%s priority=%s qsize=%s",
                content_type,
                item_id,
                priority,
                self._analysis_queue.qsize(),
            )
        except asyncio.QueueFull:
            # 不阻塞主流程：队列满时直接丢弃，依赖缓存/规则兜底
            self._analysis_pending.discard(key)
            logger.warning("[AIQueue] queue_full drop %s:%s", content_type, item_id)

    async def _drain_batch(self) -> List[_AnalysisQueueItem]:
        first = await self._analysis_queue.get()
        self._analysis_pending.discard((first.content_type, first.item_id))
        batch: List[_AnalysisQueueItem] = [first]

        loop = asyncio.get_running_loop()
        start = loop.time()
        while len(batch) < self._analysis_batch_size:
            remaining = self._analysis_batch_window_s - (loop.time() - start)
            if remaining <= 0:
                break
            try:
                item = await asyncio.wait_for(self._analysis_queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                break
            self._analysis_pending.discard((item.content_type, item.item_id))
            batch.append(item)

        return batch

    async def _analysis_worker_loop(self, worker_id: int) -> None:
        while True:
            batch = await self._drain_batch()
            try:
                await self._process_analysis_batch(batch, worker_id=worker_id)
            except Exception as e:
                logger.error("[AIQueue] worker=%s batch_process_failed: %s", worker_id, e, exc_info=True)

    async def _process_analysis_batch(self, batch: List[_AnalysisQueueItem], worker_id: int = 0) -> None:
        # 分类型聚合
        comment_ids = [t.item_id for t in batch if t.content_type == "comment"]
        danmaku_ids = [t.item_id for t in batch if t.content_type == "danmaku"]

        if not comment_ids and not danmaku_ids:
            return

        db = SessionLocal()
        try:
            comments = []
            danmakus = []
            if comment_ids:
                comments = db.query(Comment).filter(Comment.id.in_(comment_ids)).all()
            if danmaku_ids:
                danmakus = db.query(Danmaku).filter(Danmaku.id.in_(danmaku_ids)).all()

            # group by normalized content to analyze once
            groups: Dict[Tuple[str, str], List[Any]] = {}
            priorities: Dict[Tuple[str, str], str] = {}

            id_to_priority: Dict[Tuple[str, int], str] = {(t.content_type, t.item_id): t.priority for t in batch}

            for c in comments:
                key = ("comment", self._normalize_for_dedup(c.content))
                groups.setdefault(key, []).append(c)
                priorities.setdefault(key, id_to_priority.get(("comment", c.id), "low"))

            for d in danmakus:
                key = ("danmaku", self._normalize_for_dedup(d.content))
                groups.setdefault(key, []).append(d)
                priorities.setdefault(key, id_to_priority.get(("danmaku", d.id), "low"))

            processed = 0
            for (content_type, _norm), items in groups.items():
                # 使用首条内容作为代表
                content = (items[0].content or "").strip()
                if not content:
                    continue
                priority = priorities.get((content_type, _norm), "low")
                priority = self._effective_priority(content_type, content, priority)
                result = await self.analyze_content_with_policy(
                    content=content,
                    content_type=content_type,
                    force_jury=False,
                    video_id=None,
                    priority=priority,
                )
                processed += len(items)

                trace = result.get("decision_trace")
                store_trace = bool(trace) and self._should_store_trace(result)
                trace_json = None
                if store_trace:
                    try:
                        trace_json = json.dumps(trace, ensure_ascii=False)
                    except Exception:
                        trace_json = None

                for obj in items:
                    if content_type == "danmaku":
                        obj.ai_score = result.get("score", 60)
                        obj.ai_category = result.get("category", "普通")
                        obj.ai_reason = result.get("reason")
                        obj.ai_confidence = result.get("confidence", 0.5)
                        obj.ai_source = result.get("source")
                        obj.ai_prompt_version_id = result.get("prompt_version_id")
                        obj.ai_model = result.get("model_name")
                        if store_trace:
                            obj.ai_trace = trace_json
                        obj.is_highlight = bool(result.get("is_highlight", False) or (obj.ai_score or 0) >= 90)
                    else:
                        obj.ai_score = result.get("score", 60)
                        obj.ai_label = result.get("label", "普通")
                        obj.ai_reason = result.get("reason")
                        conf = result.get("confidence", 0.5)
                        obj.ai_confidence = int(float(conf) * 100) if conf is not None else None
                        obj.ai_source = result.get("source")
                        obj.ai_prompt_version_id = result.get("prompt_version_id")
                        obj.ai_model = result.get("model_name")
                        if store_trace:
                            obj.ai_trace = trace_json

            if processed:
                db.commit()
                logger.info("[AIQueue] worker=%s processed=%s batch=%s", worker_id, processed, len(batch))

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def _mark_metric(self, metric: str) -> None:
        """轻量埋点：记录规则/缓存/云端/本地/jury 调用次数。"""
        try:
            await redis_service.incr_metric(metric)
        except Exception:
            # 埋点失败不影响主流程
            pass

    def _check_budget(self, video_id: Optional[int], input_chars: int) -> bool:
        """检查预算限制"""
        if not video_id:
            return True
            
        # 获取预算限制配置
        max_calls = getattr(settings, 'CLOUD_MAX_CALLS_PER_VIDEO', 0)
        max_chars = getattr(settings, 'CLOUD_MAX_INPUT_CHARS_PER_VIDEO', 0)
        
        if max_calls <= 0 and max_chars <= 0:
            return True  # 无限制
        
        current = self.cost_tracker.get(video_id, {"calls": 0, "chars": 0})
        
        # 检查调用次数限制
        if max_calls > 0 and current["calls"] >= max_calls:
            logger.warning(f"视频 {video_id} 已达到云端调用次数限制: {current['calls']}")
            return False
        
        # 检查字符数限制
        if max_chars > 0 and current["chars"] + input_chars > max_chars:
            logger.warning(f"视频 {video_id} 已达到云端字符数限制: {current['chars']} + {input_chars}")
            return False
        
        return True

    def _update_budget(self, video_id: Optional[int], input_chars: int):
        """更新预算使用情况"""
        if not video_id:
            return
        
        if video_id not in self.cost_tracker:
            self.cost_tracker[video_id] = {"calls": 0, "chars": 0}
        
        self.cost_tracker[video_id]["calls"] += 1
        self.cost_tracker[video_id]["chars"] += input_chars

    # ==================== Prompt 版本管理（已注释，不再使用） ====================
    # def _get_active_prompt(self, content_type: str) -> tuple[str, Optional[int]]:
    #     """获取激活的 Prompt 版本"""
    #     db = SessionLocal()
    #     try:
    #         # 映射内容类型到 Prompt 类型
    #         prompt_type_map = {
    #             "danmaku": "DANMAKU",
    #             "comment": "COMMENT"
    #         }
    #         prompt_type = prompt_type_map.get(content_type)
    #         
    #         if prompt_type:
    #             # 查询激活版本
    #             active_version = db.query(AiPromptVersion).filter(
    #                 AiPromptVersion.prompt_type == prompt_type,
    #                 AiPromptVersion.is_active == True
    #             ).first()
    #             
    #             if active_version:
    #                 logger.debug(f"使用数据库 Prompt 版本 {active_version.id}: {prompt_type}")
    #                 return active_version.prompt_content, active_version.id
    #         
    #         # 回退到硬编码 Prompt
    #         fallback_prompt = (
    #             DANMAKU_SYSTEM_PROMPT if content_type == "danmaku" 
    #             else COMMENT_SYSTEM_PROMPT
    #         )
    #         logger.debug(f"使用硬编码 Prompt: {content_type}")
    #         return fallback_prompt, None
    #         
    #     except Exception as e:
    #         logger.warning(f"获取 Prompt 版本失败: {e}")
    #         # 回退到硬编码 Prompt
    #         fallback_prompt = (
    #             DANMAKU_SYSTEM_PROMPT if content_type == "danmaku" 
    #             else COMMENT_SYSTEM_PROMPT
    #         )
    #         return fallback_prompt, None
    #     finally:
    #         db.close()
    
    def _get_prompt_for_model(self, content_type: str, model_type: str) -> str:
        """根据模型类型获取对应的提示词"""
        if model_type == "local_text":
            # 本地模型使用简化提示词
            if content_type == "danmaku":
                return DANMAKU_SYSTEM_PROMPT_LOCAL
            else:
                return COMMENT_SYSTEM_PROMPT_LOCAL
        else:
            # 云端模型使用完整提示词
            if content_type == "danmaku":
                return DANMAKU_SYSTEM_PROMPT_CLOUD
            else:
                return COMMENT_SYSTEM_PROMPT_CLOUD

    # ==================== 核心分析流程 ====================

    async def analyze_content_with_policy(
        self, 
        content: str, 
        content_type: str, 
        force_jury: bool = False,
        video_id: Optional[int] = None,
        priority: str = "normal"
    ) -> AIContentAnalysisResult:
        """
        策略编排的智能内容分析（APO + Multi-Agent + Token优化）
        
        Layer 1   : 规则过滤
        Layer 1.5 : 精确缓存（MD5）
        Layer 1.6 : 语义缓存（可选）
        Layer 2   : 本地/云端模型（通过模型注册表）
        Layer 3   : 多智能体陪审团（可选）
        """
        if not content:
            return self.default_response.copy()
        
        # 优化内容以减少Token消耗
        optimized_content = token_optimizer.optimize_content_for_llm(content, content_type)
        
        # 不再使用Prompt版本管理，prompt_version_id固定为None
        prompt_version_id = None
        
        trace = [
            {
                "step": "start", 
                "mode": self.mode, 
                "prompt_version_id": None,
                "content_optimized": len(optimized_content) < len(content),
                "timestamp": isoformat_in_app_tz(utc_now()),
            }
        ]

        # ==================== Layer 1: 规则过滤 ====================
        pre_check = self._rule_based_filter(optimized_content, content_type)
        if pre_check:
            await self._mark_metric("rule_hit")
            pre_check["prompt_version_id"] = prompt_version_id
            pre_check["decision_trace"] = trace + [{"step": "rule_hit"}]
            # 优化输出
            return token_optimizer.optimize_llm_response(pre_check)

        # ==================== Layer 1.5: 精确缓存 ====================
        content_hash = self._get_content_hash(optimized_content, prompt_version_id)
        exact_cache_key = f"ai:analysis:{content_type}:{content_hash}"

        try:
            cached = await redis_service.async_redis.get(exact_cache_key)
            if cached:
                logger.info(f"AI Exact Cache Hit: {optimized_content[:10]}...")
                result = json.loads(cached)
                result.setdefault("source", "cache_exact")
                result["prompt_version_id"] = prompt_version_id
                result["decision_trace"] = trace + [{"step": "cache_exact"}]
                await self._mark_metric("exact_hit")
                # 多智能体陪审团已注释，直接返回结果
                return result
        except Exception as e:
            logger.warning(f"Exact cache read failed: {e}")

        # ==================== Layer 1.6: 语义缓存（分层缓存策略） ====================
        sem_result = None
        embedding = None
        try:
            min_len = int(getattr(settings, "AI_SEMANTIC_CACHE_MIN_LEN", 0) or 0)
            if len(optimized_content) < min_len:
                embedding = None
            else:
                embedding = await embedding_service.get_text_embedding(optimized_content)
            if embedding:
                sem_key_prefix = f"ai:semcache:{content_type}"
                
                # 强化语义缓存：分层缓存策略，降低阈值以识别更多含义高度相似的语句
                # 基础阈值已从0.95降低到0.88，这里进一步降低以增强相似语句识别
                base_threshold = self._semantic_threshold_for(optimized_content)
                thresholds = [
                    base_threshold,  # 基础阈值（0.88或0.85）
                    base_threshold - 0.05,  # 降低5%作为第二层
                    base_threshold - 0.08,  # 降低8%作为第三层
                    base_threshold - 0.10,  # 降低10%作为第四层（更宽松，识别更多相似语句）
                ]
                
                for threshold in thresholds:
                    sem_cached = await redis_service.search_similar_vector(
                        cache_key_prefix=sem_key_prefix,
                        embedding=embedding,
                        threshold=threshold,
                    )
                    if sem_cached:
                        sem_result = json.loads(sem_cached)
                        sem_result.setdefault("source", "cache_semantic")
                        sem_result["prompt_version_id"] = prompt_version_id
                        sem_result["decision_trace"] = trace + [{"step": "cache_semantic", "threshold": threshold}]
                        await self._mark_metric("semantic_hit")
                        logger.info(f"语义缓存命中 (阈值={threshold:.2f}): {optimized_content[:20]}...")
                        # 多智能体陪审团已注释，直接返回结果
                        return sem_result
        except Exception as e:
            logger.warning(f"Semantic cache failed: {e}")

        # ==================== Layer 2: 模型推理（通过模型注册表） ====================
        text_models = model_registry.get_text_model_priority()
        
        if not text_models:
            logger.debug("LLM_MODE=off 或未配置任何模型，返回默认结果")
            result = self.default_response.copy()
            result["prompt_version_id"] = prompt_version_id
            result["decision_trace"] = trace + [{"step": "llm_off"}]
            await self._mark_metric("llm_off")
            return result

        # 尝试按优先级使用模型
        for model_type in text_models:
            model_config = model_registry.get_model(model_type)
            if not model_config:
                continue
            
            try:
                # 预算检查已注释，不再检查预算限制
                # if model_type.startswith("cloud"):
                #     input_chars = len(optimized_content) + len(optimized_prompt)
                #     if not self._check_budget(video_id, input_chars):
                #         logger.warning(f"预算限制，跳过云端模型 {model_type}")
                #         result = self.default_response.copy()
                #         result["prompt_version_id"] = prompt_version_id
                #         result["decision_trace"] = trace + [{"step": "budget_exceeded"}]
                #         result["reason"] = "预算不足，需人工复核"
                #         return result
                
                # 调用模型
                if model_type == "cloud_text":
                    # 云端调用：可选采样/预算控制（本地推理仍可跑，云端只处理“不确定/高风险”）
                    # 注意：采样策略仅用于 hybrid（本地优先 + 云端兜底）以降本增效；
                    # cloud_only 模式下若采样跳过，会导致没有任何模型推理，影响“强制云端”的预期。
                    # 采样策略已注释，不再跳过云端模型调用
                    # if self.mode == "hybrid":
                    #     if not await token_optimizer.should_process_content(content, content_type, priority):
                    #         await self._mark_metric("cloud_skip_optimizer")
                    #         continue
                    logger.info(
                        "[AIText] cloud_try type=%s model=%s chars=%s",
                        content_type,
                        getattr(model_config, "name", "unknown"),
                        len(optimized_content),
                    )
                    await self._mark_metric("cloud_attempt")
                    # 获取云端模型专用提示词
                    cloud_prompt = self._get_prompt_for_model(content_type, "cloud_text")
                    result = await self._call_cloud_model(optimized_content, cloud_prompt, model_config)
                    if result:
                        # 预算更新已注释
                        # self._update_budget(video_id, input_chars)
                        await self._mark_metric("cloud_call")
                        # 记录Token使用
                        # await token_optimizer.record_token_usage(input_chars // 4)  # 粗略估算token数
                elif model_type == "local_text":
                    logger.info(
                        "[AIText] local_try type=%s model=%s chars=%s",
                        content_type,
                        getattr(model_config, "name", "unknown"),
                        len(optimized_content),
                    )
                    # 获取本地模型专用提示词
                    local_prompt = self._get_prompt_for_model(content_type, "local_text")
                    result = await self._call_local_model(
                        optimized_content,
                        content_type,
                        local_prompt,
                        model_config
                    )
                    if result:
                        await self._mark_metric("local_call")
                        # 升级逻辑已注释，不再检查是否需要升级到云端
                        # confidence = result.get("confidence", 0.5)
                        # min_chars = int(getattr(settings, "LOCAL_LLM_ESCALATE_MIN_CHARS", 0) or 0)
                        # if (len(optimized_content) >= min_chars and
                        #     model_registry.should_escalate_to_cloud(confidence) and
                        #     model_registry.is_available("cloud_text")):
                        #     logger.info(f"本地模型置信度低 ({confidence:.2f})，升级到云端模型")
                        #     cloud_config = model_registry.get_model("cloud_text")
                        #     if cloud_config and self._check_budget(video_id, input_chars):
                        #         # 升级云端：不走采样，属于"难内容补审"路径
                        #         cloud_result = await self._call_cloud_model(optimized_content, optimized_prompt, cloud_config)
                        #         if cloud_result:
                        #             self._update_budget(video_id, input_chars)
                        #             await self._mark_metric("cloud_call")
                        #             await token_optimizer.record_token_usage(input_chars // 4)
                        #             result = cloud_result
                        #             result["decision_trace"] = trace + [
                        #                 {"step": "local_llm", "confidence": confidence},
                        #                 {"step": "escalate_to_cloud"}
                        #             ]
                
                if result:
                    logger.info(
                        "[AIText] done type=%s source=%s model=%s score=%s conf=%s",
                        content_type,
                        result.get("source"),
                        result.get("model_name"),
                        result.get("score"),
                        result.get("confidence"),
                    )
                    result["prompt_version_id"] = prompt_version_id
                    result.setdefault("decision_trace", trace + [{"step": model_type}])
                    
                    # 优化输出
                    result = token_optimizer.optimize_llm_response(result)
                    
                    # 保存缓存
                    await self._save_cache(optimized_content, content_type, result, embedding, prompt_version_id)
                    
                    # 多智能体陪审团已注释，直接返回结果
                    return result
                    
            except Exception as e:
                logger.error(f"模型 {model_type} 调用失败: {e}")
                continue
        
        # 所有模型都失败，返回默认结果
        logger.warning("所有模型调用失败，返回默认结果")
        result = self.default_response.copy()
        result["prompt_version_id"] = prompt_version_id
        result["decision_trace"] = trace + [{"step": "all_models_failed"}]
        return result

    # 保持向后兼容的方法
    async def analyze_content(
        self,
        content: str,
        content_type: str,
        force_jury: bool = False,
        priority: str = "normal",
        video_id: Optional[int] = None,
    ) -> AIContentAnalysisResult:
        """向后兼容的分析方法"""
        # 手动触发/复核属于明确的人工操作：必须跳过采样跳过逻辑
        effective_priority = "high" if force_jury else priority
        return await self.analyze_content_with_policy(
            content=content,
            content_type=content_type,
            force_jury=force_jury,
            video_id=video_id,
            priority=effective_priority,
        )

    # ==================== 模型调用方法 ====================

    async def _call_cloud_model(self, content: str, system_prompt: str, model_config) -> Optional[AIContentAnalysisResult]:
        """调用云端模型"""
        if not model_config.api_key:
            logger.warning("云端模型 API_KEY 为空，跳过调用")
            return None
        
        # 云端模型：直接使用传入的提示词（已在调用处根据模型类型选择）
        # Prompt压缩已注释，不再使用
        # try:
        #     from app.services.ai.prompt_compressor import prompt_compressor
        #     budget_status = token_optimizer.get_budget_status()
        #     daily_usage = budget_status.get("daily", {}).get("usage_rate", 0.0)
        #     
        #     if daily_usage > 0.8:
        #         strategy = "aggressive"
        #     elif daily_usage > 0.5:
        #         strategy = "moderate"
        #     else:
        #         strategy = "conservative"
        #     
        #     original_len = len(system_prompt)
        #     compressed_prompt = prompt_compressor.compress_prompt(system_prompt, strategy, model_type="cloud")
        #     compressed_len = len(compressed_prompt)
        #     savings = (original_len - compressed_len) / original_len * 100 if original_len > 0 else 0
        #     
        #     logger.info(f"[CloudPrompt] 📝 Prompt压缩: 策略={strategy}, 原始={original_len}字符, 压缩后={compressed_len}字符, 节省={savings:.1f}%")
        # except Exception as e:
        #     logger.warning(f"[CloudPrompt] ⚠️  Prompt压缩失败，使用原始Prompt: {e}")
        #     compressed_prompt = system_prompt
        compressed_prompt = system_prompt
        
        headers = {
            "Authorization": f"Bearer {model_config.api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": compressed_prompt},
            {"role": "user", "content": f"输入内容: {content}"},
        ]

        payload = {
            "model": model_config.name,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512,
        }

        try:
            async with httpx.AsyncClient(timeout=model_config.timeout) as client:
                resp = await client.post(
                    f"{model_config.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.error(f"Cloud Model API Error {resp.status_code}: {resp.text}")
                    await self._mark_metric("cloud_http_error")
                    if 400 <= resp.status_code < 500:
                        await self._mark_metric("cloud_http_4xx")
                    if 500 <= resp.status_code < 600:
                        await self._mark_metric("cloud_http_5xx")
                    if resp.status_code == 429:
                        await self._mark_metric("cloud_http_429")
                    return None
                
                response_text = resp.json()["choices"][0]["message"]["content"]
                data = self._parse_json_from_text(response_text)
                if not data:
                    logger.warning(f"Cloud JSON parse failed: {response_text[:300]}...")
                    await self._mark_metric("cloud_parse_error")
                    return None

                result = self.default_response.copy()
                result.update(data)
                if "confidence" not in result and isinstance(result.get("score"), (int, float)):
                    result["confidence"] = max(0.0, min(1.0, result["score"] / 100))
                result["source"] = "cloud_llm"
                result["model_name"] = model_config.name
                return result
                
        except Exception as e:
            logger.error(f"Cloud model call failed: {e}")
            await self._mark_metric("cloud_exception")
            return None

    async def _call_local_model(
        self,
        content: str,
        content_type: str,
        system_prompt: str,
        model_config
    ) -> Optional[AIContentAnalysisResult]:
        """调用本地模型"""
        try:
            logger.info(f"[LLM] 调用本地文本模型: {model_config.name} @ {model_config.base_url}")
            local_result = await local_model_service.predict(
                content,
                content_type,
                system_prompt=system_prompt
            )
            if local_result:
                logger.info(f"[LocalLLM] score={local_result.get('score')}")

                final_result = {
                    "score": local_result.get("score", 60),
                    "category": local_result.get("category", "普通"),
                    "label": local_result.get("label", "普通"),
                    "reason": local_result.get("reason", "本地模型分析"),
                    "is_highlight": local_result.get("is_highlight", False),
                    "is_inappropriate": local_result.get("is_inappropriate", False),
                    "confidence": local_result.get("confidence", 0.5),
                    "source": "local_model",
                    "model_name": model_config.name,
                }
                return final_result
            else:
                logger.warning("本地模型返回空结果")
                return None

        except Exception as e:
            logger.error(f"Local model call failed: {e}")
            return None

    async def evaluate_with_prompt(
        self,
        content: str,
        content_type: str,
        system_prompt: str,
        model_source: str = "auto"
    ) -> Optional[AIContentAnalysisResult]:
        """Run a one-off evaluation with a custom prompt, without caching."""
        source = (model_source or "auto").lower()
        if source == "local":
            model_config = model_registry.get_model("local_text")
            if not model_config:
                return None
            return await self._call_local_model(content, content_type, system_prompt, model_config)
        if source == "cloud":
            model_config = model_registry.get_model("cloud_text")
            if not model_config:
                return None
            return await self._call_cloud_model(content, system_prompt, model_config)

        for model_type in model_registry.get_text_model_priority():
            if model_type == "local_text":
                model_config = model_registry.get_model("local_text")
                if not model_config:
                    continue
                result = await self._call_local_model(content, content_type, system_prompt, model_config)
            else:
                model_config = model_registry.get_model("cloud_text")
                if not model_config:
                    continue
                result = await self._call_cloud_model(content, system_prompt, model_config)
            if result:
                return result
        return None

    # ==================== 缓存辅助 ====================

    async def _save_cache(
        self,
        content: str,
        content_type: str,
        result: AIContentAnalysisResult,
        embedding,
        prompt_version_id: Optional[int] = None
    ):
        try:
            content_hash = self._get_content_hash(content, prompt_version_id)
            exact_cache_key = f"ai:analysis:{content_type}:{content_hash}"
            sem_prefix = f"ai:semcache:{content_type}"

            # 只保存精确缓存，延长TTL到30天
            cache_ttl = 30 * 24 * 3600  # 30天
            await redis_service.async_redis.setex(
                exact_cache_key,
                cache_ttl,
                json.dumps(result, ensure_ascii=False),
            )
            
            # 语义缓存：仅当 embedding 不为空时保存
            if embedding:
                try:
                    # 复用 search_similar_vector 的 key 规则
                    max_dim = settings.AI_VECTOR_DIMENSION
                    precision = settings.AI_VECTOR_QUANTIZATION_PRECISION
                    head = embedding[:min(len(embedding), max_dim)]
                    quantized = [f"{x:.{precision}f}" for x in head]
                    vector_key = "_".join(quantized)
                    sem_key = f"{sem_prefix}:{vector_key}"
                    await redis_service.async_redis.setex(
                        sem_key,
                        settings.AI_SEMANTIC_CACHE_TTL,
                        json.dumps(result, ensure_ascii=False),
                    )
                except Exception as e:
                    logger.warning(f"Semantic cache save failed: {e}")
            logger.debug(f"AI精确缓存已保存: {content[:10]}... TTL={cache_ttl}s")
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    # ==================== 多智能体陪审团（已注释，暂时不考虑） ====================
    # async def _maybe_use_jury(self, content: str, content_type: str, result: AIContentAnalysisResult, force_jury: bool = False) -> AIContentAnalysisResult:
    #     """
    #     根据配置和置信度决定是否触发多智能体陪审团。
    #     """
    #     if not force_jury:
    #         return result
    #     if not settings.MULTI_AGENT_ENABLED:
    #         return result
    #     service = _get_multi_agent_service()
    #     if not service:
    #         return result
    #     try:
    #         jury_result = await service.analyze_with_jury(content, content_type)
    #         if jury_result:
    #             # 保留原结果以便追踪
    #             jury_result.setdefault("source", "multi_agent")
    #             jury_result.setdefault("confidence", result.get("confidence", 0.5))
    #             jury_result.setdefault("model_name", result.get("model_name"))
    #             trace = result.get("decision_trace", [])
    #             jury_trace = jury_result.pop("decision_trace", [])
    #             jury_result["decision_trace"] = trace + [{"step": "multi_agent"}] + jury_trace
    #             await self._mark_metric("jury_call")
    #             return jury_result
    #     except Exception as e:
    #         logger.warning(f"Multi-agent analyze failed: {e}")
    #     return result

    # ==================== 规则过滤 ====================

    def _rule_based_filter(
        self, content: str, content_type: str
    ) -> Optional[AIContentAnalysisResult]:
        clean = content.strip()
        if not clean:
            return self.default_response

        if re.match(r"^\d+$", clean):
            return {
                **self.default_response,
                "score": 45,
                "category": "灌水",
                "label": "复读",
                "reason": "规则命中：纯数字",
            }

        if not re.search(r"[\u4e00-\u9fa5a-zA-Z0-9]", clean):
            return {
                **self.default_response,
                "score": 50,
                "category": "情绪表达",
                "label": "表情",
                "reason": "规则命中：纯符号/表情",
            }

        if len(clean) < 2:
            return {
                **self.default_response,
                "score": 40,
                "category": "无意义",
                "label": "过短",
                "reason": "规则命中：内容过短",
            }

        keywords = [
            k.strip()
            for k in settings.AI_LOW_VALUE_KEYWORDS.split(",")
            if k.strip()
        ]
        if any(k in clean for k in keywords):
            return {
                **self.default_response,
                "score": 50,
                "category": "情绪表达",
                "reason": "规则命中：低价值关键词",
            }

        return None

    # ==================== Prompt ====================

    def _build_prompt(self, content: str, content_type: str) -> list:
        system_prompt = (
            DANMAKU_SYSTEM_PROMPT
            if content_type == "danmaku"
            else COMMENT_SYSTEM_PROMPT
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"输入内容: {content}"},
        ]

    # ==================== 图像分析功能 ====================

    async def analyze_image(self, image_data: str, prompt: str = "请分析这张图片的内容") -> Optional[str]:
        """
        图像分析功能
        
        Args:
            image_data: base64编码的图像数据
            prompt: 分析提示词
            
        Returns:
            分析结果文本，失败返回None
        """
        if not self.use_cloud:
            logger.warning("图像分析需要云端模型支持，当前模式未启用云端")
            return None
        if not self.vision_api_key:
            logger.warning("LLM_VISION_API_KEY 为空，跳过图像分析")
            return None
            
        if not self.vision_model:
            logger.warning("未配置图像识别模型")
            return None

        headers = {
            "Authorization": f"Bearer {self.vision_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # 图像处理需要更长时间
                resp = await client.post(
                    f"{self.vision_base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.error(f"Vision API Error {resp.status_code}: {resp.text}")
                    return None
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Vision API call failed: {e}")
            return None

    # ==================== LLM API 调用 ====================

    async def _call_llm_api(self, messages: list) -> Optional[str]:
        """
        云端大模型API调用
        """
        if not self.api_key:
            logger.warning("LLM_API_KEY 为空，跳过云端调用")
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.error(f"LLM API Error {resp.status_code}: {resp.text}")
                    return None
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None

    # ==================== 解析 ====================

    def _parse_json_from_text(self, text: str) -> Optional[dict]:
        """
        从模型输出中尽量提取 JSON 对象。
        兼容：```json ... ``` + 额外说明/Markdown。
        """
        if not text:
            return None

        def _cleanup(candidate: str) -> str:
            c = (candidate or "").strip()
            # 兼容模型输出的“尾逗号”
            c = re.sub(r",\s*([}\]])", r"\1", c)
            return c

        # 1) 优先解析 fenced code block（通常最干净）
        try:
            for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE):
                candidate = _cleanup(m.group(1) or "")
                if not candidate:
                    continue
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
        except Exception:
            pass

        # 2) 去除 code fence 后直接 json.loads
        clean_text = _cleanup(re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE))
        try:
            obj = json.loads(clean_text)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # 3) 再退化：截取第一个 {...} 区间（与 local_model_service 同策略）
        try:
            start_obj = clean_text.find("{")
            end_obj = clean_text.rfind("}")
            if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
                obj = json.loads(clean_text[start_obj : end_obj + 1])
                if isinstance(obj, dict):
                    return obj
        except Exception:
            pass

        return None

    def _parse_response(
        self, response_text: str, content_type: str
    ) -> AIContentAnalysisResult:
        try:
            data = self._parse_json_from_text(response_text) or {}
            result = self.default_response.copy()
            result.update(data)
            # 补充缺省字段
            if "confidence" not in result and isinstance(result.get("score"), (int, float)):
                result["confidence"] = max(0.0, min(1.0, result["score"] / 100))
            return result
        except Exception:
            logger.warning(f"JSON parse error: {response_text}")
            return self.default_response

    # ==================== 异步任务 ====================

    async def process_danmaku_task(self, danmaku_id: int):
        # 队列模式：快速入队，避免高并发时网络/IO 阻塞
        if self.queue_enabled:
            await self.enqueue_analysis("danmaku", danmaku_id, priority="low")
            return

        await self._process_danmaku_task_immediate(danmaku_id)

    def _effective_priority(self, content_type: str, content: str, priority: str) -> str:
        """根据内容特征修正优先级，避免关键内容被采样跳过。"""
        clean = (content or "").strip()
        if content_type == "danmaku":
            # 长弹幕更可能需要语义缓存/本地模型分析；短弹幕仍可采样跳过
            min_len = int(getattr(settings, "DANMAKU_ANALYSIS_MIN_LEN", 20) or 20)
            if len(clean) >= min_len:
                return "high"
        return priority

    async def _process_danmaku_task_immediate(self, danmaku_id: int):
        db = SessionLocal()
        try:
            danmaku = db.query(Danmaku).filter(Danmaku.id == danmaku_id).first()
            if not danmaku:
                return

            priority = self._effective_priority("danmaku", danmaku.content, "low")
            result = await self.analyze_content_with_policy(
                danmaku.content,
                "danmaku",
                force_jury=False,
                priority=priority,
            )
            danmaku.ai_score = result.get("score", 60)
            danmaku.ai_category = result.get("category", "普通")
            danmaku.ai_reason = result.get("reason")
            danmaku.ai_confidence = result.get("confidence", 0.5)
            danmaku.ai_source = result.get("source")
            danmaku.ai_prompt_version_id = result.get("prompt_version_id")
            danmaku.ai_model = result.get("model_name")
            trace = result.get("decision_trace")
            if trace and self._should_store_trace(result):
                try:
                    danmaku.ai_trace = json.dumps(trace, ensure_ascii=False)
                except Exception:
                    danmaku.ai_trace = None
            danmaku.is_highlight = (
                result.get("is_highlight", False) or danmaku.ai_score >= 90
            )
            db.commit()
        except Exception as e:
            logger.error(f"Danmaku task error: {e}")
            db.rollback()
        finally:
            db.close()

    async def process_comment_task(self, comment_id: int):
        # 队列模式：快速入队，避免高并发时网络/IO 阻塞
        if self.queue_enabled:
            await self.enqueue_analysis("comment", comment_id, priority="low")
            return

        await self._process_comment_task_immediate(comment_id)

    async def _process_comment_task_immediate(self, comment_id: int):
        db = SessionLocal()
        try:
            comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if not comment:
                return

            result = await self.analyze_content_with_policy(comment.content, "comment", force_jury=False, priority="low")
            comment.ai_score = result.get("score", 60)
            comment.ai_label = result.get("label", "普通")
            comment.ai_reason = result.get("reason")
            # 整型存储：乘以 100
            conf = result.get("confidence", 0.5)
            comment.ai_confidence = int(conf * 100) if conf is not None else None
            comment.ai_source = result.get("source")
            comment.ai_prompt_version_id = result.get("prompt_version_id")
            comment.ai_model = result.get("model_name")
            trace = result.get("decision_trace")
            if trace and self._should_store_trace(result):
                try:
                    comment.ai_trace = json.dumps(trace, ensure_ascii=False)
                except Exception:
                    comment.ai_trace = None
            db.commit()
        except Exception as e:
            logger.error(f"Comment task error: {e}")
            db.rollback()
        finally:
            db.close()


# ==================== 全局实例 ====================

llm_service = LLMService()
