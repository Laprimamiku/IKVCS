"""Embedding 向量服务

基于 Zhipu AI Embedding 模型的封装，
用于为弹幕/评论文本生成语义向量，
后续可结合 Redis / 向量数据库做语义缓存或相似度搜索。

模型配置通过 settings.EMBEDDING_MODEL 读取，默认使用 embedding-3-pro。
"""

import logging
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Zhipu Embedding 服务封装

    说明：
    - 模型名称从配置读取（settings.EMBEDDING_MODEL）
    - 使用异步 HTTP 客户端，兼容 FastAPI 的 async 调用链
    - 对网络错误、超时、返回结构异常做统一兜底
    """

    def __init__(self) -> None:
        # 从配置中读取 API 相关信息，避免硬编码
        # 目前与 LLM 共用同一套 API KEY / BASE_URL
        self.api_key: str = settings.LLM_API_KEY
        self.base_url: str = settings.LLM_BASE_URL.rstrip("/")

        # 从配置读取 Embedding 模型名称
        self.model: str = settings.EMBEDDING_MODEL

        # 请求超时时间（秒），可根据线上稳定性再做调整
        self.timeout: float = 15.0

    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """为单段文本生成向量表示

        参数说明：
        - text: 需要做语义缓存 / 相似度搜索的原始文本

        返回：
        - 成功时返回一维向量 (List[float])
        - 失败时返回 None，并在日志中记录详细原因
        """
        # 简单防御：空字符串或全是空白时直接返回 None
        clean_text = text.strip()
        if not clean_text:
            logger.warning("EmbeddingService: 空文本，不生成向量")
            return None

        headers = {
            # Zhipu 兼容 OpenAI 风格的认证方式
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            # 指定使用的向量模型
            "model": self.model,
            # 这里使用单条输入，后续如需要批量可以扩展新的接口
            "input": clean_text,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers,
                )

            if resp.status_code != 200:
                # 将状态码和返回内容打印出来，便于线上排查
                logger.error(
                    "EmbeddingService: 请求失败 status=%s, body=%s",
                    resp.status_code,
                    resp.text,
                )
                return None

            data = resp.json()

            # Zhipu 兼容 OpenAI Embeddings 返回格式：data[0].embedding
            try:
                embedding: List[float] = data["data"][0]["embedding"]
            except (KeyError, IndexError, TypeError) as e:
                logger.error("EmbeddingService: 解析返回结构失败: %s, body=%s", e, data)
                return None

            # 额外做一次长度检查（可选），有助于在模型升级时观察向量维度变化
            if not isinstance(embedding, list) or not embedding:
                logger.error("EmbeddingService: 返回向量为空或类型异常: %s", type(embedding))
                return None

            return embedding

        except httpx.ReadTimeout:
            # 读超时：属于常见网络问题，写成 warning 即可
            logger.warning("EmbeddingService: 调用超时 (ReadTimeout)")
            return None
        except httpx.RequestError as e:
            # RequestError 覆盖 DNS 解析失败、连接失败等情况
            logger.error("EmbeddingService: 网络请求异常: %s", e)
            return None
        except Exception as e:  # 防御性兜底，避免影响主流程
            logger.error("EmbeddingService: 未知异常: %s", e)
            return None


# 全局单例，供其他模块直接导入使用
embedding_service = EmbeddingService()
