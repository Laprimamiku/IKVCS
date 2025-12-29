"""
视频内容大纲提取服务
基于字幕内容，使用 LLM 提取视频章节/主题
"""
import json
import logging
from typing import List, Optional
from pathlib import Path

from app.core.config import settings
from app.core.types import SubtitleEntry, OutlineEntry
from app.services.video.subtitle_parser import SubtitleParser
from app.services.ai.llm_service import llm_service

logger = logging.getLogger(__name__)


class OutlineService:
    """视频大纲提取服务"""
    
    @staticmethod
    async def extract_outline(video_id: int, subtitle_url: str) -> List[OutlineEntry]:
        """
        提取视频内容大纲
        
        Args:
            video_id: 视频ID
            subtitle_url: 字幕文件URL
            
        Returns:
            List[Dict]: 大纲列表，每个条目包含 {title, start_time, description}
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
            outline = await OutlineService._llm_extract_outline(full_text, subtitles)
            
            return outline
            
        except Exception as e:
            logger.error(f"提取视频大纲失败 (video_id={video_id}): {e}")
            return []
    
    @staticmethod
    async def _llm_extract_outline(
        full_text: str,
        subtitles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        使用 LLM 提取大纲
        
        Args:
            full_text: 字幕完整文本
            subtitles: 字幕条目列表（包含时间信息）
            
        Returns:
            List[Dict]: 大纲列表
        """
        # 构建提示词
        prompt = f"""请分析以下视频字幕内容，提取视频的主要章节/主题大纲。

要求：
1. 识别视频的主要主题和章节
2. 每个章节包含：标题、开始时间（秒）、简要描述
3. 章节数量控制在 5-10 个
4. 返回 JSON 格式，格式如下：
[
  {{
    "title": "章节标题",
    "start_time": 0.0,
    "description": "章节描述"
  }}
]

字幕内容：
{full_text[:3000]}  # 限制长度，避免超出 token 限制

请返回 JSON 格式的大纲列表："""
        
        try:
            # 调用 LLM 服务
            messages = [
                {"role": "system", "content": "你是一个专业的视频内容分析助手，擅长从字幕中提取视频章节大纲。"},
                {"role": "user", "content": prompt}
            ]
            response_text = await llm_service._call_llm_api(messages)
            if not response_text:
                return []
            response = response_text
            
            # 解析响应
            outline = OutlineService._parse_llm_response(response)
            
            # 验证和补充时间信息
            outline = OutlineService._validate_and_fill_times(outline, subtitles)
            
            return outline
            
        except Exception as e:
            logger.error(f"LLM 提取大纲失败: {e}")
            return []
    
    @staticmethod
    def _parse_llm_response(response_text: str) -> List[OutlineEntry]:
        """解析 LLM 响应"""
        try:
            # 清理响应文本
            text = response_text.strip()
            if text.startswith('```'):
                # 移除代码块标记
                lines = text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines[-1].strip() == '```':
                    lines = lines[:-1]
                text = '\n'.join(lines)
            
            # 尝试解析 JSON
            data = json.loads(text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'outline' in data:
                return data['outline']
            else:
                return []
        except json.JSONDecodeError as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            return []
    
    @staticmethod
    def _validate_and_fill_times(
        outline: List[OutlineEntry],
        subtitles: List[SubtitleEntry]
    ) -> List[OutlineEntry]:
        """验证和补充时间信息"""
        result: List[OutlineEntry] = []
        for item in outline:
            start_time = item.get('start_time', 0)
            
            # 如果时间不在字幕范围内，尝试根据描述匹配
            if subtitles and (start_time == 0 or start_time > subtitles[-1]['end_time']):
                # 根据标题或描述在字幕中查找匹配的时间点
                title = item.get('title', '')
                for subtitle in subtitles:
                    if title.lower() in subtitle['text'].lower():
                        start_time = subtitle['start_time']
                        break
            
            result.append(OutlineEntry(
                title=item.get('title', '未知章节'),
                start_time=float(start_time),
                description=item.get('description', '')
            ))
        
        return result

