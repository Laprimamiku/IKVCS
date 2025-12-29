"""
观看历史记录数据模型
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class WatchHistory(Base):
    """
    观看历史记录模型
    
    对应数据库表：watch_history
    
    字段说明：
    - id: 主键
    - user_id: 用户ID（外键关联 users 表）
    - video_id: 视频ID（外键关联 videos 表）
    - watched_at: 观看时间（不保留具体播放时间，只记录观看时间）
    """
    __tablename__ = "watch_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="用户ID")
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, comment="视频ID")
    watched_at = Column(DateTime, default=datetime.utcnow, comment="观看时间")
    
    # 关系映射
    user = relationship("User", foreign_keys=[user_id])
    video = relationship("Video", foreign_keys=[video_id])
    
    # 索引和约束
    __table_args__ = (
        UniqueConstraint('user_id', 'video_id', name='uq_user_video_watch'),  # 同一用户同一视频只保留一条记录
        Index('idx_user_watched', 'user_id', 'watched_at'),  # 方便查询用户的观看历史
    )
    
    def __repr__(self):
        return f"<WatchHistory(id={self.id}, user_id={self.user_id}, video_id={self.video_id})>"

