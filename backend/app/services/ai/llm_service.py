"""
LLM 智能分析服务
需求：8.1-8.5, 10.1-10.4, 20.1-20.4

功能：
1. 弹幕 / 评论智能评分与分类
2. 规则预过滤，减少 LLM Token 消耗
3. Prompt 模板化
4. 结果结构化解析
5. Redis 缓存（内容指纹级别）
6. 异步后台任务，直接更新数据库
"""

import httpx
import json
import logging
import hashlib
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.services.ai.prompts import (
    DANMAKU_SYSTEM_PROMPT,
    COMMENT_SYSTEM_PROMPT
)
from app.services.cache.redis_service import redis_service

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.timeout = 30.0

        # 兜底响应（任何异常都会回落到这里）
        self.default_response = {
            "score": 60,
            "category": "普通",
            "label": "普通",
            "reason": "默认处理",
            "is_highlight": False,
            "is_inappropriate": False
        }

    # ==================== 核心分析流程 ====================

    def _get_content_hash(self, content: str) -> str:
        """计算内容指纹，用于 Redis 缓存"""
        return hashlib.md5(content.strip().encode("utf-8")).hexdigest()

    async def analyze_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        优化后的分析流程：
        Redis 缓存 → 规则预过滤 → LLM → 结果缓存
        """
        if not content:
            return self.default_response

        # 0. Redis Cache Look-aside
        content_hash = self._get_content_hash(content)
        cache_key = f"ai:analysis:{content_type}:{content_hash}"

        cached_result = await redis_service.async_redis.get(cache_key)
        if cached_result:
            try:
                logger.info(f"AI Cache Hit: {content[:10]}...")
                return json.loads(cached_result)
            except Exception:
                pass

        # 1. 规则预过滤
        pre_check = self._rule_based_filter(content, content_type)
        if pre_check:
            await redis_service.async_redis.setex(
                cache_key,
                86400 * 7,
                json.dumps(pre_check)
            )
            return pre_check

        # 2. 构建 Prompt
        messages = self._build_prompt(content, content_type)

        # 3. 调用 LLM
        response_text = await self._call_llm_api(messages)
        if not response_text:
            return self.default_response

        # 4. 解析结果
        result = self._parse_response(response_text, content_type)

        # 5. 写入缓存（7 天）
        await redis_service.async_redis.setex(
            cache_key,
            86400 * 7,
            json.dumps(result)
        )

        return result

    # ==================== 规则过滤 ====================

    def _rule_based_filter(self, content: str, content_type: str) -> Optional[Dict[str, Any]]:
        """
        低成本规则过滤，避免无意义内容调用 LLM
        """
        clean_content = content.strip()
        if not clean_content:
            return self.default_response

        # 从配置读取低价值关键词列表
        keywords_str = settings.AI_LOW_VALUE_KEYWORDS
        low_value_keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

        if len(clean_content) < 4:
            if clean_content.isdigit() or any(k in clean_content for k in low_value_keywords):
                return {
                    **self.default_response,
                    "score": 50,
                    "category": "情绪表达",
                    "reason": "规则命中：常见短内容",
                    "is_highlight": False
                }

        return None

    # ==================== Prompt 构建 ====================

    def _build_prompt(self, content: str, content_type: str) -> list:
        if content_type == "danmaku":
            system_prompt = DANMAKU_SYSTEM_PROMPT
        else:
            system_prompt = COMMENT_SYSTEM_PROMPT

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"输入内容: {content}"}
        ]

    # ==================== LLM API 调用 ====================

    async def _call_llm_api(self, messages: list) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 300
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )

                if resp.status_code != 200:
                    logger.error(f"LLM API Error {resp.status_code}: {resp.text}")
                    return None

                data = resp.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LLM API Call Failed: {e}")
            return None

    # ==================== 结果解析 ====================

    def _parse_response(self, response_text: str, content_type: str) -> Dict[str, Any]:
        try:
            clean_text = (
                response_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            data = json.loads(clean_text)

            result = self.default_response.copy()
            result.update(data)

            result["category"] = str(result.get("category", "普通"))
            result["label"] = str(result.get("label", "普通"))

            return result

        except json.JSONDecodeError:
            logger.warning(f"JSON Parse Error: {response_text}")
            return self.default_response

    # ==================== 异步任务处理 ====================

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

            if "reason" in result:
                logger.info(
                    f"[AI] Danmaku {danmaku_id} Reason: {result['reason']}"
                )

            db.commit()

        except Exception as e:
            logger.error(f"Danmaku Task Error {danmaku_id}: {e}")
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

            if "reason" in result:
                logger.info(
                    f"[AI] Comment {comment_id} Reason: {result['reason']}"
                )

            db.commit()

        except Exception as e:
            logger.error(f"Comment Task Error {comment_id}: {e}")
            db.rollback()
        finally:
            db.close()


# 全局实例
llm_service = LLMService()
