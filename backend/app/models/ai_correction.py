"""
AI 修正记录模型

用于记录管理员对AI误判的修正，支持反馈式自我纠错机制
"""

from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, Enum
from datetime import datetime
from app.core.database import Base


class AiCorrection(Base):
    """AI 修正记录"""
    __tablename__ = "ai_corrections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False, comment="原始内容")
    content_type = Column(
        Enum('comment', 'danmaku', name='content_type_enum'),
        nullable=False,
        comment="内容类型"
    )
    original_result = Column(JSON, comment="AI 原始分析结果")
    corrected_result = Column(JSON, comment="管理员修正后的结果")
    correction_reason = Column(Text, comment="修正原因")
    corrected_by = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        comment="修正人ID"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="创建时间"
    )
    
    def __repr__(self):
        return f"<AiCorrection(id={self.id}, content_type={self.content_type})>"
