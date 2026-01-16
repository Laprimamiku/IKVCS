"""
应用配置管理
从环境变量读取配置
"""
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

def _resolve_env_files() -> list[str]:
    base_dir = Path(__file__).resolve().parents[2]  # backend/
    env = os.getenv("APP_ENV", "development").strip() or "development"
    candidates = [
        base_dir / ".env",
        base_dir / f".env.{env}",
        base_dir / ".env.local",
        base_dir / f".env.{env}.local",
    ]
    return [str(path) for path in candidates if path.exists()]


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "IKVCS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str  # 必需，从 .env 读取
    
    # 数据库配置
    # 优先使用 DATABASE_URL，如果未配置则根据 IKVCS_DB_* 等字段构建默认连接串（对齐 Docker MySQL）
    DATABASE_URL: str | None = None
    DB_HOST: str = Field("127.0.0.1", alias="IKVCS_DB_HOST")
    DB_PORT: int = Field(3306, alias="IKVCS_DB_PORT")
    DB_USER: str = Field("root", alias="IKVCS_DB_USER")
    DB_PASSWORD: str = Field("", alias="IKVCS_DB_PASSWORD")
    DB_NAME: str = Field("ikvcs", alias="IKVCS_DB_NAME")
    
    # Redis 配置（默认对齐 Docker Redis 的 host/port，同时兼容原有 REDIS_* 环境变量）
    REDIS_HOST: str = "127.0.0.1"  # 默认值，可通过环境变量 REDIS_HOST 覆盖
    REDIS_PORT: int = 6379  # 默认值，可通过环境变量 REDIS_PORT 覆盖
    REDIS_DB: int = 0  # 默认值，可通过环境变量 REDIS_DB 覆盖
    REDIS_PASSWORD: str = ""  # 默认值，可通过环境变量 REDIS_PASSWORD 覆盖
    
    # MinIO 配置（为后续 P1/P2 存储抽象预留，与 docs/docker改造方案.md 对齐）
    MINIO_ENDPOINT: str = Field("http://127.0.0.1:9000", alias="IKVCS_MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field("", alias="IKVCS_MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field("", alias="IKVCS_MINIO_SECRET_KEY")
    MINIO_BUCKET: str = Field("ikvcs", alias="IKVCS_MINIO_BUCKET")
    
    # JWT 配置
    JWT_SECRET_KEY: str  # 必需，从 .env 读取
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 小时
    
    # LLM 模式配置 - 单一事实来源
    # off | cloud_only | local_only | hybrid（默认混合）
    LLM_MODE: str = "hybrid"
    
    # LLM API 配置（LLM_MODE=off/local_only 时允许为空）
    LLM_API_KEY: str = ""  # 可选，off/local_only 模式时允许为空
    
    # ==================== 智谱GLM配置（推荐） ====================
    # 文本模型配置（用于字幕分点、弹幕/评论分析等）
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"  # 智谱GLM API地址
    LLM_MODEL: str = "glm-4-flash"  # 文本模型：免费用户并发限制200次
    
    # 云端图像识别模型配置（用于视频抽帧审核）
    LLM_VISION_API_KEY: str = ""  # 图像识别API密钥，可选（与LLM_API_KEY相同）
    LLM_VISION_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"  # 智谱GLM视觉模型API地址
    LLM_VISION_MODEL: str = "glm-4v-plus"  # 视觉模型：免费用户并发限制5次

    # ASR (speech-to-text) model config
    ASR_API_KEY: str = ""  # optional; fallback to LLM_API_KEY when empty
    ASR_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ASR_MODEL: str = "GLM-ASR-2512"

    
    # ==================== CLIProxyAPI配置（已注释，保留备用） ====================
    # 之前的CLI API配置（通过CLIProxyAPI访问反重力模型）
    # LLM_BASE_URL: str = "https://cli.309831.xyz/v1"  # CLIProxyAPI地址
    # LLM_MODEL: str = "gemini-3-flash-preview"  # 反重力模型
    # LLM_VISION_BASE_URL: str = "https://cli.309831.xyz/v1"
    # LLM_VISION_MODEL: str = "gemini-3-flash-preview"
    # 注意：CLIProxyAPI存在429限流问题（model_cooldown），已切换为智谱GLM
    
    # 视觉模式配置（可选但建议）
    VISION_MODE: str = "hybrid"  # off | cloud_only | local_only | hybrid
    
    # 云端/本地模型切换配置（已废弃，请使用 LLM_MODE）
    USE_CLOUD_LLM: bool = True  # 兼容性保留：用于旧逻辑与 .env，推荐使用 LLM_MODE
    
    # 本地 LLM 配置
    LOCAL_LLM_ENABLED: bool = False  # 已废弃，请使用 LLM_MODE，仅作兼容性保留
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434/v1"  # 默认 Ollama 地址，可通过环境变量覆盖
    LOCAL_LLM_MODEL: str = "qwen2.5:0.5b-instruct"  # 默认使用 0.5B 指令模型，可通过环境变量覆盖
    LOCAL_LLM_THRESHOLD_LOW: int = 30  # 本地模型低分置信区间下限
    LOCAL_LLM_THRESHOLD_HIGH: int = 80 # 本地模型高分置信区间上限
    LOCAL_LLM_TIMEOUT: float = 60.0  # 本地模型超时时间（秒）
    LOCAL_LLM_MAX_CONCURRENT: int = 1  # 本地模型最大并发，默认单并发保护显存
    
    # 本地模型协作配置
    LOCAL_LLM_ESCALATE_TO_CLOUD: bool = True  # 本地模型低置信度时是否升级到云端
    LOCAL_LLM_ESCALATE_MIN_CHARS: int = 50  # 短文本不升级到云端，优先省 token/RTT
    LOCAL_LLM_ESCALATE_CONFIDENCE: float = 0.55  # 仅当本地置信度低于该值才升级到云端（降本增效）

    # 本地视觉模型（暂不启用：抽帧审核/字幕审核由云端模型负责）
    LOCAL_VISION_ENABLED: bool = False
    LOCAL_VISION_MODEL: str = "moondream:latest"
    
    # 硬件优化配置（针对 i5-11260H/16GB/RTX 3050 4GB）
    HARDWARE_PROFILE: str = "rtx3050_laptop"  # 硬件配置档案
    GPU_MEMORY_LIMIT_MB: int = 3500  # GPU显存限制（MB），为RTX 3050 4GB预留500MB
    CPU_THREADS_LIMIT: int = 4  # CPU线程限制，i5-11260H 6核限制为4线程避免过载
    MEMORY_USAGE_LIMIT_MB: int = 12000  # 内存使用限制（MB），16GB预留4GB给系统
    
    # Embedding API 配置
    EMBEDDING_MODEL: str = "embedding-3-pro"  # Embedding 模型名称，默认值可通过环境变量覆盖
    EMBEDDING_BASE_URL: str = "http://localhost:11434"  # 默认指向本地 Ollama，可通过环境变量覆盖
    
    # AI 分析配置
    AI_LOW_VALUE_KEYWORDS: str = "666,111,233,哈哈,打卡,第一,前排,来了"  # 低价值关键词列表（逗号分隔）
    DANMAKU_ANALYSIS_MIN_LEN: int = 20  # 弹幕长度>=该值时强制进入分析（避免被采样跳过）
    
    # AI 语义缓存配置（Layer 2）
    AI_SEMANTIC_CACHE_TTL: int = 604800  # 语义缓存过期时间（秒），默认7天
    AI_SEMANTIC_CACHE_THRESHOLD: float = 0.95  # 语义相似度阈值（0-1），当前为预留参数
    AI_SEMANTIC_CACHE_THRESHOLD_SHORT: float = 0.92  # 短文本语义缓存阈值（更保守，降低误命中）
    AI_SEMANTIC_CACHE_MIN_LEN: int = 12  # 低于该长度不做 embedding/语义缓存，减少本地开销
    AI_VECTOR_DIMENSION: int = 64  # 用于构造缓存Key的向量维度数（取前N维）
    AI_VECTOR_QUANTIZATION_PRECISION: int = 3  # 向量量化精度（小数位数）

    # Token节省和成本控制配置（高杠杆策略）
    TOKEN_SAVE_ENABLED: bool = True  # 是否启用Token节省策略
    TOKEN_SAVE_CONTENT_MAX_LENGTH: int = 500  # 内容最大长度，超出部分截断
    TOKEN_SAVE_REASON_MAX_LENGTH: int = 50  # AI推理reason字段最大长度
    TOKEN_SAVE_BATCH_SIZE: int = 10  # 批量处理大小，减少API调用次数
    TOKEN_SAVE_SAMPLING_RATE: float = 0.3  # 采样率，只处理30%的低风险内容
    TOKEN_SAVE_PROMPT_COMPRESSION: str = "moderate"  # Prompt压缩策略: conservative/moderate/aggressive
    TOKEN_SAVE_USE_COMPRESSED_PROMPTS: bool = False  # 是否使用压缩版Prompt模板（更激进，节省更多Token）

    # 高频短文本（弹幕/评论）降本增效：队列批处理 + 控制 trace 写入
    AI_ANALYSIS_QUEUE_ENABLED: bool = True  # 弹幕/评论分析是否走队列批处理（推荐开启）
    AI_ANALYSIS_QUEUE_WORKERS: int = 1  # 队列消费者数量（RTX 3050 建议 1）
    AI_ANALYSIS_QUEUE_MAXSIZE: int = 2000  # 队列最大积压（避免异常流量导致内存膨胀）
    AI_ANALYSIS_BATCH_SIZE: int = 30  # 单批处理最大条数
    AI_ANALYSIS_BATCH_WINDOW_MS: int = 500  # 批量聚合窗口（毫秒）
    AI_ANALYSIS_TRACE_MODE: str = "risky"  # none | all | risky | sample
    AI_ANALYSIS_TRACE_SAMPLE_RATE: float = 0.05  # sample 模式下抽样比例
    AI_ANALYSIS_TRACE_RISK_SCORE: int = 55  # 低于该分数默认写入 trace 便于审计
    AI_ANALYSIS_TRACE_LOW_CONFIDENCE: float = 0.6  # 低置信度默认写入 trace
    
    # 云端模型并发控制配置（精细化）
    # 注意：智谱GLM免费用户并发限制
    # - glm-4v-plus（视觉模型）：5次并发
    # - glm-4-flash（文本模型）：200次并发
    CLOUD_FRAME_REVIEW_MAX_CONCURRENT: int = 5  # 云端帧审核最大并发数（GLM-4V-Plus免费用户限制：5次）
    CLOUD_MAX_CALLS_PER_VIDEO: int = 50  # 每个视频云端模型最大调用次数（成本控制）
    CLOUD_MAX_INPUT_CHARS_PER_VIDEO: int = 5000  # 每个视频云端模型最大输入字符数（Token控制）
    CLOUD_DAILY_BUDGET_CALLS: int = 1000  # 每日云端调用预算限制
    CLOUD_HOURLY_BUDGET_CALLS: int = 100  # 每小时云端调用预算限制
    
    # 图片批量审核配置（模型调度优化）
    FRAME_BATCH_REVIEW_ENABLED: bool = True  # 是否启用批量审核（图片拼接）
    FRAME_GRID_ROWS: int = 3  # 网格行数（默认3×3）
    FRAME_GRID_COLS: int = 3  # 网格列数（默认3×3）

    # 多模态两阶段审核配置（Stage 1 低成本初筛 + Stage 2 精审）
    TWO_STAGE_REVIEW_ENABLED: bool = True
    TWO_STAGE_STAGE1_MAX_FRAMES: int = 8  # Stage 1 抽帧审核数量上限（用于控成本）
    TWO_STAGE_STAGE2_TRIGGER_MIN_SCORE: int = 85  # Stage 1 最低分低于该值则进入 Stage 2

    # AI 多智能体配置（Layer 3.1-3.4）
    MULTI_AGENT_ENABLED: bool = False  # 是否启用多智能体陪审团（True/False默认关闭） 
    MULTI_AGENT_CONFLICT_THRESHOLD: float = 0.2  # 冲突阈值（分数差异超过20%视为冲突）

    # 云端调用预算控制（移除重复定义）
    # CLOUD_MAX_CALLS_PER_VIDEO 已在上方定义

    # AI 反馈式自我纠错配置（Layer 4）
    SELF_CORRECTION_ENABLED: bool = False  # 是否启用反馈式自我纠错
    SELF_CORRECTION_MIN_SAMPLES: int = 10  # 触发分析的最小样本数量
    SELF_CORRECTION_AUTO_UPDATE: bool = False  # 是否自动更新Prompt（建议手动审核）
    SELF_CORRECTION_ANALYSIS_DAYS: int = 7  # 默认分析最近N天的错误

    # GPU 管理配置（解决 LLM 推理时的电感啸叫问题）- 仅在本地模式时使用
    GPU_MANAGEMENT_ENABLED: bool = False  # 是否启用 GPU 管理（默认禁用），可通过环境变量 GPU_MANAGEMENT_ENABLED 覆盖
    GPU_ID: int = 0  # GPU 设备 ID（默认 0）
    GPU_LOCKED_CLOCK: int = 1500  # 锁定的核心频率（MHz），默认 1500MHz（建议范围：1200-1500）
    GPU_POWER_LIMIT_RATIO: float = 0.75  # 功耗限制比例（0-1），默认 0.75（75%），建议范围：0.7-0.8
    
    # 视觉模式配置已移至上方

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
    
    # 视频帧提取配置
    MAX_FRAMES_PER_VIDEO: int = 50  # 每个视频最多提取的帧数量（避免存储过大）
    FRAME_EXTRACT_MAX_COUNT: int = 30  # 兼容旧配置
    FRAME_EXTRACT_INTERVAL: int = 5  # 均匀采样间隔（秒），从10秒改为5秒，提高采样密度
    FRAME_EXTRACT_MIN_FRAMES: int = 10  # 每个视频最少提取的帧数量（确保短视频也能有足够的采样）
    FRAME_REVIEW_MAX_CONCURRENT: int = 3  # 帧审核最大并发数（避免超出模型算力，可根据 GPU 显存调整）
    # GPU 优化建议（根据显存大小调整）：
    # - 4GB 显存（如 RTX 3050）：3 并发（推荐，避免 OOM）
    # - 8GB 显存：5-6 并发
    # - 16GB+ 显存：8-12 并发
    # 注意：如果遇到 GPU OOM 错误，请降低并发数
    
    # 转码配置
    TRANSCODE_MAX_CONCURRENT: int = 1  # 最大并发转码任务数（RTX 3050 4GB建议保持1，避免GPU显存不足）
    # 转码清晰度配置（格式：name:resolution:video_bitrate:audio_bitrate）
    # 第一阶段（立即转码，快速可用）：360p、480p
    # 第二阶段（后台转码，渐进增强）：720p、1080p
    TRANSCODE_RESOLUTIONS: str = "360p:640x360:500k:96k,480p:854x480:800k:128k,720p:1280x720:2000k:128k,1080p:1920x1080:4000k:192k"
    # 转码策略：progressive（渐进式，先转低清晰度）或 all（一次性转所有清晰度）
    TRANSCODE_STRATEGY: str = "progressive"  # progressive 或 all
    # 第一阶段转码清晰度（快速转码，让用户能立即观看）
    TRANSCODE_PRIORITY_RESOLUTIONS: str = "360p,480p"  # 逗号分隔
    # GPU硬件加速配置（RTX 3050支持NVENC）
    TRANSCODE_USE_GPU: bool = True  # 是否使用GPU硬件加速（默认禁用，避免AV1等格式兼容性问题）
    TRANSCODE_GPU_DEVICE: int = 0  # GPU设备编号（多GPU时使用）
    
    # 全局功能开关
    AUTO_REVIEW_ENABLED: bool = False  # 是否启用自动审核（视频上传后自动审核）
    HIGH_BITRATE_TRANSCODE_ENABLED: bool = False  # 是否启用高码率转码（720p/1080p）
    
    # CORS 配置（多个源用逗号分隔）
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"  # 默认值，可通过环境变量 CORS_ORIGINS 覆盖

    # 应用时区（用于 API 输出时间序列化等）
    # 建议使用 IANA 时区名，例如：Asia/Shanghai
    APP_TIMEZONE: str = "Asia/Shanghai"
    
    class Config:
        # Load backend env files with simple layered overrides.
        env_file = _resolve_env_files()
        case_sensitive = True
        extra = "ignore"

# 全局配置实例
settings = Settings()
