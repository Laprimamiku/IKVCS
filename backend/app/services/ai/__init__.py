"""
AI 服务模块
"""
from app.services.ai.llm_service import LLMService

# 多智能体服务（可选）
try:
    from app.services.ai.multi_agent_service import MultiAgentService, multi_agent_service
    __all__ = ['LLMService', 'MultiAgentService', 'multi_agent_service']
except ImportError:
    __all__ = ['LLMService']

