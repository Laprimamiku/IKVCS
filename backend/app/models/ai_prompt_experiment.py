"""
Prompt workflow experiment model.
Stores prompt test and evaluation results.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Index

from app.core.database import Base


class AiPromptExperiment(Base):
    """Prompt workflow experiment."""

    __tablename__ = "ai_prompt_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("ai_prompt_tasks.id", ondelete="SET NULL"), nullable=True)
    prompt_type = Column(String(50), nullable=False, comment="Prompt type")
    candidate_version_id = Column(
        Integer, ForeignKey("ai_prompt_versions.id", ondelete="SET NULL"), nullable=True
    )
    active_version_id = Column(
        Integer, ForeignKey("ai_prompt_versions.id", ondelete="SET NULL"), nullable=True
    )
    model_source = Column(String(50), default="auto", comment="Model source")
    dataset_source = Column(String(50), default="corrections", comment="Dataset source")
    sample_limit = Column(Integer, default=50, comment="Requested sample size")
    sample_count = Column(Integer, default=0, comment="Actual sample size")
    status = Column(String(20), default="completed", comment="Experiment status")

    metrics = Column(JSON, comment="Evaluation metrics")
    sample_details = Column(JSON, comment="Sample-level comparison details")

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, comment="Created at")

    __table_args__ = (
        Index("idx_prompt_experiment_type", "prompt_type"),
        Index("idx_prompt_experiment_task", "task_id"),
        Index("idx_prompt_experiment_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AiPromptExperiment(id={self.id}, prompt_type={self.prompt_type})>"
