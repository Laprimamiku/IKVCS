"""
上传会话数据模型

需求：3.1-3.6（视频分片上传）
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from datetime import datetime

from app.core.database import Base


class UploadSession(Base):
    """
    上传会话模型
    
    对应数据库表：upload_sessions
    
    字段说明：
    - file_hash: 文件哈希（SHA-256），作为主键
    - user_id: 上传者ID
    - file_name: 原始文件名
    - file_size: 文件大小（字节）
    - total_chunks: 总分片数
    - uploaded_chunks: 已上传分片列表（逗号分隔，如 "1,2,3,5"）
    - is_completed: 是否完成上传
    - video_id: 关联的视频ID（上传完成后创建）
    - created_at: 创建时间
    - updated_at: 更新时间
    
    为什么使用 file_hash 作为主键：
        - 文件哈希唯一标识一个文件
        - 支持秒传：相同文件哈希表示相同内容
        - 防止重复上传
    """
    __tablename__ = "upload_sessions"
    
    file_hash = Column(String(64), primary_key=True, comment="文件哈希（SHA-256）")
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="上传者ID")
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    total_chunks = Column(Integer, nullable=False, comment="总分片数")
    uploaded_chunks = Column(Text, nullable=True, comment="已上传分片列表")
    is_completed = Column(Boolean, default=False, comment="是否完成上传")
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='SET NULL'), nullable=True, comment="关联视频ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    def __repr__(self):
        return f"<UploadSession(file_hash='{self.file_hash}', file_name='{self.file_name}', is_completed={self.is_completed})>"
