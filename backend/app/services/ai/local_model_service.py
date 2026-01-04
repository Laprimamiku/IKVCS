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
        # 允许通过配置动态调整，无需硬编码
        self.base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.model = settings.LOCAL_LLM_MODEL
        self.timeout = settings.LOCAL_LLM_TIMEOUT

    async def predict(self, content: str, content_type: str) -> Optional[AIContentAnalysisResult]:
        """
        调用本地模型进行预测
        
        注意：GPU 管理已改为手动模式
        - 如需消除电感啸叫，请在调用前手动锁定 GPU 频率
        - 调用后手动恢复 GPU 设置
        - 详见：backend/docs/GPU_MANAGEMENT.md
        
        Returns:
            Dict: 预测结果（包含 score, category, label, confidence 等）
            None: 如果调用失败、超时或解析错误，返回 None (触发降级)
        """
        if not settings.LOCAL_LLM_ENABLED:
            return None

        # 1. 准备提示词
        system_prompt = self._get_system_prompt(content_type)
        
        # 针对 0.5B 小模型的额外提示，强调 JSON 格式
        json_instruction = "\n请务必只返回 JSON 格式结果，不要包含 Markdown 标记或其他解释文本。"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt + json_instruction},
                            {"role": "user", "content": f"输入内容: {content}"}
                        ],
                        "temperature": 0.1,  # 低温度，追求确定性
                        "max_tokens": 256,   # 限制输出长度
                        "stream": False
                    }
                )

                if response.status_code != 200:
                    logger.warning(f"[LocalLLM] 调用失败: {response.status_code} - {response.text}")
                    return None

                result_text = response.json()["choices"][0]["message"]["content"]
                
                # 2. 解析结果
                parsed_result = self._parse_json_safely(result_text)
                if not parsed_result:
                    return None

                # 3. 添加元数据（移除置信度计算，不再需要）
                parsed_result["source"] = "local_model"
                parsed_result["model_name"] = self.model

                return parsed_result

        except httpx.TimeoutException:
            logger.warning(f"[LocalLLM] 请求超时 ({self.timeout}s)")
            return None
        except Exception as e:
            logger.error(f"[LocalLLM] 发生异常: {str(e)}")
            return None

    def _get_system_prompt(self, content_type: str) -> str:
        return COMMENT_SYSTEM_PROMPT if content_type == "comment" else DANMAKU_SYSTEM_PROMPT

    def _parse_json_safely(self, text: str) -> Optional[AIContentAnalysisResult]:
        """鲁棒的 JSON 解析，应对小模型可能输出 Markdown 代码块的情况"""
        try:
            # 清理 Markdown 标记 ```json ... ```
            clean_text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
            # 尝试直接解析
            return json.loads(clean_text)
        except json.JSONDecodeError:
            logger.warning(f"[LocalLLM] JSON 解析失败: {text[:50]}...")
            return None


# 单例模式导出
local_model_service = LocalModelService()