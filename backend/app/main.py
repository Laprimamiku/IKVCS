"""
IKVCS FastAPI 应用入口

这个文件是整个后端应用的入口
相当于 Spring Boot 的 Application.java
"""
import logging
from logging.handlers import RotatingFileHandler
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base

# 创建日志目录
os.makedirs("logs", exist_ok=True)

# 配置日志系统
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[
        # 控制台输出
        logging.StreamHandler(),
        # 文件输出（自动轮转，最大 10MB，保留 10 个文件）
        RotatingFileHandler(
            'logs/app.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
    ]
)

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="IKVCS API",
    description="智能知识型视频社区系统 API",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI 地址
    redoc_url="/redoc"  # ReDoc 地址
)

# CORS 配置（跨域资源共享）
# 允许前端（Vue）访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),  # 从配置读取允许的域名
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)

# 启动事件：创建数据库表
@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行
    
    创建所有数据库表（如果不存在）
    相当于 Spring Boot 的 @PostConstruct
    """
    logger.info("🚀 应用启动中...")
    logger.info(f"📝 环境：{settings.APP_ENV}")
    logger.info(f"🔧 调试模式：{settings.DEBUG}")
    
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表创建成功")
    except Exception as e:
        logger.error(f"❌ 数据库表创建失败：{e}")
    
    logger.info("✅ 应用启动完成")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("👋 应用关闭中...")

# TODO: 注册路由
# from app.api import auth, users, videos, upload, interactions, danmaku, websocket, admin
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
# app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
# app.include_router(videos.router, prefix="/api/v1/videos", tags=["视频"])
# app.include_router(upload.router, prefix="/api/v1/upload", tags=["上传"])
# app.include_router(interactions.router, prefix="/api/v1", tags=["互动"])
# app.include_router(danmaku.router, prefix="/api/v1", tags=["弹幕"])
# app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理"])

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "IKVCS API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV
    }
