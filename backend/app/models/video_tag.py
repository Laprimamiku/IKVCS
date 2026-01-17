"""
视频标签数据模型

功能：
- 视频标签管理
- 支持多对多关系（一个视频可以有多个标签，一个标签可以被多个视频使用）
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

# 视频和标签的关联表（多对多关系）
video_tag_association = Table(
    'video_tag_associations',
    Base.metadata,
    Column('video_id', Integer, ForeignKey('videos.id', ondelete='CASCADE'), primary_key=True, comment="视频ID"),
    Column('tag_id', Integer, ForeignKey('video_tags.id', ondelete='CASCADE'), primary_key=True, comment="标签ID"),
    Column('created_at', DateTime, default=datetime.utcnow, comment="关联创建时间"),
    Index('idx_video_tag', 'video_id', 'tag_id'),
    Index('idx_tag_video', 'tag_id', 'video_id'),
)


class VideoTag(Base):
    """
    视频标签模型
    
    对应数据库表：video_tags
    
    字段说明：
    - id: 主键
    - name: 标签名称（唯一）
    - usage_count: 使用次数（统计有多少视频使用了该标签）
    - created_at: 创建时间
    """
    __tablename__ = "video_tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="标签ID")
    name = Column(String(50), unique=True, nullable=False, index=True, comment="标签名称")
    usage_count = Column(Integer, default=0, comment="使用次数")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系映射（多对多）
    videos = relationship(
        "Video",
        secondary=video_tag_association,
        back_populates="tags",
        lazy="dynamic"
    )
    
    __table_args__ = (
        Index('idx_tag_name', 'name'),
        Index('idx_tag_usage', 'usage_count'),
    )
    
    def __repr__(self):
        return f"<VideoTag(id={self.id}, name='{self.name}', usage_count={self.usage_count})>"

