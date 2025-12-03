"""
举报数据模型
需求：16.1-16.5
"""
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime
from datetime import datetime

# TODO: 从 database 导入 Base
# from app.core.database import Base

# TODO: 实现 Report 模型
# class Report(Base):
#     __tablename__ = "reports"
#     
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     reporter_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
#     target_type = Column(Enum('VIDEO', 'COMMENT', 'DANMAKU'), nullable=False)
#     target_id = Column(Integer, nullable=False)
#     reason = Column(String(100), nullable=False)
#     description = Column(Text, nullable=True)
#     status = Column(Integer, default=0)  # 0=待处理, 1=已处理, 2=已忽略
#     handler_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
#     admin_note = Column(Text, nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     handled_at = Column(DateTime, nullable=True)
