"""
字幕审核服务（使用 qwen2.5:0.5b-instruct）

职责：
1. 调用 qwen2.5:0.5b-instruct 分析字幕内容
2. 检测违规内容（暴力、血腥、色情、政治敏感等）
3. 返回审核结果和评分
"""

import httpx
import json
import logging
import re
from typing import Optional, Dict, Any

from app.core.config import settings
from app.services.ai.local_model_service import local_model_service

logger = logging.getLogger(__name__)

# 字幕审核专用 Prompt
SUBTITLE_REVIEW_PROMPT = """你是一个专业的内容审核员。请分析以下视频字幕内容，判断是否包含违规内容。

违规内容类型：
1. 暴力内容：描述暴力行为、伤害、武器等
2. 血腥内容：描述血腥场景、恐怖内容等
3. 色情内容：性暗示、裸露描述等
4. 政治敏感：涉及敏感政治话题
5. 其他不当内容：违法、低俗等

请以JSON格式返回分析结果：
{
    "is_violation": true/false,
    "is_suspicious": true/false,
    "violation_type": "violence/blood/porn/political/other/none",
    "score": 0-100,
    "description": "详细描述"
}

评分标准：
- 0-30: 明显违规，必须拒绝
- 31-60: 疑似违规，需要人工审核
- 61-100: 正常内容，可以发布

请务必只返回 JSON 格式结果，不要包含 Markdown 标记或其他解释文本。"""


class SubtitleReviewService:
    """字幕审核服务（使用 qwen2.5:0.5b-instruct）"""
    
    def __init__(self):
        self.base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.model = settings.LOCAL_LLM_MODEL  # qwen2.5:0.5b-instruct
        self.timeout = settings.LOCAL_LLM_TIMEOUT
    
    async def review_subtitle(
        self,
        subtitle_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        审核字幕内容
        
        参数:
            subtitle_text: 字幕文本内容
        
        返回:
            Dict: 审核结果
                - is_violation: bool - 是否违规
                - is_suspicious: bool - 是否疑似违规
                - violation_type: str - 违规类型
                - score: int - 审核评分（0-100）
                - description: str - 审核描述
        """
        if not settings.LOCAL_LLM_ENABLED:
            logger.warning("本地模型未启用，跳过字幕审核")
            return None
        
        if not subtitle_text or len(subtitle_text.strip()) == 0:
            return {
                "is_violation": False,
                "is_suspicious": False,
                "violation_type": "none",
                "score": 100,
                "description": "字幕为空，无需审核"
            }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SUBTITLE_REVIEW_PROMPT},
                            {"role": "user", "content": f"字幕内容：\n{subtitle_text}"}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 256,
                        "stream": False
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"[SubtitleReview] 调用失败: {response.status_code} - {response.text}")
                    return None
                
                result_text = response.json()["choices"][0]["message"]["content"]
                
                # 解析结果
                result = self._parse_result(result_text)
                return result
                
        except httpx.TimeoutException:
            logger.warning(f"[SubtitleReview] 请求超时 ({self.timeout}s)")
            return None
        except Exception as e:
            logger.error(f"[SubtitleReview] 发生异常: {str(e)}")
            return None
    
    def _parse_result(self, text: str) -> Dict[str, Any]:
        """解析模型返回的结果"""
        # 默认结果
        default_result = {
            "is_violation": False,
            "is_suspicious": False,
            "violation_type": "none",
            "score": 80,
            "description": "内容正常"
        }
        
        try:
            # 清理 Markdown 标记
            clean_text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
            result = json.loads(clean_text)
            
            # 验证和规范化结果
            return {
                "is_violation": bool(result.get("is_violation", False)),
                "is_suspicious": bool(result.get("is_suspicious", False)),
                "violation_type": str(result.get("violation_type", "none")),
                "score": int(result.get("score", 80)),
                "description": str(result.get("description", "内容正常"))
            }
        except json.JSONDecodeError:
            logger.warning(f"[SubtitleReview] JSON 解析失败: {text[:100]}")
            # 尝试从文本中提取关键词判断
            return self._fallback_parse(text)
        except Exception as e:
            logger.error(f"[SubtitleReview] 解析结果异常: {e}")
            return default_result
    
    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """备用解析方法（从文本中提取关键词）"""
        text_lower = text.lower()
        
        # 检测明显违规关键词
        violation_keywords = ["暴力", "血腥", "色情", "violence", "blood", "porn", "sex"]
        if any(keyword in text_lower for keyword in violation_keywords):
            return {
                "is_violation": True,
                "is_suspicious": False,
                "violation_type": "other",
                "score": 30,
                "description": "检测到疑似违规内容"
            }
        
        # 检测疑似违规
        suspicious_keywords = ["敏感", "不当", "sensitive", "inappropriate"]
        if any(keyword in text_lower for keyword in suspicious_keywords):
            return {
                "is_violation": False,
                "is_suspicious": True,
                "violation_type": "other",
                "score": 50,
                "description": "内容可能存在问题，需要人工审核"
            }
        
        return {
            "is_violation": False,
            "is_suspicious": False,
            "violation_type": "none",
            "score": 80,
            "description": "内容正常"
        }


# 全局实例
subtitle_review_service = SubtitleReviewService()

