"""
用户兴趣画像数据模型
需求：13.1-13.5
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from datetime import datetime

# TODO: 从 database 导入 Base
# from app.core.database import Base

# TODO: 实现 UserInterest 模型
# class UserInterest(Base):
#     __tablename__ = "user_interests"
#     
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
#     category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'))
#     weight = Column(Integer, default=0)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#     
#     # 唯一约束
#     __table_args__ = (
#         UniqueConstraint('user_id', 'category_id', name='uq_user_category'),
#     )
