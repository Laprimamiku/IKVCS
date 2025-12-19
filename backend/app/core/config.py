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
    REDIS_HOST: str = "localhost"  # 默认值，可通过环境变量覆盖
    REDIS_PORT: int = 6379  # 默认值，可通过环境变量覆盖
    REDIS_DB: int = 0  # 默认值，可通过环境变量覆盖
    REDIS_PASSWORD: str = ""  # 默认值，可通过环境变量覆盖
    
    # JWT 配置
    JWT_SECRET_KEY: str  # 必需，从 .env 读取
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 小时
    
    # LLM API 配置
    LLM_API_KEY: str  # 必需，从 .env 读取
    LLM_BASE_URL: str = "https://api.openai.com/v1"  # 默认值，可通过环境变量覆盖
    LLM_MODEL: str = "gpt-3.5-turbo"  # 默认值，可通过环境变量覆盖
    
    # AI 分析配置
    AI_LOW_VALUE_KEYWORDS: str = "666,111,233,哈哈,打卡,第一,前排,来了"  # 低价值关键词列表（逗号分隔）
    
    # 文件存储配置
    STORAGE_ROOT: str = "./storage"  # 统一存储根目录
    
    # 存储根目录上传+视频
    # 上传相关
    UPLOAD_DIR: str = "./storage/uploads"  # 上传文件根目录
    UPLOAD_TEMP_DIR: str = "./storage/uploads/temp"  # 分片上传临时目录
    UPLOAD_AVATAR_DIR: str = "./storage/uploads/avatars"  # 用户头像
    UPLOAD_COVER_DIR: str = "./storage/uploads/covers"  # 视频封面
    UPLOAD_SUBTITLE_DIR: str = "./storage/uploads/subtitles"  # 字幕文件
    
    # 视频相关
    VIDEO_DIR: str = "./storage/videos"  # 视频根目录
    VIDEO_ORIGINAL_DIR: str = "./storage/videos/originals"  # 原始上传视频
    VIDEO_HLS_DIR: str = "./storage/videos/hls"  # HLS转码输出
    
    MAX_UPLOAD_SIZE: int = 2147483648  # 2GB
    CHUNK_SIZE: int = 5242880  # 分片大小：5MB
    UPLOAD_SESSION_EXPIRE: int = 604800  # 上传会话过期时间：7天（秒）
    
    # 转码配置
    TRANSCODE_MAX_CONCURRENT: int = 1  # 最大并发转码任务数
    # 转码清晰度配置（格式：name:resolution:video_bitrate:audio_bitrate）
    # 第一阶段（立即转码，快速可用）：360p、480p
    # 第二阶段（后台转码，渐进增强）：720p、1080p
    TRANSCODE_RESOLUTIONS: str = "360p:640x360:500k:96k,480p:854x480:800k:128k,720p:1280x720:2000k:128k,1080p:1920x1080:4000k:192k"
    # 转码策略：progressive（渐进式，先转低清晰度）或 all（一次性转所有清晰度）
    TRANSCODE_STRATEGY: str = "progressive"  # progressive 或 all
    # 第一阶段转码清晰度（快速转码，让用户能立即观看）
    TRANSCODE_PRIORITY_RESOLUTIONS: str = "360p,480p"  # 逗号分隔
    
    # CORS 配置（多个源用逗号分隔）
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"  # 默认值，可通过环境变量覆盖
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()
