"""
上传会话数据模型
需求：3.1-3.6
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, DateTime
from datetime import datetime

# TODO: 从 database 导入 Base
# from app.core.database import Base

# TODO: 实现 UploadSession 模型
# class UploadSession(Base):
#     __tablename__ = "upload_sessions"
#     
#     file_hash = Column(String(64), primary_key=True)  # SHA-256
#     user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
#     file_name = Column(String(255), nullable=False)
#     total_chunks = Column(Integer, nullable=False)
#     uploaded_chunks = Column(Text, nullable=True)  # "1,2,3,5"
#     is_completed = Column(Boolean, default=False)
#     created_at = Column(DateTime, default=datetime.utcnow)
