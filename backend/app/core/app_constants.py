"""
应用常量定义

统一管理分页大小、超时时间等配置常量，避免魔法数字
"""
from typing import Final

# 分页配置
DEFAULT_PAGE_SIZE: Final[int] = 20  # 默认每页数量
MAX_PAGE_SIZE: Final[int] = 100  # 最大每页数量
MIN_PAGE_SIZE: Final[int] = 1  # 最小每页数量

# 推荐服务配置
RECOMMENDATION_HOT_LIMIT: Final[int] = 20  # 热门视频数量
RECOMMENDATION_SIMILAR_LIMIT: Final[int] = 10  # 同类视频数量
RECOMMENDATION_PERSONALIZED_LIMIT: Final[int] = 10  # 个性化视频数量
RECOMMENDATION_TOTAL_LIMIT: Final[int] = 20  # 最终返回数量

# 缓存 TTL（秒）
CACHE_TTL_SHORT: Final[int] = 300  # 5分钟
CACHE_TTL_MEDIUM: Final[int] = 600  # 10分钟
CACHE_TTL_LONG: Final[int] = 3600  # 1小时

# 时间相关配置
RECENT_DAYS: Final[int] = 30  # 最近N天行为有效（用于推荐服务）

