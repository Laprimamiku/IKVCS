"""
模型注册表 - 统一管理所有AI模型配置
解决硬编码模型名问题，支持运行时切换
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    api_key: str
    base_url: str
    timeout: float = 60.0
    max_concurrent: int = 5
    enabled: bool = True


class ModelRegistry:
    """模型注册表"""
    
    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """从配置初始化模型"""
        
        # 获取LLM模式
        llm_mode = settings.LLM_MODE.lower()
        vision_mode = getattr(settings, 'VISION_MODE', 'hybrid').lower()
        
        # 云端文本模型（仅在需要云端且有API密钥时初始化）
        if llm_mode in ("cloud_only", "hybrid") and settings.LLM_API_KEY:
            self._models["cloud_text"] = ModelConfig(
                name=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                timeout=60.0,
                max_concurrent=getattr(settings, 'CLOUD_HOURLY_BUDGET_CALLS', 100) // 10,  # 动态并发控制
                enabled=True
            )
        
        # 云端视觉模型
        vision_api_key = getattr(settings, 'LLM_VISION_API_KEY', settings.LLM_API_KEY) or settings.LLM_API_KEY
        vision_base_url = getattr(settings, 'LLM_VISION_BASE_URL', settings.LLM_BASE_URL) or settings.LLM_BASE_URL
        vision_model = getattr(settings, 'LLM_VISION_MODEL', settings.LLM_MODEL) or settings.LLM_MODEL
        
        if vision_mode in ("cloud_only", "hybrid") and vision_api_key:
            self._models["cloud_vision"] = ModelConfig(
                name=vision_model,
                api_key=vision_api_key,
                base_url=vision_base_url,
                timeout=60.0,
                max_concurrent=settings.CLOUD_FRAME_REVIEW_MAX_CONCURRENT,
                enabled=True
            )
        
        # 本地文本模型（根据LLM_MODE决定，不再依赖LOCAL_LLM_ENABLED）
        if llm_mode in ("local_only", "hybrid"):
            # 根据硬件配置调整并发数
            max_concurrent = self._get_optimal_local_concurrent()
            
            self._models["local_text"] = ModelConfig(
                name=settings.LOCAL_LLM_MODEL,
                api_key="",  # 本地模型不需要API密钥
                base_url=settings.LOCAL_LLM_BASE_URL,
                timeout=settings.LOCAL_LLM_TIMEOUT,
                max_concurrent=max_concurrent,
                enabled=True
            )
    
    def _get_optimal_local_concurrent(self) -> int:
        """根据硬件配置获取最优本地模型并发数"""
        hardware_profile = getattr(settings, 'HARDWARE_PROFILE', 'default')
        
        if hardware_profile == 'rtx3050_laptop':
            # RTX 3050 Laptop 4GB 显存，保守并发
            return 1
        elif hardware_profile == 'rtx4060_desktop':
            # RTX 4060 8GB 显存，可以适当提高
            return 2
        else:
            # 默认保守配置
            return getattr(settings, 'LOCAL_LLM_MAX_CONCURRENT', 1)
    
    def get_model(self, model_type: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self._models.get(model_type)
    
    def is_available(self, model_type: str) -> bool:
        """检查模型是否可用"""
        model = self._models.get(model_type)
        return model is not None and model.enabled
    
    def get_available_models(self) -> Dict[str, ModelConfig]:
        """获取所有可用模型"""
        return {k: v for k, v in self._models.items() if v.enabled}
    
    def get_text_model_priority(self) -> list[str]:
        """获取文本模型优先级顺序"""
        llm_mode = settings.LLM_MODE.lower()
        
        if llm_mode == "off":
            return []
        elif llm_mode == "cloud_only":
            return ["cloud_text"] if self.is_available("cloud_text") else []
        elif llm_mode == "local_only":
            return ["local_text"] if self.is_available("local_text") else []
        elif llm_mode == "hybrid":
            # 混合模式：本地优先，云端兜底
            available = []
            if self.is_available("local_text"):
                available.append("local_text")
            if self.is_available("cloud_text"):
                available.append("cloud_text")
            return available
        else:
            return []
    
    def get_vision_model_priority(self) -> list[str]:
        """获取视觉模型优先级顺序"""
        vision_mode = getattr(settings, 'VISION_MODE', 'hybrid').lower()
        
        if vision_mode == "off":
            return []
        elif vision_mode == "cloud_only":
            return ["cloud_vision"] if self.is_available("cloud_vision") else []
        elif vision_mode == "local_only":
            return []  # 暂不支持本地视觉模型
        elif vision_mode == "hybrid":
            return ["cloud_vision"] if self.is_available("cloud_vision") else []
        else:
            return []
    
    def should_escalate_to_cloud(self, local_confidence: float) -> bool:
        """判断是否应该从本地模型升级到云端模型"""
        if not settings.LOCAL_LLM_ESCALATE_TO_CLOUD:
            return False
        
        if not self.is_available("cloud_text"):
            return False
        
        # 只在“明显不确定”时升级，避免短文本大量升级造成 token/RTT 暴涨
        threshold = float(getattr(settings, "LOCAL_LLM_ESCALATE_CONFIDENCE", 0.55) or 0.55)
        return local_confidence < threshold
    
    def reload(self):
        """重新加载模型配置"""
        self._models.clear()
        self._initialize_models()


# 全局模型注册表实例
model_registry = ModelRegistry()
