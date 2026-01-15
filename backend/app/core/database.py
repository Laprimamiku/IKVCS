"""
数据库连接配置

这个文件的作用：
1. 创建数据库引擎（Engine）- 相当于 Java 的 DataSource
2. 创建会话工厂（SessionLocal）- 相当于 MyBatis 的 SqlSessionFactory
3. 提供依赖注入函数（get_db）- 相当于 Spring 的 @Autowired
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings


def _build_database_url() -> str:
    """
    根据配置构建最终的数据库连接字符串。
    
    优先使用 DATABASE_URL；如果未配置，则根据 IKVCS_DB_* 等字段构建
    默认的 MySQL + PyMySQL 连接串，以便本地后端直接连接 Docker 中的 MySQL。
    """
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    user = settings.DB_USER
    password = settings.DB_PASSWORD or ""
    host = settings.DB_HOST
    port = settings.DB_PORT
    db = settings.DB_NAME
    
    # 使用 mysql+pymysql，与 backend/requirements.txt 中的依赖保持一致
    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
        "?charset=utf8mb4"
    )


# 创建数据库引擎
# echo=True 会打印 SQL 语句（开发时方便调试，生产环境建议关闭）
engine = create_engine(
    _build_database_url(),
    echo=settings.DEBUG,  # 开发环境打印 SQL
    pool_pre_ping=True,   # 连接池预检查（防止连接失效）
    pool_recycle=3600     # 连接回收时间（1小时）
)

# 创建会话工厂
# autocommit=False: 需要手动提交事务
# autoflush=False: 需要手动刷新到数据库
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类（所有数据模型都继承这个类）
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）
    
    这个函数会被 FastAPI 的 Depends() 调用
    相当于 Spring 的 @Autowired
    
    使用方式：
    @router.get("/users")
    def get_users(db: Session = Depends(get_db)):
        users = db.query(User).all()
        return users
    """
    db = SessionLocal()
    try:
        yield db  # 返回数据库会话
    finally:
        db.close()  # 请求结束后自动关闭连接
