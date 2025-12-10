"""
应用配置管理
从环境变量读取配置
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "IKVCS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str  # 必需，从 .env 读取
    
    # 数据库配置
    DATABASE_URL: str  # 必需，从 .env 读取
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # JWT 配置
    JWT_SECRET_KEY: str  # 必需，从 .env 读取
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 小时
    
    # LLM API 配置
    LLM_API_KEY: str  # 必需，从 .env 读取
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-3.5-turbo"
    
    # 文件存储配置
    UPLOAD_DIR: str = "./uploads"
    VIDEO_DIR: str = "./videos"
    UPLOAD_TEMP_DIR: str = "./uploads/temp"  # 上传临时目录
    HLS_OUTPUT_DIR: str = "./videos/hls"  # HLS转码输出目录
    MAX_UPLOAD_SIZE: int = 2147483648  # 2GB
    CHUNK_SIZE: int = 5242880  # 分片大小：5MB
    UPLOAD_SESSION_EXPIRE: int = 604800  # 上传会话过期时间：7天（秒）
    
    # 转码配置
    TRANSCODE_MAX_CONCURRENT: int = 1  # 最大并发转码任务数
    TRANSCODE_RESOLUTIONS: str = "480p:854x480:800k:128k,720p:1280x720:2000k:128k"  # 转码清晰度配置
    
    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()
