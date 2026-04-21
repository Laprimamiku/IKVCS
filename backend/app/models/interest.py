"""
用户兴趣画像数据模型
需求：13.1-13.5
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from datetime import datetime

from app.core.database import Base


class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="用户ID")
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False, comment="分类ID")
    weight = Column(Integer, default=0, nullable=False, comment="兴趣权重")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    __table_args__ = (
        UniqueConstraint('user_id', 'category_id', name='uq_user_category'),
    )
