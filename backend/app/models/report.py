"""
举报数据模型
需求：16.1-16.5
"""
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Report(Base):
    """
    举报模型
    
    对应数据库表：reports
    """
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="举报ID")
    reporter_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="举报人ID")
    target_type = Column(Enum('VIDEO', 'COMMENT', 'DANMAKU', name='report_target_type'), nullable=False, comment="举报目标类型")
    target_id = Column(Integer, nullable=False, comment="举报目标ID")
    reason = Column(String(100), nullable=False, comment="举报原因")
    description = Column(Text, nullable=True, comment="举报描述")
    status = Column(Integer, default=0, comment="处理状态：0=待处理, 1=已处理, 2=已忽略")
    handler_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment="处理人ID")
    admin_note = Column(Text, nullable=True, comment="管理员备注")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    handled_at = Column(DateTime, nullable=True, comment="处理时间")
    
    # 关系映射
    reporter = relationship("User", foreign_keys=[reporter_id])
    handler = relationship("User", foreign_keys=[handler_id])
    
    def __repr__(self):
        return f"<Report(id={self.id}, target_type={self.target_type}, target_id={self.target_id}, status={self.status})>"
