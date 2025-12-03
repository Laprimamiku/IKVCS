"""
数据模型包

这个文件导出所有数据模型，方便其他模块导入

使用方式：
from app.models import User, Video, Category
"""

from app.models.user import User
from app.models.video import Video, Category

# 导出所有模型（方便导入）
__all__ = [
    "User",
    "Video",
    "Category",
]
