"""
图像审核服务（支持云端和本地模型）

职责：
1. 调用云端或本地模型分析图像内容
2. 检测违规内容（暴力、血腥、色情等）
3. 返回审核结果和评分
"""

import os
import httpx
import base64
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class ImageReviewService:
    """图像审核服务（支持云端和本地模型）"""
    
    def __init__(self):
        self.local_base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        # 本地视觉（moondream）暂不用于抽帧审核：按需求全部走云端视觉模型
        # 若后续要启用本地视觉，可打开 LOCAL_VISION_ENABLED 并设置 LOCAL_VISION_MODEL
        self.local_model = getattr(settings, "LOCAL_VISION_MODEL", "moondream:latest")
        self.local_timeout = 10.0
        self.mode = getattr(settings, "VISION_MODE", "hybrid").lower()
        has_cloud_key = bool(settings.LLM_VISION_API_KEY or settings.LLM_API_KEY)
        self.use_cloud = self.mode in ("cloud_only", "hybrid") and has_cloud_key
        # 本地视觉强制由开关控制，避免误用本地模型跑抽帧审核
        self.use_local = bool(getattr(settings, "LOCAL_VISION_ENABLED", False)) and self.mode in ("local_only", "hybrid")
    
    async def review_image(
        self,
        image_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        审核单张图像
        
        参数:
            image_path: 图像文件路径（绝对路径或相对于storage的路径）
        
        返回:
            Dict: 审核结果
                - is_violation: bool - 是否违规
                - is_suspicious: bool - 是否疑似违规
                - violation_type: str - 违规类型（violence/blood/porn等）
                - score: int - 审核评分（0-100，越低越危险）
                - description: str - 审核描述
        """
        # 读取图像文件并转换为 base64
        try:
            image_data = self._read_image_as_base64(image_path)
            if not image_data:
                return None
        except Exception as e:
            logger.error(f"读取图像文件失败: {e}")
            return None
        
        # 优先使用云端模型，失败时回退到本地模型（如果启用）
        if self.use_cloud:
            result = await self._review_with_cloud_model(image_data)
            if result is not None:
                return result
            logger.warning("云端模型图像审核失败，准备回退到本地模型（如已启用）")
        
        if not self.use_local:
            # 本地视觉（moondream）暂不启用：抽帧审核由云端模型负责
            return None

        # 使用本地模型（VISION_MODE 允许时作为兜底）
        return await self._review_with_local_model(image_data)
    
    async def _review_with_cloud_model(
        self,
        image_data: str
    ) -> Optional[Dict[str, Any]]:
        """使用云端模型审核图像"""
        try:
            api_key = settings.LLM_VISION_API_KEY or settings.LLM_API_KEY
            base_url = (settings.LLM_VISION_BASE_URL or settings.LLM_BASE_URL).rstrip("/")
            model = settings.LLM_VISION_MODEL or settings.LLM_MODEL
            timeout = 30.0
            
            if not base_url or not model or not api_key:
                logger.warning("[CloudVision] 配置缺失（base_url/model/api_key），跳过云端审核")
                return None
            
            logger.info(f"[CloudVision] 开始云端图像审核 - 模型: {model}, API: {base_url}")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            
            prompt = """请分析这张图片的内容，判断是否包含以下违规内容：
1. 暴力内容（打架、武器、伤害等）
2. 血腥内容（血迹、伤口、恐怖场景等）
3. 色情内容（裸露、性暗示等）
4. 其他不当内容

请以JSON格式返回分析结果：
{
    "is_violation": true/false,
    "is_suspicious": true/false,
    "violation_type": "violence/blood/porn/other/none",
    "score": 0-100,
    "description": "详细描述"
}

评分标准：
- 0-30: 明显违规，必须拒绝
- 31-60: 疑似违规，需要人工审核
- 61-100: 正常内容，可以发布

请务必只返回 JSON 格式结果，不要包含 Markdown 标记或其他解释文本。"""
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
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
                    logger.error(f"[CloudVision] API错误: {response.status_code} - {response.text}")
                    return None
                
                response_data = response.json()
                response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not response_text:
                    logger.warning(f"[CloudVision] 模型返回空响应: {response_data}")
                    return None
                
                logger.info(f"[CloudVision] 模型响应: {response_text[:200]}...")
                return self._parse_result(response_text)
                
        except httpx.TimeoutException:
            logger.error(f"[CloudVision] 请求超时 ({timeout}s)")
            return None
        except httpx.RequestError as e:
            logger.error(f"[CloudVision] 网络请求错误: {e}")
            return None
        except Exception as e:
            logger.error(f"[CloudVision] 云端图像审核失败: {e}", exc_info=True)
            return None
    
    async def _review_with_local_model(
        self,
        image_data: str
    ) -> Optional[Dict[str, Any]]:
        """使用本地模型审核图像"""
        # 检查本地模型是否启用
        local_enabled = self.use_local or self.mode == "local_only"
        if not local_enabled:
            logger.warning("[LocalModel] 本地模型未启用，跳过图像审核")
            return None
        
        prompt = """请分析这张图片的内容，判断是否包含以下违规内容：
1. 暴力内容（打架、武器、伤害等）
2. 血腥内容（血迹、伤口、恐怖场景等）
3. 色情内容（裸露、性暗示等）
4. 其他不当内容

请以JSON格式返回分析结果：
{
    "is_violation": true/false,
    "is_suspicious": true/false,
    "violation_type": "violence/blood/porn/other/none",
    "score": 0-100,
    "description": "详细描述"
}

评分标准：
- 0-30: 明显违规，必须拒绝
- 31-60: 疑似违规，需要人工审核
- 61-100: 正常内容，可以发布"""
        
        try:
            logger.info(f"[LocalVision] 调用本地图像模型: {self.local_model} @ {self.local_base_url}")
            # trust_env=False: avoid routing localhost through system proxy
            async with httpx.AsyncClient(timeout=self.local_timeout, trust_env=False) as client:
                response = await client.post(
                    f"{self.local_base_url}/chat/completions",
                    json={
                        "model": self.local_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_data}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "stream": False
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"本地图像审核API错误: {response.status_code} - {response.text}")
                    return None
                
                response_data = response.json()
                response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not response_text:
                    logger.warning("本地模型返回空响应")
                    return None
                
                return self._parse_result(response_text)
                
        except httpx.TimeoutException:
            logger.warning(f"本地图像审核请求超时 ({self.local_timeout}s)")
            return None
        except Exception as e:
            logger.error(f"本地图像审核失败: {e}")
            return None
    
    def _read_image_as_base64(self, image_path: str) -> Optional[str]:
        """读取图像文件并转换为 base64"""
        # 规范化路径
        image_path = os.path.normpath(image_path)
        
        if not os.path.exists(image_path):
            logger.error(f"图像文件不存在: {image_path}")
            return None
        
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                return image_base64
        except Exception as e:
            logger.error(f"读取图像文件失败: {e}")
            return None
    
    def _parse_result(self, text: str) -> Dict[str, Any]:
        """解析模型返回的结果"""
        import json
        import re
        
        # 默认结果
        default_result = {
            "is_violation": False,
            "is_suspicious": False,
            "violation_type": "none",
            "score": 80,
            "description": "内容正常"
        }
        
        try:
            # 清理响应文本，移除可能的 Markdown 标记
            clean_text = text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # 尝试直接解析 JSON
            try:
                result = json.loads(clean_text)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取 JSON 片段
                json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise json.JSONDecodeError("No JSON found", text, 0)
            
            # 验证必需字段
            required_fields = ["is_violation", "is_suspicious", "violation_type", "score", "description"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"图像审核响应缺少字段: {field}")
                    return self._fallback_parse(text)
            
            # 确保数据类型正确
            return {
                "is_violation": bool(result.get("is_violation", False)),
                "is_suspicious": bool(result.get("is_suspicious", False)),
                "violation_type": str(result.get("violation_type", "none")),
                "score": int(result.get("score", 80)),
                "description": str(result.get("description", "内容正常"))
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"解析图像审核结果失败: {e}, 原始文本: {text[:100]}")
            return self._fallback_parse(text)
    
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
image_review_service = ImageReviewService()
