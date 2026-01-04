"""
视频管理 API 模块

按职责拆分的路由文件：
- query.py: 视频查询（列表、详情、状态、大纲、摘要、知识点）
- management.py: 视频管理（更新、删除、上传封面/字幕）
- interaction.py: 视频互动（点赞、收藏）
- ai.py: AI功能（生成大纲、AI分析、生成摘要）
- transcode.py: 转码功能（开发调试）
"""

from fastapi import APIRouter
from .query import router as query_router
from .management import router as management_router
from .interaction import router as interaction_router
from .ai import router as ai_router
from .transcode import router as transcode_router

# 创建主路由
router = APIRouter()

# 注册子路由（保持原有路径结构）
router.include_router(query_router, tags=["video-query"])
router.include_router(management_router, tags=["video-management"])
router.include_router(interaction_router, tags=["video-interaction"])
router.include_router(ai_router, tags=["video-ai"])
router.include_router(transcode_router, tags=["video-transcode"])

