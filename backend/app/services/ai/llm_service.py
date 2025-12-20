"""
LLM 智能分析服务
需求：8.1-8.5, 10.1-10.4, 20.1-20.4

功能：
1. 弹幕 / 评论智能评分与分类
2. 规则预过滤，减少 LLM Token 消耗
3. Prompt 模板化
4. 结果结构化解析
5. Redis 精确缓存 + 语义缓存
6. 本地小模型 + 云端大模型协同
7. 异步后台任务，直接更新数据库
"""

import httpx
import json
import logging
import hashlib
import re
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.models.ai_training_sample import AiTrainingSample
from app.services.ai.prompts import (
    DANMAKU_SYSTEM_PROMPT,
    COMMENT_SYSTEM_PROMPT
)
from app.services.cache.redis_service import redis_service
from app.services.ai.embedding_service import embedding_service
from app.services.ai.local_model_service import local_model_service

logger = logging.getLogger(__name__)

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
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.timeout = 30.0

        self.default_response = {
            "score": 60,
            "category": "普通",
            "label": "普通",
            "reason": "默认处理",
            "is_highlight": False,
            "is_inappropriate": False
        }

    # ==================== 工具方法 ====================

    def _get_content_hash(self, content: str) -> str:
        return hashlib.md5(content.strip().encode("utf-8")).hexdigest()

    # ==================== 核心分析流程 ====================

    async def analyze_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        智能内容分析（三层架构 + 本地小模型协同）

        Layer 1   : 规则过滤
        Layer 1.5 : 精确缓存（MD5）
        Layer 2   : 语义缓存（Embedding）
        Layer 2.5 : 本地小模型（Local LLM）
        Layer 3   : 云端大模型（Cloud LLM）
        """
        if not content:
            return self.default_response

        # ==================== Layer 1: 规则过滤 ====================
        pre_check = self._rule_based_filter(content, content_type)
        if pre_check:
            return pre_check

        # ==================== Layer 1.5: 精确缓存 ====================
        content_hash = self._get_content_hash(content)
        exact_cache_key = f"ai:analysis:{content_type}:{content_hash}"

        try:
            cached = await redis_service.async_redis.get(exact_cache_key)
            if cached:
                logger.info(f"AI Exact Cache Hit: {content[:10]}...")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Exact cache read failed: {e}")

        # ==================== Layer 2: 语义缓存 ====================
        embedding = await embedding_service.get_text_embedding(content)
        sem_prefix = f"ai:semcache:{content_type}"

        if embedding is not None:
            sem_cached = await redis_service.search_similar_vector(
                cache_key_prefix=sem_prefix,
                embedding=embedding,
                threshold=settings.AI_SEMANTIC_CACHE_THRESHOLD,
            )
            if sem_cached:
                try:
                    result = json.loads(sem_cached)
                    await redis_service.async_redis.setex(
                        exact_cache_key,
                        settings.AI_SEMANTIC_CACHE_TTL,
                        json.dumps(result),
                    )
                    logger.info(f"AI Semantic Cache Hit: {content[:10]}...")
                    return result
                except Exception:
                    logger.warning("Semantic cache parse error")

        # ==================== Layer 2.5: 本地小模型 ====================
        local_result = None
        should_use_cloud = True

        if settings.LOCAL_LLM_ENABLED:
            try:
                local_result = await local_model_service.predict(content, content_type)
                if local_result:
                    confidence = local_result.get("confidence", 0.0)
                    threshold = settings.LOCAL_LLM_THRESHOLD_HIGH / 100.0

                    logger.info(
                        f"[LocalLLM] score={local_result.get('score')} conf={confidence:.2f}"
                    )

                    if confidence >= threshold:
                        logger.info("✅ 本地模型高置信度命中，跳过云端")

                        final_result = {
                            "score": local_result["score"],
                            "category": local_result["category"],
                            "label": local_result["label"],
                            "reason": local_result.get("reason", "本地模型分析"),
                        }

                        await self._save_training_sample(
                            content, local_result, "local_hit"
                        )
                        await self._save_cache(
                            content, content_type, final_result, embedding
                        )
                        return final_result

            except Exception as e:
                logger.error(f"Local LLM failed, downgrade: {e}")

        # ==================== Layer 3: 云端大模型 ====================
        messages = self._build_prompt(content, content_type)
        response_text = await self._call_llm_api(messages)
        if not response_text:
            return self.default_response

        result = self._parse_response(response_text, content_type)

        if local_result:
            await self._save_training_sample(content, local_result, "local_low_conf")
            await self._save_training_sample(content, result, "cloud_final")

        await self._save_cache(content, content_type, result, embedding)
        return result

    # ==================== 缓存辅助 ====================

    async def _save_cache(
        self,
        content: str,
        content_type: str,
        result: Dict[str, Any],
        embedding
    ):
        try:
            content_hash = self._get_content_hash(content)
            exact_cache_key = f"ai:analysis:{content_type}:{content_hash}"
            sem_prefix = f"ai:semcache:{content_type}"

            if embedding is not None:
                await redis_service.save_vector_result(
                    cache_key_prefix=sem_prefix,
                    embedding=embedding,
                    result_json=json.dumps(result),
                    ttl=settings.AI_SEMANTIC_CACHE_TTL,
                )

            await redis_service.async_redis.setex(
                exact_cache_key,
                settings.AI_SEMANTIC_CACHE_TTL,
                json.dumps(result),
            )
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    # ==================== 规则过滤 ====================

    def _rule_based_filter(
        self, content: str, content_type: str
    ) -> Optional[Dict[str, Any]]:
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

    # ==================== LLM API ====================

    async def _call_llm_api(self, messages: list) -> Optional[str]:
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

    def _parse_response(
        self, response_text: str, content_type: str
    ) -> Dict[str, Any]:
        try:
            clean = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            result = self.default_response.copy()
            result.update(data)
            return result
        except Exception:
            logger.warning(f"JSON parse error: {response_text}")
            return self.default_response

    # ==================== 训练样本 ====================

    async def _save_training_sample(
        self, content: str, result: Dict[str, Any], source_tag: str
    ):
        try:
            db = SessionLocal()
            try:
                model_name = (
                    settings.LLM_MODEL
                    if source_tag == "cloud_final"
                    else settings.LOCAL_LLM_MODEL
                )
                sample = AiTrainingSample(
                    content=content,
                    ai_score=result.get("score", 0),
                    ai_category=result.get("category", "unknown"),
                    ai_label=result.get("label", "unknown"),
                    source_model=model_name,
                    local_confidence=result.get("confidence", 1.0),
                )
                db.add(sample)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Save training sample failed: {e}")

    # ==================== 异步任务 ====================

    async def process_danmaku_task(self, danmaku_id: int):
        db = SessionLocal()
        try:
            danmaku = db.query(Danmaku).filter(Danmaku.id == danmaku_id).first()
            if not danmaku:
                return

            result = await self.analyze_content(danmaku.content, "danmaku")
            danmaku.ai_score = result.get("score", 60)
            danmaku.ai_category = result.get("category", "普通")
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
        db = SessionLocal()
        try:
            comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if not comment:
                return

            result = await self.analyze_content(comment.content, "comment")
            comment.ai_score = result.get("score", 60)
            comment.ai_label = result.get("label", "普通")
            db.commit()
        except Exception as e:
            logger.error(f"Comment task error: {e}")
            db.rollback()
        finally:
            db.close()


# ==================== 全局实例 ====================

llm_service = LLMService()
