"""
Prompt workflow task model.
Defines the task scope and evaluation criteria for prompt engineering.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, DateTime, ForeignKey, Index

from app.core.database import Base


class AiPromptTask(Base):
    """Prompt workflow task."""

    __tablename__ = "ai_prompt_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="Task name")
    prompt_type = Column(String(50), nullable=False, comment="Prompt type")
    goal = Column(Text, comment="Task goal")
    metrics = Column(JSON, comment="Evaluation metrics")
    dataset_source = Column(String(50), default="corrections", comment="Dataset source")
    sample_min = Column(Integer, default=20, comment="Minimum sample size")
    is_active = Column(Boolean, default=True, comment="Whether task is active")

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created at")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Updated at")

    __table_args__ = (
        Index("idx_prompt_task_type", "prompt_type"),
        Index("idx_prompt_task_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AiPromptTask(id={self.id}, prompt_type={self.prompt_type})>"
