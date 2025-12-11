"""
存储目录初始化工具

确保所有存储目录结构符合规范
"""
import os
from pathlib import Path
from app.core.config import settings


def ensure_storage_structure():
    """
    确保存储目录结构完整
    
    根据优化结构文档创建所有必要的目录：
    - storage/uploads/ (根目录)
    - storage/uploads/temp/
    - storage/uploads/avatars/
    - storage/uploads/covers/
    - storage/uploads/subtitles/
    - storage/videos/ (根目录)
    - storage/videos/originals/
    - storage/videos/hls/
    """
    directories = [
        settings.STORAGE_ROOT,
        settings.UPLOAD_DIR,
        settings.UPLOAD_TEMP_DIR,
        settings.UPLOAD_AVATAR_DIR,
        settings.UPLOAD_COVER_DIR,
        settings.UPLOAD_SUBTITLE_DIR,
        settings.VIDEO_DIR,
        settings.VIDEO_ORIGINAL_DIR,
        settings.VIDEO_HLS_DIR,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    return directories

