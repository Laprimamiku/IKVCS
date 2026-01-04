"""
视频内容大纲提取服务
基于字幕内容，使用 LLM 提取视频章节/主题
"""
import logging
from typing import List, Optional, Callable
from pathlib import Path

from app.core.config import settings
from app.core.types import OutlineEntry
from app.services.video.subtitle_parser import SubtitleParser
from app.services.video.outline.outline_llm import llm_extract_outline
from app.services.video.outline.outline_validator import merge_outlines

logger = logging.getLogger(__name__)


class OutlineService:
    """视频大纲提取服务"""
    
    @staticmethod
    async def extract_outline(
        video_id: int, 
        subtitle_url: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[OutlineEntry]:
        """
        提取视频内容大纲
        
        Args:
            video_id: 视频ID
            subtitle_url: 字幕文件URL
            progress_callback: 进度回调函数（可选）
            
        Returns:
            List[OutlineEntry]: 大纲列表，每个条目包含 {title, start_time, description, key_points}
        """
        try:
            # 1. 解析字幕文件
            subtitle_path = Path(settings.STORAGE_ROOT) / subtitle_url.lstrip('/')
            if not subtitle_path.exists():
                # 尝试从 uploads 目录查找
                subtitle_path = Path(settings.UPLOAD_SUBTITLE_DIR) / Path(subtitle_url).name
                if not subtitle_path.exists():
                    logger.warning(f"字幕文件不存在: {subtitle_url}")
                    return []
            
            subtitles = SubtitleParser.parse_subtitle_file(str(subtitle_path))
            if not subtitles:
                logger.warning(f"字幕文件为空: {subtitle_url}")
                return []
            
            # 2. 提取文本内容
            full_text = SubtitleParser.extract_text_only(subtitles)
            if len(full_text) < 50:  # 文本太短，无法提取大纲
                return []
            
            # 3. 使用 LLM 提取大纲
            if progress_callback:
                await progress_callback(10, "开始分析字幕内容...")
            
            outline = await llm_extract_outline(
                full_text, 
                subtitles,
                progress_callback=progress_callback
            )
            
            # 4. 合并和优化大纲（如果是分段处理，需要合并）
            if outline:
                outline = merge_outlines(outline, subtitles)
            
            if progress_callback:
                await progress_callback(100, f"大纲生成完成，共 {len(outline) if outline else 0} 个章节")
            
            return outline
            
        except Exception as e:
            logger.error(f"提取视频大纲失败 (video_id={video_id}): {e}")
            return []
