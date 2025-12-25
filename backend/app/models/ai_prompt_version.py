"""
Prompt 版本历史模型

用于记录 System Prompt 的版本历史，支持版本回滚
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Index
from datetime import datetime
from app.core.database import Base


class AiPromptVersion(Base):
    """Prompt 版本历史"""
    __tablename__ = "ai_prompt_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_type = Column(
        String(50),
        nullable=False,
        comment="Prompt 类型（COMMENT / DANMAKU / MEME_EXPERT / EMOTION_EXPERT / LEGAL_EXPERT）"
    )
    prompt_content = Column(Text, nullable=False, comment="Prompt 内容")
    update_reason = Column(Text, comment="更新原因")
    updated_by = Column(
        Integer,
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        comment="更新人ID"
    )
    is_active = Column(
        Boolean,
        default=False,
        comment="是否为当前激活版本"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="创建时间"
    )
    
    # 索引
    __table_args__ = (
        Index('idx_prompt_type', 'prompt_type'),
        Index('idx_created_at', 'created_at'),
        Index('idx_is_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<AiPromptVersion(id={self.id}, prompt_type={self.prompt_type}, is_active={self.is_active})>"
