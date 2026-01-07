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
        self.mode = getattr(settings, "LLM_MODE", "hybrid").lower()
        self.use_cloud = self.mode in ("cloud_only", "hybrid") and bool(settings.LLM_API_KEY)
        # 字幕审核由云端模型负责；本地模型不用于字幕审核（可后续扩展）
        self.use_local = False
    
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

        if self.mode == "off":
            return {
                "is_violation": False,
                "is_suspicious": False,
                "violation_type": "none",
                "score": 100,
                "description": "LLM_MODE=off，跳过字幕审核"
            }
        
        # 字幕审核：统一走云端（当前不使用本地模型进行字幕审核）
        if self.use_cloud:
            logger.info(f"[SubtitleReview] 调用云端模型: {settings.LLM_MODEL} @ {settings.LLM_BASE_URL}")
            cloud = await self._review_with_cloud_model(subtitle_text)
            if cloud is not None:
                return cloud
            logger.warning("[SubtitleReview] 云端模型审核失败")

        logger.warning("[SubtitleReview] 云端模型不可用，返回默认通过（可改为疑似以触发人工复核）")
        return {
            "is_violation": False,
            "is_suspicious": False,
            "violation_type": "none",
            "score": 100,
            "description": "云端模型不可用，跳过审核"
        }
    
    async def _review_with_cloud_model(
        self,
        subtitle_text: str
    ) -> Optional[Dict[str, Any]]:
        """使用云端模型审核字幕"""
        try:
            # 限制输入文本长度，避免超过模型限制
            max_input_length = getattr(settings, "CLOUD_MAX_INPUT_CHARS_PER_VIDEO", 8000) or 8000
            if len(subtitle_text) > max_input_length:
                logger.warning(f"字幕文本过长 ({len(subtitle_text)} 字符)，截取前 {max_input_length} 字符")
                subtitle_text = subtitle_text[:max_input_length] + "...[文本已截断]"
            
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
                "max_tokens": 512,  # 增加token限制，确保完整的JSON响应
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
        if not self.local_base_url or not self.local_model:
            logger.warning("本地字幕审核配置缺失（base_url/model），跳过字幕审核")
            return None
        
        try:
            # trust_env=False: avoid routing localhost through system proxy
            async with httpx.AsyncClient(timeout=self.local_timeout, trust_env=False) as client:
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
            
            # 尝试直接解析JSON
            try:
                result = json.loads(clean_text)
            except json.JSONDecodeError as e:
                # 如果JSON被截断，尝试修复
                logger.warning(f"JSON解析失败，尝试修复截断的JSON: {e}")
                result = self._try_fix_truncated_json(clean_text)
                if result is None:
                    raise e
            
            # 验证必需字段
            required_fields = ["is_violation", "is_suspicious", "violation_type", "score", "description"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"审核响应缺少字段: {field}")
                    return self._create_default_response(80, "内容正常", "字段不完整，使用默认结果")
            
            # 确保数据类型正确
            result["is_violation"] = bool(result["is_violation"])
            result["is_suspicious"] = bool(result["is_suspicious"])
            result["score"] = int(result["score"])
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"解析字幕审核响应失败: {e}, 响应内容: {response_text[:200]}...")
            # 使用智能备用解析方法
            return self._intelligent_fallback_parse(response_text)
    
    def _try_fix_truncated_json(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试修复被截断的JSON"""
        try:
            # 如果JSON被截断，尝试找到最后一个完整的字段
            # 查找最后一个逗号或引号的位置
            last_comma = text.rfind(',')
            last_quote = text.rfind('"')
            
            if last_comma > 0 and last_quote > last_comma:
                # 尝试在最后一个逗号处截断并添加结束符
                truncated = text[:last_comma] + '}'
                return json.loads(truncated)
            elif last_quote > 0:
                # 尝试在最后一个引号后添加结束符
                truncated = text[:last_quote + 1] + '}'
                return json.loads(truncated)
            
            return None
        except:
            return None
    
    def _create_default_response(self, score: int, violation_type: str, description: str) -> Dict[str, Any]:
        """创建默认响应"""
        return {
            "is_violation": score < 30,
            "is_suspicious": 30 <= score < 60,
            "violation_type": violation_type if score < 60 else "none",
            "score": score,
            "description": description
        }
    
    def _intelligent_fallback_parse(self, text: str) -> Dict[str, Any]:
        """智能备用解析方法（基于上下文分析）"""
        text_lower = text.lower()
        
        # 首先检查是否是学术/教育内容
        educational_indicators = [
            "学术", "教育", "科普", "分析", "研究", "统计", "数据", "理论",
            "academic", "educational", "analysis", "research", "study", "statistics"
        ]
        
        is_educational = any(indicator in text_lower for indicator in educational_indicators)
        
        # 检测真正的违规关键词（需要上下文判断）
        violation_keywords = ["色情", "裸体", "性行为", "porn", "nude", "sex act"]
        violence_keywords = ["杀人", "伤害他人", "暴力行为", "murder", "harm others", "violent act"]
        
        # 如果是教育内容，即使包含敏感词汇也不应该被标记为违规
        if is_educational:
            # 对于教育内容，给予较高评分
            return {
                "is_violation": False,
                "is_suspicious": False,
                "violation_type": "none",
                "score": 85,
                "description": "教育/学术内容，虽然涉及敏感话题但属于正常讨论范围"
            }
        
        # 检测明显违规内容（非教育语境下）
        if any(keyword in text_lower for keyword in violation_keywords):
            return {
                "is_violation": True,
                "is_suspicious": False,
                "violation_type": "porn",
                "score": 20,
                "description": "检测到色情相关内容"
            }
        
        if any(keyword in text_lower for keyword in violence_keywords):
            return {
                "is_violation": True,
                "is_suspicious": False,
                "violation_type": "violence",
                "score": 25,
                "description": "检测到暴力相关内容"
            }
        
        # 检测疑似违规（需要人工审核）
        suspicious_keywords = ["政治敏感", "争议话题", "sensitive political", "controversial"]
        if any(keyword in text_lower for keyword in suspicious_keywords):
            return {
                "is_violation": False,
                "is_suspicious": True,
                "violation_type": "political",
                "score": 50,
                "description": "内容涉及敏感话题，建议人工审核"
            }
        
        # 默认为正常内容
        return {
            "is_violation": False,
            "is_suspicious": False,
            "violation_type": "none",
            "score": 75,
            "description": "解析失败，但未检测到明显违规内容"
        }


# 全局实例
subtitle_review_service = SubtitleReviewService()
