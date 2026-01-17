"""
用户关注关系模型
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class UserFollow(Base):
    """
    用户关注关系表
    
    支持单向关注：
    - user_id 关注 target_user_id
    - 被关注者可以移除粉丝（取消对方的关注）
    """
    __tablename__ = "user_follows"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="关注关系ID")
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="关注者ID")
    target_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="被关注者ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="关注时间")
    
    # 关系映射
    user = relationship("User", foreign_keys=[user_id], backref="following_relations")
    target_user = relationship("User", foreign_keys=[target_user_id], backref="follower_relations")
    
    # 联合唯一索引，防止重复关注
    __table_args__ = (
        UniqueConstraint('user_id', 'target_user_id', name='uq_user_follow'),
        Index('idx_user_id', 'user_id'),
        Index('idx_target_user_id', 'target_user_id'),
    )
    
    def __repr__(self):
        return f"<UserFollow(user_id={self.user_id}, target_user_id={self.target_user_id})>"

