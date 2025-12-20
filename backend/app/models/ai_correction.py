# backend/app/models/ai_correction.py
"""
AI修正记录数据模型
用于反馈式自我纠错功能
"""
from sqlalchemy import Column, Integer, Text, JSON, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class AICorrection(Base):
    """AI修正记录模型"""
    __tablename__ = "ai_corrections"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="修正记录ID")
    content = Column(Text, nullable=False, comment="原始内容")
    content_type = Column(String(20), nullable=False, comment="内容类型：comment/danmaku")
    original_result = Column(JSON, comment="AI原始分析结果")
    corrected_result = Column(JSON, comment="管理员修正后的结果")
    correction_reason = Column(Text, comment="修正原因")
    corrected_by = Column(Integer, ForeignKey('users.id'), nullable=False, comment="修正人ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系映射
    corrector = relationship("User", foreign_keys=[corrected_by])
    
    def __repr__(self):
        return f"<AICorrection(id={self.id}, content_type={self.content_type}, corrected_by={self.corrected_by})>"


class AIPromptVersion(Base):
    """AI Prompt版本历史模型"""
    __tablename__ = "ai_prompt_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="版本ID")
    prompt_type = Column(String(50), nullable=False, comment="Prompt类型：COMMENT/DANMAKU")
    prompt_content = Column(Text, nullable=False, comment="Prompt内容")
    update_reason = Column(Text, comment="更新原因")
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True, comment="更新人ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系映射
    updater = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<AIPromptVersion(id={self.id}, prompt_type={self.prompt_type}, updated_by={self.updated_by})>"
