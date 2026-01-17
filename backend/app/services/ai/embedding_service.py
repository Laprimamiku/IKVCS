"""Embedding vector service – wraps local Ollama qwen3-embedding:0.6b."""

import asyncio
import logging
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Ollama Embedding 封装"""

    def __init__(self) -> None:
        self.base_url: str = settings.EMBEDDING_BASE_URL.rstrip("/")
        self.model: str = settings.EMBEDDING_MODEL
        self.timeout: float = 15.0
        self.max_retries: int = 3
        self.retry_backoff: float = 1.5

    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding via local Ollama /api/embeddings."""
        clean_text = text.strip()
        if not clean_text:
            logger.warning("EmbeddingService: 空文本，不生成向量")
            return None
        if not self.base_url or not self.model:
            logger.error("EmbeddingService: 基础配置缺失，跳过向量生成")
            return None

        payload = {"model": self.model, "prompt": clean_text}
        logger.info(f"[Embedding] 调用模型: {self.model} @ {self.base_url}")

        for attempt in range(1, self.max_retries + 1):
            try:
                # trust_env=False: avoid routing localhost through system proxy (can cause 502 with empty body)
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json=payload,
                    )
            except httpx.ReadTimeout:
                logger.warning(
                    "EmbeddingService: 调用超时 (attempt %s/%s)",
                    attempt,
                    self.max_retries,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * attempt)
                    continue
                return None
            except httpx.RequestError as e:
                logger.error(
                    "EmbeddingService: 网络请求异常 (attempt %s/%s): %s",
                    attempt,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * attempt)
                    continue
                return None

            if resp.status_code != 200:
                error_detail = resp.text[:500] if resp.text else "无响应内容"
                logger.error(
                    "EmbeddingService: 请求失败 status=%s, body=%s",
                    resp.status_code,
                    error_detail,
                )
                # 如果是404，可能是模型名称错误，提供更详细的错误信息
                if resp.status_code == 404:
                    logger.error(f"EmbeddingService: 模型 '{self.model}' 可能不存在，请检查Ollama中的模型名称。可用命令: ollama list")
                # 对 5xx 进行快速重试，其它错误直接返回
                if attempt < self.max_retries and resp.status_code >= 500:
                    await asyncio.sleep(self.retry_backoff * attempt)
                    continue
                return None

            try:
                data = resp.json()
            except ValueError as e:
                logger.error("EmbeddingService: 解析返回 JSON 失败: %s", e)
                return None

            embedding = data.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                logger.error("EmbeddingService: 返回向量为空或类型异常")
                return None

            return embedding

        return None


# 全局单例，供其他模块直接导入使用
embedding_service = EmbeddingService()
