"""
管理后台 API 模块

按功能域拆分的路由文件：
- category_admin.py: 分类管理
- video_admin.py: 视频审核、封禁、恢复
- user_admin.py: 用户管理
- report_admin.py: 举报处理
- statistics_admin.py: 数据统计
- ai_admin.py: AI管理、自我纠错
"""

from fastapi import APIRouter
from .category_admin import router as category_router
from .video_admin import router as video_router
from .user_admin import router as user_router
from .report_admin import router as report_router
from .statistics_admin import router as statistics_router
from .ai_admin import router as ai_router

# 创建主路由
router = APIRouter()

# 注册子路由（保持原有路径结构）
router.include_router(category_router, prefix="/categories", tags=["admin-category"])
router.include_router(video_router, prefix="/videos", tags=["admin-video"])
router.include_router(user_router, prefix="/users", tags=["admin-user"])
router.include_router(report_router, prefix="/reports", tags=["admin-report"])
router.include_router(statistics_router, prefix="/statistics", tags=["admin-statistics"])
router.include_router(ai_router, prefix="/ai", tags=["admin-ai"])

