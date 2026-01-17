import asyncio
import httpx
import json
import logging
import re
from typing import Optional

from app.core.config import settings
from app.core.types import AIContentAnalysisResult
from app.services.ai.prompts import COMMENT_SYSTEM_PROMPT, DANMAKU_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LocalModelService:
    """
    本地小模型服务 (Ollama)

    职责：
    1. 调用本地 Ollama API 进行推理
    2. 解析非结构化的 LLM 输出为 JSON
    3. 计算简单的置信度
    """

    def __init__(self):
        self.base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.model = settings.LOCAL_LLM_MODEL
        self.timeout = settings.LOCAL_LLM_TIMEOUT
        self.mode = getattr(settings, "LLM_MODE", "hybrid").lower()
        self.max_concurrent = getattr(settings, "LOCAL_LLM_MAX_CONCURRENT", 1)
        self._semaphore = asyncio.Semaphore(max(1, self.max_concurrent))

    async def predict(
        self,
        content: str,
        content_type: str,
        system_prompt: Optional[str] = None
    ) -> Optional[AIContentAnalysisResult]:
        """
        调用本地模型进行预测。

        返回:
            - Dict: 预测结果（包含 score, category, label, confidence 等）
            - None: 调用失败/超时/解析错误则返回 None
        """
        # 模式与开关判定
        mode = self.mode
        if mode == "off":
            logger.debug("LLM_MODE=off，跳过本地模型调用")
            return None
        if mode == "cloud_only":
            logger.debug("LLM_MODE=cloud_only，跳过本地模型调用")
            return None
        # LLM_MODE 已是单一事实来源：hybrid/local_only 允许本地模型；如需禁用本地模型请改为 cloud_only/off
        if not self.base_url or not self.model:
            return None

        # 1. 准备提示词
        system_prompt = system_prompt or self._get_system_prompt(content_type)
        json_instruction = "\n请务必只返回 JSON 格式结果，不要包含 Markdown 标记或其他解释文本。"

        try:
            async with self._semaphore:
                logger.info(f"[LocalLLM] 调用本地文本模型: {self.model} @ {self.base_url}")
                # trust_env=False: avoid routing localhost through system proxy (can cause 502 with empty body)
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_prompt + json_instruction},
                                {"role": "user", "content": f"输入内容: {content}"},
                            ],
                            "temperature": 0.1,
                            "max_tokens": 256,
                            "stream": False,
                        },
                    )

                    if response.status_code != 200:
                        error_detail = response.text[:500] if response.text else "无响应内容"
                        logger.warning(f"[LocalLLM] 调用失败: {response.status_code} - {error_detail}")
                        # 如果是404，可能是模型名称错误，提供更详细的错误信息
                        if response.status_code == 404:
                            logger.error(f"[LocalLLM] 模型 '{self.model}' 可能不存在，请检查Ollama中的模型名称。可用命令: ollama list")
                        return None

                    result_json = response.json()
                    if "choices" not in result_json or not result_json["choices"]:
                        logger.warning(f"[LocalLLM] 响应格式异常: {result_json}")
                        return None
                    
                    result_text = result_json["choices"][0]["message"]["content"]

                    # 2. 解析结果
                    parsed_result = self._parse_json_safely(result_text)
                    if not parsed_result:
                        return None

                    # 3. 补充元数据和置信度
                    score = parsed_result.get("score")
                    confidence = parsed_result.get("confidence")
                    if confidence is None and isinstance(score, (int, float)):
                        confidence = max(0.0, min(1.0, score / 100))
                    parsed_result["confidence"] = confidence if confidence is not None else 0.5
                    parsed_result["source"] = "local_model"
                    parsed_result["model_name"] = self.model

                    return parsed_result

        except httpx.TimeoutException:
            logger.warning(f"[LocalLLM] 请求超时 ({self.timeout}s)")
            return None
        except Exception as e:  # noqa: BLE001
            logger.error(f"[LocalLLM] 发生异常: {e}")
            return None

    def _get_system_prompt(self, content_type: str) -> str:
        return COMMENT_SYSTEM_PROMPT if content_type == "comment" else DANMAKU_SYSTEM_PROMPT

    def _parse_json_safely(self, text: str) -> Optional[AIContentAnalysisResult]:
        """鲁棒解析 JSON，兼容模型输出的 Markdown 代码块。"""
        try:
            clean_text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # 尝试截取第一个 JSON 对象/数组
            try:
                start_obj = clean_text.find("{")
                end_obj = clean_text.rfind("}")
                if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
                    return json.loads(clean_text[start_obj : end_obj + 1])
                start_arr = clean_text.find("[")
                end_arr = clean_text.rfind("]")
                if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
                    return json.loads(clean_text[start_arr : end_arr + 1])
            except Exception:
                pass
            logger.warning(f"[LocalLLM] JSON 解析失败: {text[:200]}...")
            return None


# 单例模式导出
local_model_service = LocalModelService()
