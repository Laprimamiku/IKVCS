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
from typing import Optional

from app.core.config import settings
from app.core.types import AIContentAnalysisResult
from app.core.database import SessionLocal
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.services.ai.prompts import (
    DANMAKU_SYSTEM_PROMPT,
    COMMENT_SYSTEM_PROMPT
)
from app.services.cache.redis_service import redis_service
# from app.services.ai.embedding_service import embedding_service  # 暂时注释，采用简化缓存方案
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
        # 云端大模型配置（已注释，暂时不使用）
        # self.api_key = settings.LLM_API_KEY
        # self.base_url = settings.LLM_BASE_URL
        # self.model = settings.LLM_MODEL
        self.timeout = 30.0  # 保留 timeout，可能被其他方法使用

        self.default_response: AIContentAnalysisResult = {
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

    async def analyze_content(self, content: str, content_type: str) -> AIContentAnalysisResult:
        """
        智能内容分析（简化架构 - 仅使用本地模型）

        Layer 1   : 规则过滤
        Layer 1.5 : 精确缓存（MD5）
        Layer 2   : 本地模型（Local LLM）
        
        注：云端大模型调用已注释，暂时不使用
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

        # ==================== Layer 2: 本地模型 ====================
        if not settings.LOCAL_LLM_ENABLED:
            logger.warning("本地模型未启用，返回默认结果")
            return self.default_response

        try:
            local_result = await local_model_service.predict(content, content_type)
            if local_result:
                logger.info(f"[LocalLLM] score={local_result.get('score')}")

                final_result = {
                    "score": local_result.get("score", 60),
                    "category": local_result.get("category", "普通"),
                    "label": local_result.get("label", "普通"),
                    "reason": local_result.get("reason", "本地模型分析"),
                    "is_highlight": local_result.get("is_highlight", False),
                    "is_inappropriate": local_result.get("is_inappropriate", False),
                }

                # 保存缓存
                await self._save_cache(
                    content, content_type, final_result, None
                )
                return final_result
            else:
                logger.warning("本地模型返回空结果，返回默认结果")
                return self.default_response

        except Exception as e:
            logger.error(f"Local LLM failed: {e}")
            return self.default_response

        # ==================== Layer 3: 云端大模型（已注释，暂时不使用）====================
        # messages = self._build_prompt(content, content_type)
        # response_text = await self._call_llm_api(messages)
        # if not response_text:
        #     return self.default_response
        #
        # result = self._parse_response(response_text, content_type)
        # await self._save_cache(content, content_type, result, None)
        # return result

    # ==================== 缓存辅助 ====================

    async def _save_cache(
        self,
        content: str,
        content_type: str,
        result: AIContentAnalysisResult,
        embedding  # 保留参数但暂时不使用
    ):
        try:
            content_hash = self._get_content_hash(content)
            exact_cache_key = f"ai:analysis:{content_type}:{content_hash}"
            # sem_prefix = f"ai:semcache:{content_type}"

            # 暂时注释语义缓存保存
            # if embedding is not None:
            #     await redis_service.save_vector_result(
            #         cache_key_prefix=sem_prefix,
            #         embedding=embedding,
            #         result_json=json.dumps(result),
            #         ttl=settings.AI_SEMANTIC_CACHE_TTL,
            #     )

            # 只保存精确缓存，延长TTL到30天
            cache_ttl = 30 * 24 * 3600  # 30天
            await redis_service.async_redis.setex(
                exact_cache_key,
                cache_ttl,
                json.dumps(result),
            )
            logger.debug(f"AI精确缓存已保存: {content[:10]}... TTL={cache_ttl}s")
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

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

    # ==================== LLM API（已注释云端调用，暂时不使用）====================

    async def _call_llm_api(self, messages: list) -> Optional[str]:
        """
        云端大模型API调用（已注释，暂时不使用）
        
        注意：其他服务可能仍在使用此方法，因此保留方法签名
        但实际API调用已注释，返回 None
        """
        # 云端大模型调用已注释，暂时不使用
        # headers = {
        #     "Authorization": f"Bearer {self.api_key}",
        #     "Content-Type": "application/json",
        # }
        #
        # payload = {
        #     "model": self.model,
        #     "messages": messages,
        #     "temperature": 0.3,
        #     "max_tokens": 512,
        # }
        #
        # try:
        #     async with httpx.AsyncClient(timeout=self.timeout) as client:
        #         resp = await client.post(
        #             f"{self.base_url}/chat/completions",
        #             json=payload,
        #             headers=headers,
        #         )
        #         if resp.status_code != 200:
        #             logger.error(f"LLM API Error {resp.status_code}: {resp.text}")
        #             return None
        #         return resp.json()["choices"][0]["message"]["content"]
        # except Exception as e:
        #     logger.error(f"LLM API call failed: {e}")
        #     return None
        
        logger.warning("云端大模型调用已禁用，返回 None")
        return None

    # ==================== 解析 ====================

    def _parse_response(
        self, response_text: str, content_type: str
    ) -> AIContentAnalysisResult:
        try:
            clean = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            result = self.default_response.copy()
            result.update(data)
            return result
        except Exception:
            logger.warning(f"JSON parse error: {response_text}")
            return self.default_response

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
