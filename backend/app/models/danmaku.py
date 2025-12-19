"""
弹幕数据模型
需求：7.1-7.5, 8.1-8.5
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Index
from datetime import datetime

from app.core.database import Base

class Danmaku(Base):
    __tablename__ = "danmakus"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    content = Column(String(255), nullable=False)
    video_time = Column(Float, nullable=False)  # 视频时间轴位置（秒）
    color = Column(String(20), default='#FFFFFF')
    ai_score = Column(Integer, nullable=True)  # AI 评分 0-100
    ai_category = Column(String(50), nullable=True)  # AI 分类
    is_highlight = Column(Boolean, default=False)  # 是否高亮显示
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 索引：通常会根据视频ID和时间查询
    __table_args__ = (
        Index('idx_video_time', 'video_id', 'video_time'),
    )
