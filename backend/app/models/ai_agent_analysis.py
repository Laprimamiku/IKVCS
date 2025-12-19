"""
Agent 分析记录模型

用于记录多智能体陪审团的分析过程，便于：
1. 审计和调试
2. 分析 Agent 表现
3. 优化 Agent Prompt
"""

from sqlalchemy import Column, Integer, String, JSON, DateTime, Index
from datetime import datetime

from app.core.database import Base


class AgentAnalysis(Base):
    """Agent 分析记录"""
    __tablename__ = "ai_agent_analysis"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), nullable=False, comment="内容哈希（MD5）")
    agent_name = Column(
        String(50), 
        nullable=False, 
        comment="Agent 名称（multi_agent / meme_expert / ...）"
    )
    agent_result = Column(
        JSON, 
        nullable=True, 
        comment="Agent 分析结果（JSON 格式）"
    )
    final_result = Column(
        JSON, 
        nullable=True, 
        comment="最终裁决结果（JSON 格式）"
    )
    created_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        comment="创建时间"
    )
    
    # 索引
    __table_args__ = (
        Index('idx_content_hash', 'content_hash'),
        Index('idx_agent_name', 'agent_name'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AgentAnalysis(id={self.id}, agent_name={self.agent_name})>"