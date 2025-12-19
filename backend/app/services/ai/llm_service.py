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
import re
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
from app.services.ai.embedding_service import embedding_service

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

        # 0. Layer 1 - 规则预过滤（本地正则）
        pre_check = self._rule_based_filter(content, content_type)
        if pre_check:
            return pre_check

        # 0.5 Layer 1.5 - 精确内容指纹缓存（MD5）
        # 说明：
        # - 用于处理「完全相同文本」的重复调用场景
        # - 不依赖向量检索，命中则直接返回结果，完全避免 Embedding / LLM 再次调用
        content_hash = self._get_content_hash(content)
        exact_cache_key = f"ai:analysis:{content_type}:{content_hash}"

        try:
            exact_cached = await redis_service.async_redis.get(exact_cache_key)
            if exact_cached:
                try:
                    logger.info(f"AI Exact Cache Hit: {content[:10]}...")
                    return json.loads(exact_cached)
                except Exception:
                    logger.warning("AI Exact Cache Parse Error")
        except Exception as e:
            # 精确缓存失败不影响主流程，只记录日志
            logger.warning(f"AI Exact Cache Read Failed: {e}")

        # 1. Layer 2 - 语义缓存（Embedding + Redis）
        # 1.1 生成 Embedding 向量
        # 说明：如果向量生成失败，不中断流程，直接进入 LLM 调用
        embedding = await embedding_service.get_text_embedding(content)

        # 为不同内容类型设置不同的缓存前缀，避免互相污染
        sem_prefix = f"ai:semcache:{content_type}"

        # 如果拿到了向量，则尝试用语义缓存命中
        if embedding is not None:
            sem_cached = await redis_service.search_similar_vector(
                cache_key_prefix=sem_prefix,
                embedding=embedding,
                threshold=settings.AI_SEMANTIC_CACHE_THRESHOLD,
            )
            if sem_cached:
                try:
                    logger.info(f"AI Semantic Cache Hit: {content[:10]}...")
                    result = json.loads(sem_cached)
                    # 重要：命中语义缓存时，也要写入精确缓存（MD5），确保下次能直接命中精确缓存
                    try:
                        await redis_service.async_redis.setex(
                            exact_cache_key,
                            settings.AI_SEMANTIC_CACHE_TTL,
                            json.dumps(result),
                        )
                        logger.debug(f"AI Exact Cache Written (from semantic cache): {content[:10]}...")
                    except Exception:
                        logger.warning("AI Exact Cache Write Failed (from semantic cache)")
                    return result
                except Exception:
                    # 解析失败不影响主流程，只打印日志
                    logger.warning("AI Semantic Cache Parse Error")

        # 2. 构建 Prompt
        messages = self._build_prompt(content, content_type)

        # 3. 调用 LLM
        response_text = await self._call_llm_api(messages)
        if not response_text:
            return self.default_response

        # 4. 解析结果
        result = self._parse_response(response_text, content_type)

        # 5. Layer 2 - 将本次 LLM 结果写入缓存（语义缓存 + 精确内容缓存）
        try:
            # 5.1 写入语义缓存：只有在 embedding 存在时才写入，保证 Key 构造一致
            if embedding is not None:
                await redis_service.save_vector_result(
                    cache_key_prefix=sem_prefix,
                    embedding=embedding,
                    result_json=json.dumps(result),
                    ttl=settings.AI_SEMANTIC_CACHE_TTL,
                )

            # 5.2 写入精确内容指纹缓存（MD5）
            await redis_service.async_redis.setex(
                exact_cache_key,
                settings.AI_SEMANTIC_CACHE_TTL,
                json.dumps(result),
            )
        except Exception:
            # 缓存写入失败不影响主流程
            logger.warning("AI Cache Save Failed")

        return result

    # ==================== 规则过滤 ====================

    def _rule_based_filter(self, content: str, content_type: str) -> Optional[Dict[str, Any]]:
        """
        低成本规则过滤，避免无意义内容调用 LLM
        """
        clean_content = content.strip()
        if not clean_content:
            return self.default_response

        # MODIFIED: Layer 1 - 本地正则规则
        # 1. 纯数字 (e.g., "666", "2333")
        if re.match(r'^\d+$', clean_content):
            return {
                **self.default_response,
                "score": 45,
                "category": "灌水",
                "label": "复读",
                "reason": "规则命中：纯数字",
                "is_highlight": False
            }

        # 2. 纯 Emoji / 符号 (如果内容不包含任何中英文数字)
        # [\u4e00-\u9fa5] 汉字, [a-zA-Z0-9] 字母数字
        if not re.search(r'[\u4e00-\u9fa5a-zA-Z0-9]', clean_content):
            return {
                **self.default_response,
                "score": 50,
                "category": "情绪表达",
                "label": "表情",
                "reason": "规则命中：纯表情/符号",
                "is_highlight": False
            }

        # 3. 超短文本 (< 2 chars)
        if len(clean_content) < 2:
            return {
                **self.default_response,
                "score": 40,
                "category": "无意义",
                "label": "过短",
                "reason": "规则命中：内容过短",
                "is_highlight": False
            }

        # 从配置读取低价值关键词列表
        keywords_str = settings.AI_LOW_VALUE_KEYWORDS
        low_value_keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

        # 关键词匹配
        if any(k in clean_content for k in low_value_keywords):
            return {
                **self.default_response,
                "score": 50,
                "category": "情绪表达",
                "reason": "规则命中：常见关键词",
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
            "temperature": 0.3,  # MODIFIED: 适度提高以处理多样化表达
            "max_tokens": 512    # MODIFIED: 增加输出长度限制
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
