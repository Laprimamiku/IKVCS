from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class AiTrainingSample(Base):
    """
    AI 训练样本表
    用于收集本地小模型与云端大模型的分析结果，用于后续微调或评估
    """
    __tablename__ = "ai_training_samples"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False, comment="分析的原始内容")
    ai_score = Column(Integer, comment="模型给出的评分")
    ai_category = Column(String(50), comment="模型分类")
    ai_label = Column(String(50), comment="模型标签")
    
    # 区分来源：'glm-4-flash' (云端) 或 'qwen2.5:0.5b-instruct' (本地)
    source_model = Column(String(50), index=True, comment="来源模型")
    
    # 本地模型特有字段
    local_confidence = Column(Float, nullable=True, comment="本地模型置信度")
    
    # 标记是否被人工修正（未来功能）
    is_corrected = Column(Boolean, default=False, comment="是否已被人工修正")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)