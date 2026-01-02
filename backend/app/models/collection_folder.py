"""
收藏文件夹模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class CollectionFolder(Base):
    """
    收藏文件夹表
    用户可以创建文件夹来分类管理收藏的视频
    """
    __tablename__ = "collection_folders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False, comment="文件夹名称")
    description = Column(Text, nullable=True, comment="文件夹描述")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    user = relationship("User", backref="collection_folders")
    collections = relationship("UserCollection", back_populates="folder", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_id', 'user_id'),
    )

