"""
评论数据模型
需求：9.1-9.5, 10.1-10.4
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Comment(Base):
    """
    评论模型
    
    对应数据库表：comments
    """
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="评论ID")
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, comment="视频ID")
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="用户ID")
    parent_id = Column(Integer, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True, comment="父评论ID")
    reply_to_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment="回复目标用户ID（用于@功能）")
    content = Column(Text, nullable=False, comment="评论内容")
    ai_score = Column(Integer, nullable=True, comment="AI评分")
    ai_label = Column(String(50), nullable=True, comment="AI标签")
    like_count = Column(Integer, default=0, comment="点赞数")
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系映射
    user = relationship("User", foreign_keys=[user_id])
    reply_to_user = relationship("User", foreign_keys=[reply_to_user_id])
    video = relationship("Video", foreign_keys=[video_id])
    parent = relationship("Comment", remote_side=[id], backref="replies")
    
    # 索引（提升查询性能）
    __table_args__ = (
        Index('idx_video_id', 'video_id'),  # 查询视频的评论
        Index('idx_video_parent', 'video_id', 'parent_id'),  # 查询视频的根评论
        Index('idx_user_id', 'user_id'),  # 查询用户的评论
        Index('idx_created_at', 'created_at'),  # 按时间排序
        Index('idx_like_count', 'like_count'),  # 按点赞数排序
    )
    
    def __repr__(self):
        return f"<Comment(id={self.id}, video_id={self.video_id}, user_id={self.user_id})>"
