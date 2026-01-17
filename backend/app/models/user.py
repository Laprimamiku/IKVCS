"""
用户数据模型

这个文件定义了 User 表的结构
相当于 Java 的 Entity 类 + MyBatis 的 Mapper XML

需求：1.1-1.5（用户注册与认证）, 2.1-2.4（用户信息管理）
"""
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class User(Base):
    """
    用户模型
    
    对应数据库表：users
    
    字段说明：
    - id: 主键，自增
    - username: 用户名（唯一，用于登录）
    - password_hash: 密码哈希（bcrypt 加密，不存储明文）
    - nickname: 昵称（用于显示）
    - avatar: 头像 URL
    - intro: 个人简介
    - role: 角色（user=普通用户, admin=管理员）
    - status: 状态（0=封禁, 1=正常）
    - last_login_time: 最后登录时间
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    __tablename__ = "users"
    
    # 基本字段
    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    nickname = Column(String(50), nullable=False, comment="昵称")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    intro = Column(String(500), nullable=True, comment="个人简介")
    
    # 权限和状态
    role = Column(Enum('user', 'admin', name='user_role'), default='user', comment="角色")
    status = Column(Integer, default=1, comment="状态：0=封禁, 1=正常")
    # profile_visible 字段暂时不添加到模型中，因为数据库表中可能还没有该字段
    # 如果需要，可以通过数据库迁移添加该字段
    
    # 时间字段
    last_login_time = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系映射（后续会用到）
    # videos = relationship("Video", back_populates="uploader")
    # danmakus = relationship("Danmaku", back_populates="user")
    # comments = relationship("Comment", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', nickname='{self.nickname}')>"
