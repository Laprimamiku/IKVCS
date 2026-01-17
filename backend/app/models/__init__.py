"""
数据模型包

这个文件导出所有数据模型，方便其他模块导入

使用方式：
from app.models import User, Video, Category, UploadSession, Danmaku, Comment, Report
"""

from app.models.user import User
from app.models.video import Video, Category
from app.models.upload import UploadSession
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.models.report import Report
from app.models.ai_training_sample import AiTrainingSample
from app.models.ai_prompt_task import AiPromptTask
from app.models.ai_prompt_experiment import AiPromptExperiment
from app.models.watch_history import WatchHistory
from app.models.collection_folder import CollectionFolder
from app.models.user_follow import UserFollow
from app.models.video_tag import VideoTag

# AI 相关模型（可选）
try:
    from app.models.ai_agent_analysis import AgentAnalysis
    _has_agent_analysis = True
except ImportError:
    _has_agent_analysis = False

# 导出所有模型（方便导入）
__all__ = [
    "User",
    "Video",
    "Category",
    "UploadSession",
    "Danmaku",
    "Comment",
    "Report",
    "WatchHistory",
    "CollectionFolder",
    "UserFollow",
    "VideoTag",
    "AiPromptTask",
    "AiPromptExperiment",
]

if _has_agent_analysis:
    __all__.append("AgentAnalysis")
