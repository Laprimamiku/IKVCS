"""
图像审核服务（使用 moondream）

职责：
1. 调用 moondream 模型分析图像内容
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
    """图像审核服务（使用 moondream）"""
    
    def __init__(self):
        self.base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.model = "moondream"  # moondream 模型名称
        self.timeout = 10.0
    
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
        if not settings.LOCAL_LLM_ENABLED:
            logger.warning("本地模型未启用，跳过图像审核")
            return None
        
        # 读取图像文件并转换为 base64
        try:
            image_data = self._read_image_as_base64(image_path)
            if not image_data:
                return None
        except Exception as e:
            logger.error(f"读取图像文件失败: {e}")
            return None
        
        # 构建审核提示词
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # moondream 使用 OpenAI 兼容的 chat/completions API（支持 vision）
                # 参考 Ollama 官方文档：https://github.com/ollama/ollama/blob/main/docs/api.md
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
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
                    logger.warning(f"[Moondream] 调用失败: {response.status_code} - {response.text}")
                    return None
                
                # OpenAI 兼容格式的响应
                result_data = response.json()
                result_text = result_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # 解析结果
                result = self._parse_result(result_text)
                return result
                
        except httpx.TimeoutException:
            logger.warning(f"[Moondream] 请求超时 ({self.timeout}s)")
            return None
        except Exception as e:
            logger.error(f"[Moondream] 发生异常: {str(e)}")
            return None
    
    def _read_image_as_base64(self, image_path: str) -> Optional[str]:
        """读取图像文件并转换为 base64"""
        # 处理相对路径
        if not os.path.isabs(image_path):
            image_path = os.path.join(settings.STORAGE_ROOT, image_path)
        
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
        """解析 moondream 返回的结果"""
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
            # 尝试提取 JSON
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # 验证字段
                if "is_violation" in result:
                    return {
                        "is_violation": bool(result.get("is_violation", False)),
                        "is_suspicious": bool(result.get("is_suspicious", False)),
                        "violation_type": str(result.get("violation_type", "none")),
                        "score": int(result.get("score", 80)),
                        "description": str(result.get("description", "内容正常"))
                    }
        except Exception as e:
            logger.warning(f"解析 moondream 结果失败: {e}, 原始文本: {text[:100]}")
        
        # 如果解析失败，尝试从文本中提取关键词判断
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ["暴力", "血腥", "色情", "violence", "blood", "porn"]):
            return {
                "is_violation": True,
                "is_suspicious": False,
                "violation_type": "other",
                "score": 30,
                "description": "检测到疑似违规内容"
            }
        
        return default_result


# 全局实例
image_review_service = ImageReviewService()

