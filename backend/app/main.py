"""
IKVCS FastAPI 应用入口

这个文件是整个后端应用的入口
相当于 Spring Boot 的 Application.java
"""
import logging
import asyncio
import os

from logging.handlers import RotatingFileHandler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import videos

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, users, categories, upload, videos, danmaku, websocket
from app.api.websocket import start_redis_listener

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

# ==================== 全局异常处理 ====================
# 类比 Java：相当于 @ControllerAdvice + @ExceptionHandler

from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    处理自定义应用异常
    
    类比 Java：
        @ExceptionHandler(AppException.class)
        public ResponseEntity<ErrorResponse> handleAppException(AppException e) {
            return ResponseEntity.status(e.getStatusCode())
                .body(new ErrorResponse(e.getMessage()));
        }
    """
    logger.error(
        f"应用异常: {exc.message} (状态码: {exc.status_code})",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    处理所有未捕获的异常
    
    类比 Java：
        @ExceptionHandler(Exception.class)
        public ResponseEntity<ErrorResponse> handleGeneralException(Exception e) {
            logger.error("未捕获的异常", e);
            return ResponseEntity.status(500)
                .body(new ErrorResponse("服务器内部错误"));
        }
    """
    logger.error(
        f"未捕获的异常: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": "系统出现异常，请稍后重试或联系管理员",
            "status_code": 500
        }
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

# 启动事件：创建数据库表 + 启动 Redis 监听
@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行
    
    创建所有数据库表（如果不存在）
    相当于 Spring Boot 的 @PostConstruct
    """
    logger.info("应用启动中...")
    logger.info(f"环境：{settings.APP_ENV}")
    logger.info(f"调试模式：{settings.DEBUG}")
    
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败：{e}")

    # 启动 Redis 监听器（任务10测试问题）
    # 关键修改：将任务赋值给 app.state.redis_task，防止被垃圾回收(GC)
    from app.api.websocket import start_redis_listener
    app.state.redis_task = asyncio.create_task(start_redis_listener())
    logger.info("后台 Redis 监听任务已启动并绑定")
    
    logger.info("应用启动完成")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("应用关闭中...")

# 配置静态文件服务（用于访问上传的文件与转码输出）
os.makedirs("uploads/avatars", exist_ok=True)
os.makedirs("videos/hls", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

# 注册路由
# 类比 Spring Boot：相当于在 Application.java 中配置 Controller 扫描路径
from app.api import auth, users, categories, upload, videos
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["分类"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["上传"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["视频"])

# TODO: 后续任务会注册更多路由
app.include_router(danmaku.router, prefix="/api/v1", tags=["弹幕"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理"])
# app.include_router(interactions.router, prefix="/api/v1", tags=["互动"])

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