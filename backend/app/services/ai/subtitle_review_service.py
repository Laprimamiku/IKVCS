"""
字幕审核服务（支持云端和本地模型）

职责：
1. 调用云端或本地模型分析字幕内容
2. 检测违规内容（暴力、血腥、色情、政治敏感等）
3. 返回审核结果和评分
"""

import httpx
import json
import logging
import re
from typing import Optional, Dict, Any

from app.core.config import settings

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
    """字幕审核服务（支持云端和本地模型）"""
    
    def __init__(self):
        self.local_base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.local_model = settings.LOCAL_LLM_MODEL
        self.local_timeout = settings.LOCAL_LLM_TIMEOUT
    
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
        if not subtitle_text or len(subtitle_text.strip()) == 0:
            return {
                "is_violation": False,
                "is_suspicious": False,
                "violation_type": "none",
                "score": 100,
                "description": "字幕为空，无需审核"
            }
        
        # 优先使用云端模型，失败时回退到本地模型
        if settings.USE_CLOUD_LLM:
            result = await self._review_with_cloud_model(subtitle_text)
            if result is not None:
                return result
            logger.warning("云端模型审核失败，回退到本地模型")
        
        # 使用本地模型
        return await self._review_with_local_model(subtitle_text)
    
    async def _review_with_cloud_model(
        self,
        subtitle_text: str
    ) -> Optional[Dict[str, Any]]:
        """使用云端模型审核字幕"""
        try:
            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_BASE_URL.rstrip("/")
            model = settings.LLM_MODEL
            timeout = 30.0
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SUBTITLE_REVIEW_PROMPT},
                    {"role": "user", "content": f"字幕内容：\n{subtitle_text}"}
                ],
                "temperature": 0.1,
                "max_tokens": 256,
            }
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                
                if response.status_code != 200:
                    logger.error(f"云端字幕审核API错误: {response.status_code} - {response.text}")
                    return None
                
                response_data = response.json()
                response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not response_text:
                    logger.warning("云端模型返回空响应")
                    return None
                
                return self._parse_review_response(response_text)
                
        except Exception as e:
            logger.error(f"云端字幕审核失败: {e}")
            return None
    
    async def _review_with_local_model(
        self,
        subtitle_text: str
    ) -> Optional[Dict[str, Any]]:
        """使用本地模型审核字幕"""
        if not settings.LOCAL_LLM_ENABLED:
            logger.warning("本地模型未启用，跳过字幕审核")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=self.local_timeout) as client:
                response = await client.post(
                    f"{self.local_base_url}/chat/completions",
                    json={
                        "model": self.local_model,
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
                    logger.error(f"本地字幕审核API错误: {response.status_code} - {response.text}")
                    return None
                
                response_data = response.json()
                response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not response_text:
                    logger.warning("本地模型返回空响应")
                    return None
                
                return self._parse_review_response(response_text)
                
        except Exception as e:
            logger.error(f"本地字幕审核失败: {e}")
            return None
    
    def _parse_review_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """解析审核响应"""
        try:
            # 清理响应文本，移除可能的 Markdown 标记
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            result = json.loads(clean_text)
            
            # 验证必需字段
            required_fields = ["is_violation", "is_suspicious", "violation_type", "score", "description"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"审核响应缺少字段: {field}")
                    return None
            
            # 确保数据类型正确
            result["is_violation"] = bool(result["is_violation"])
            result["is_suspicious"] = bool(result["is_suspicious"])
            result["score"] = int(result["score"])
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"解析字幕审核响应失败: {e}, 响应内容: {response_text}")
            # 使用备用解析方法
            return self._fallback_parse(response_text)
    
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