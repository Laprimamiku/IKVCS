"""
IKVCS FastAPI 应用入口

这个文件是整个后端应用的入口
相当于 Spring Boot 的 Application.java
"""
import logging
import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, users, categories, upload, danmaku, websocket, comments, interactions
from app.api.videos import router as videos_router

# 创建日志目录
os.makedirs("logs", exist_ok=True)

# 配置日志系统（使用自定义格式化器）
from app.core.logging_config import setup_logging
setup_logging(
    debug=settings.DEBUG,
    log_file='logs/app.log'
)

logger = logging.getLogger(__name__)

# 启动时打印LLM配置信息（便于确认模型切换）
logger.info("=" * 80)
logger.info("📋 LLM配置信息（启动时）:")
logger.info(f"  LLM_MODE: {settings.LLM_MODE}")
logger.info(f"  文本模型: {settings.LLM_MODEL} @ {settings.LLM_BASE_URL}")
logger.info(f"  视觉模型: {settings.LLM_VISION_MODEL or settings.LLM_MODEL} @ {settings.LLM_VISION_BASE_URL or settings.LLM_BASE_URL}")
logger.info(f"  API Key: {'已配置' if settings.LLM_API_KEY else '未配置'}")
logger.info("=" * 80)

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
            "status_code": exc.status_code,
            "error_code": exc.error_code.value  # 添加错误码
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
    
    from app.core.error_codes import ErrorCode
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": "系统出现异常，请稍后重试或联系管理员",
            "status_code": 500,
            "error_code": ErrorCode.INTERNAL_ERROR.value  # 添加错误码
        }
    )

# CORS 配置（跨域资源共享）
# 允许前端（Vue）访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],  # 从配置读取允许的域名
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)

# 启动事件：创建数据库表 + 启动 Redis 监听 + GPU 管理
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
    
    # 初始化存储目录结构（启动时再次确保目录存在）
    try:
        from app.utils.storage_utils import ensure_storage_structure
        directories = ensure_storage_structure()
        logger.info(f"存储目录结构初始化完成：{len(directories)} 个目录")
    except Exception as e:
        logger.error(f"存储目录初始化失败：{e}")
    
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

    # 高频短文本 AI 分析队列（批量处理/限峰）
    try:
        from app.services.ai.llm_service import llm_service
        await llm_service.start_analysis_queue()
    except Exception as e:
        logger.error(f"AI 分析队列启动失败: {e}", exc_info=True)
    
    # GPU 管理：当前为手动模式
    # 注意：GPU 配置需要手动执行命令，详见 backend/docs/GPU_MANAGEMENT.md
    # 锁定命令：nvidia-smi -i 0 -lgc 1500
    # 恢复命令：nvidia-smi -i 0 -rgc
    logger.info("GPU 管理：当前为手动模式，请参考 backend/docs/GPU_MANAGEMENT.md 了解如何手动锁定和恢复 GPU")
    
    logger.info("应用启动完成")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("应用关闭中...")

    # 停止 AI 分析队列
    try:
        from app.services.ai.llm_service import llm_service
        await llm_service.stop_analysis_queue()
    except Exception as e:
        logger.debug(f"AI 分析队列关闭失败（可忽略）: {e}")
    
    # GPU 管理：仅在可能使用本地模型且启用 GPU 管理时执行
    llm_mode = getattr(settings, "LLM_MODE", "hybrid").lower()
    uses_local_llm = llm_mode in ("local_only", "hybrid")
    if uses_local_llm and settings.GPU_MANAGEMENT_ENABLED:
        try:
            from app.utils.gpu_manager import get_gpu_manager
            gpu_manager = get_gpu_manager()
            if gpu_manager and gpu_manager._is_configured:
                logger.info("检测到 GPU 仍处于配置状态，正在恢复...")
                success = gpu_manager.reset_to_default()
                if success:
                    logger.info("GPU 已重置到默认状态")
                else:
                    logger.warning("GPU 重置失败，但服务将继续关闭")
        except Exception as e:
            logger.error(f"GPU 重置失败：{e}", exc_info=True)
            # GPU 重置失败不应阻止服务关闭
    else:
        logger.debug("GPU 管理已禁用（未使用本地模型或 GPU 管理未启用）")
    
    logger.info("应用关闭完成")

# 初始化存储目录（在挂载静态文件之前）
from app.utils.storage_utils import ensure_storage_structure
try:
    ensure_storage_structure()
    logger.info("存储目录初始化完成")
except Exception as e:
    logger.error(f"存储目录初始化失败：{e}")

# 配置静态文件服务（用于访问上传的文件与转码输出）
# 使用配置中的路径，确保与存储结构一致
# 新结构：
# - /uploads -> ./storage/uploads (包含 covers, avatars, subtitles 等)
# - /videos -> ./storage/videos (包含 hls, originals 等)
import os
upload_dir = os.path.abspath(settings.UPLOAD_DIR)
video_dir = os.path.abspath(settings.VIDEO_DIR)
avatar_dir = os.path.abspath(settings.UPLOAD_AVATAR_DIR)
cover_dir = os.path.abspath(settings.UPLOAD_COVER_DIR)

logger.info(f"挂载静态文件目录：/uploads -> {upload_dir}")
logger.info(f"挂载静态文件目录：/videos -> {video_dir}")
logger.info(f"挂载静态文件目录：/avatars -> {avatar_dir}")
logger.info(f"挂载静态文件目录：/covers -> {cover_dir}")

app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
app.mount("/videos", StaticFiles(directory=video_dir), name="videos")
app.mount("/avatars", StaticFiles(directory=avatar_dir), name="avatars")
app.mount("/covers", StaticFiles(directory=cover_dir), name="covers")

# 注册路由
# 类比 Spring Boot：相当于在 Application.java 中配置 Controller 扫描路径
from app.api import auth, users, categories, upload, danmaku, websocket, comments, interactions, search
from app.api.videos import router as videos_router
from app.api.admin import router as admin_router
from app.api.recommendations import router as recommendations_router

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["分类"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["上传"])
app.include_router(videos_router, prefix="/api/v1/videos", tags=["视频"])

# 兼容无尾随斜杠访问：避免 /api/v1/videos -> /api/v1/videos/ 的 307 Redirect
from app.api.videos.query import get_video_list
app.add_api_route(
    "/api/v1/videos",
    get_video_list,
    methods=["GET"],
    name="get_video_list_noslash",
    include_in_schema=False,
)

app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
app.include_router(danmaku.router, prefix="/api/v1", tags=["弹幕"])
app.include_router(comments.router, prefix="/api/v1", tags=["评论"]) 
app.include_router(interactions.router, prefix="/api/v1", tags=["互动"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["管理"])
app.include_router(search.router, prefix="/api/v1/search", tags=["搜索"])
app.include_router(recommendations_router, prefix="/api/v1/recommendations", tags=["推荐"])


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
