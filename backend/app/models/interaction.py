from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship # <--- [新增]
from datetime import datetime
from app.core.database import Base

class UserLike(Base):
    """
    用户点赞记录表
    支持视频点赞和评论点赞，通过 target_type 区分
    """
    __tablename__ = "user_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_id = Column(Integer, nullable=False, comment="目标ID(视频ID或评论ID)")
    target_type = Column(String(20), nullable=False, comment="目标类型: video/comment")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 联合唯一索引，防止重复点赞
    __table_args__ = (
        UniqueConstraint('user_id', 'target_id', 'target_type', name='uq_user_like_target'),
        Index('idx_target_likes', 'target_type', 'target_id'), # 方便查询某个对象的点赞数
    )

class UserCollection(Base):
    """
    用户收藏记录表
    仅针对视频
    """
    __tablename__ = "user_collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    folder_id = Column(Integer, ForeignKey('collection_folders.id', ondelete='SET NULL'), nullable=True, comment="所属文件夹ID")
    created_at = Column(DateTime, default=datetime.utcnow)

    # [新增] 关联视频模型，以便在收藏列表中获取视频详情
    # lazy='joined' 表示查询收藏时自动加载视频信息
    video = relationship("Video", lazy="joined")
    folder = relationship("CollectionFolder", back_populates="collections", lazy="select")

    # 联合唯一索引
    __table_args__ = (
        UniqueConstraint('user_id', 'video_id', name='uq_user_collection_video'),
        Index('idx_folder_id', 'folder_id'),
    )