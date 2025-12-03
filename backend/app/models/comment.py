"""
评论数据模型
需求：9.1-9.5, 10.1-10.4
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from datetime import datetime

# TODO: 从 database 导入 Base
# from app.core.database import Base

# TODO: 实现 Comment 模型
# class Comment(Base):
#     __tablename__ = "comments"
#     
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'))
#     user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
#     parent_id = Column(Integer, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
#     content = Column(Text, nullable=False)
#     ai_score = Column(Integer, nullable=True)
#     ai_label = Column(String(50), nullable=True)
#     like_count = Column(Integer, default=0)
#     is_deleted = Column(Boolean, default=False)
#     created_at = Column(DateTime, default=datetime.utcnow)
