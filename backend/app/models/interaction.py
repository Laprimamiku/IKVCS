"""
互动数据模型（点赞、收藏）
需求：11.1-11.5, 12.1-12.4
"""
from sqlalchemy import Column, Integer, Enum, ForeignKey, DateTime, UniqueConstraint, Index
from datetime import datetime

# TODO: 从 database 导入 Base
# from app.core.database import Base

# TODO: 实现 UserLike 模型
# class UserLike(Base):
#     __tablename__ = "user_likes"
#     
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
#     target_type = Column(Enum('VIDEO', 'COMMENT'), nullable=False)
#     target_id = Column(Integer, nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     
#     # 唯一约束
#     __table_args__ = (
#         UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_user_like'),
#         Index('idx_target', 'target_type', 'target_id'),
#     )

# TODO: 实现 UserCollection 模型
# class UserCollection(Base):
#     __tablename__ = "user_collections"
#     
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
#     video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'))
#     created_at = Column(DateTime, default=datetime.utcnow)
#     
#     # 唯一约束
#     __table_args__ = (
#         UniqueConstraint('user_id', 'video_id', name='uq_user_collection'),
#     )
