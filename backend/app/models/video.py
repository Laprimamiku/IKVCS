"""
视频和分类数据模型

需求：
- 4.1-4.5（视频转码处理）
- 5.1-5.5（视频列表与检索）
- 6.1-6.3（视频分类管理）
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Category(Base):
    """
    分类模型
    
    对应数据库表：categories
    
    字段说明：
    - id: 主键
    - name: 分类名称（唯一）
    - description: 分类描述
    - created_at: 创建时间
    """
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name = Column(String(50), unique=True, nullable=False, comment="分类名称")
    description = Column(String(255), nullable=True, comment="分类描述")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系映射
    # videos = relationship("Video", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Video(Base):
    """
    视频模型
    
    对应数据库表：videos
    
    字段说明：
    - id: 主键
    - uploader_id: 上传者ID（外键关联 users 表）
    - category_id: 分类ID（外键关联 categories 表）
    - title: 视频标题
    - description: 视频描述
    - cover_url: 封面图 URL
    - video_url: 视频 URL（m3u8 格式）
    - subtitle_url: 字幕文件 URL
    - duration: 视频时长（秒）
    - status: 视频状态（0=转码中, 1=审核中, 2=已发布, 3=拒绝, 4=软删除）
    - view_count: 播放量
    - like_count: 点赞数
    - collect_count: 收藏数
    - created_at: 创建时间
    """
    __tablename__ = "videos"
    
    # 基本字段
    id = Column(Integer, primary_key=True, autoincrement=True, comment="视频ID")
    uploader_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="上传者ID")
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False, comment="分类ID")
    
    # 视频信息
    title = Column(String(100), nullable=False, comment="视频标题")
    description = Column(Text, nullable=True, comment="视频描述")
    cover_url = Column(String(255), nullable=True, comment="封面图URL")
    video_url = Column(String(255), nullable=True, comment="视频URL（m3u8）")
    subtitle_url = Column(String(255), nullable=True, comment="字幕文件URL")
    duration = Column(Integer, default=0, comment="视频时长（秒）")
    
    # 状态和统计
    status = Column(Integer, default=0, comment="状态：0=转码中, 1=审核中, 2=已发布, 3=拒绝, 4=软删除")
    view_count = Column(Integer, default=0, comment="播放量")
    like_count = Column(Integer, default=0, comment="点赞数")
    collect_count = Column(Integer, default=0, comment="收藏数")
    
    # 时间字段
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 索引（提升查询性能）
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_category', 'category_id'),
        Index('idx_created', 'created_at'),
    )
    
    # 关系映射
    # uploader = relationship("User", back_populates="videos")
    # category = relationship("Category", back_populates="videos")
    # danmakus = relationship("Danmaku", back_populates="video")
    # comments = relationship("Comment", back_populates="video")
    
    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', status={self.status})>"
