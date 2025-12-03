"""
LLM 智能分析服务
需求：8.1-8.5, 10.1-10.4, 20.1-20.4

⚠️ 重要提示：
此文件需要根据你使用的 LLM API 提供商进行配置
支持的 API 格式：OpenAI、Kimi、DeepSeek、Claude 等兼容 OpenAI 格式的 API
"""
import httpx
import json
from typing import Dict

# TODO: 从 config 导入配置
# from app.core.config import settings

class LLMService:
    """LLM 服务封装"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """
        初始化 LLM 服务
        
        参数：
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        
        ⚠️ 配置示例：
        - OpenAI: base_url="https://api.openai.com/v1", model="gpt-3.5-turbo"
        - Kimi: base_url="https://api.moonshot.cn/v1", model="moonshot-v1-8k"
        - DeepSeek: base_url="https://api.deepseek.com/v1", model="deepseek-chat"
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    async def analyze_content(
        self,
        content: str,
        content_type: str  # "danmaku" or "comment"
    ) -> Dict:
        """
        调用 LLM API 分析内容价值
        
        返回格式：
        {
            "score": 85,  # 0-100 分
            "category": "知识补充",  # 弹幕分类
            "label": "优质讨论",     # 评论标签
            "is_inappropriate": false
        }
        
        ⚠️ 需要实现：
        1. 构建 prompt（根据 content_type）
        2. 调用 LLM API
        3. 解析响应并返回结构化数据
        """
        # TODO: 实现 LLM API 调用
        pass
    
    def _build_prompt(self, content: str, content_type: str) -> str:
        """
        构建 LLM prompt
        
        ⚠️ 需要根据你的需求定制 prompt
        参考设计文档中的 prompt 模板
        """
        # TODO: 实现 prompt 构建
        pass
    
    async def _call_llm_api(self, prompt: str) -> str:
        """
        调用 LLM API
        
        ⚠️ 需要根据你使用的 API 提供商实现
        通常使用 httpx 发送 POST 请求到 /chat/completions 端点
        """
        # TODO: 实现 API 调用
        pass
    
    def _parse_response(self, response: str) -> Dict:
        """
        解析 LLM 响应
        
        ⚠️ 需要处理 JSON 解析和错误情况
        """
        # TODO: 实现响应解析
        pass

# 全局 LLM 服务实例
# llm_service = LLMService(
#     api_key=settings.LLM_API_KEY,
#     base_url=settings.LLM_BASE_URL,
#     model=settings.LLM_MODEL
# )
