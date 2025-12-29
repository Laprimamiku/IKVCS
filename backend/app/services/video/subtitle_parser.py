"""
字幕解析服务
支持 SRT、VTT、JSON、ASS 格式
"""
import re
import json
import logging
from typing import List
from pathlib import Path

from app.core.types import SubtitleEntry

logger = logging.getLogger(__name__)


class SubtitleParser:
    """字幕解析器"""
    
    @staticmethod
    def parse_subtitle_file(file_path: str) -> List[SubtitleEntry]:
        """
        解析字幕文件
        
        Args:
            file_path: 字幕文件路径
            
        Returns:
            List[Dict]: 字幕条目列表，每个条目包含 {start_time, end_time, text}
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"字幕文件不存在: {file_path}")
        
        ext = path.suffix.lower()
        
        if ext == '.srt':
            return SubtitleParser._parse_srt(file_path)
        elif ext == '.vtt':
            return SubtitleParser._parse_vtt(file_path)
        elif ext == '.json':
            return SubtitleParser._parse_json(file_path)
        elif ext == '.ass':
            return SubtitleParser._parse_ass(file_path)
        else:
            raise ValueError(f"不支持的字幕格式: {ext}")
    
    @staticmethod
    def _parse_srt(file_path: str) -> List[SubtitleEntry]:
        """解析 SRT 格式"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SRT 格式：序号、时间轴、文本
        pattern = r'(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\d+\s*\n|\n*$)'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        subtitles = []
        for match in matches:
            start_time = SubtitleParser._srt_time_to_seconds(match.group(2))
            end_time = SubtitleParser._srt_time_to_seconds(match.group(3))
            text = match.group(4).strip().replace('\n', ' ')
            
            subtitles.append({
                'start_time': start_time,
                'end_time': end_time,
                'text': text
            })
        
        return subtitles
    
    @staticmethod
    def _parse_vtt(file_path: str) -> List[SubtitleEntry]:
        """解析 VTT 格式"""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        subtitles = []
        current_subtitle = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
                continue
            
            # 时间轴行：00:00:00.000 --> 00:00:05.000
            time_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})', line)
            if time_match:
                if current_subtitle:
                    subtitles.append(current_subtitle)
                start_time = SubtitleParser._vtt_time_to_seconds(time_match.group(1))
                end_time = SubtitleParser._vtt_time_to_seconds(time_match.group(2))
                current_subtitle = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': ''
                }
            elif current_subtitle:
                if current_subtitle['text']:
                    current_subtitle['text'] += ' '
                current_subtitle['text'] += line
        
        if current_subtitle:
            subtitles.append(current_subtitle)
        
        return subtitles
    
    @staticmethod
    def _parse_json(file_path: str) -> List[SubtitleEntry]:
        """解析 JSON 格式"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        subtitles = []
        if isinstance(data, list):
            for item in data:
                subtitles.append({
                    'start_time': item.get('start', item.get('start_time', 0)),
                    'end_time': item.get('end', item.get('end_time', 0)),
                    'text': item.get('text', item.get('content', ''))
                })
        elif isinstance(data, dict) and 'subtitles' in data:
            for item in data['subtitles']:
                subtitles.append({
                    'start_time': item.get('start', item.get('start_time', 0)),
                    'end_time': item.get('end', item.get('end_time', 0)),
                    'text': item.get('text', item.get('content', ''))
                })
        
        return subtitles
    
    @staticmethod
    def _parse_ass(file_path: str) -> List[SubtitleEntry]:
        """解析 ASS 格式（简化版）"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        subtitles = []
        # ASS 格式：Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,文本内容
        pattern = r'Dialogue:.*?,\d+:\d{2}:\d{2}\.\d{2},\d+:\d{2}:\d{2}\.\d{2},.*?,,(.*)'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            # 简化处理：提取时间（需要更复杂的解析）
            # 这里返回一个简化版本
            text = match.group(1).strip()
            if text:
                subtitles.append({
                    'start_time': 0,  # ASS 格式需要更复杂的解析
                    'end_time': 0,
                    'text': text
                })
        
        return subtitles
    
    @staticmethod
    def _srt_time_to_seconds(time_str: str) -> float:
        """SRT 时间格式转秒数：00:00:00,000"""
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    @staticmethod
    def _vtt_time_to_seconds(time_str: str) -> float:
        """VTT 时间格式转秒数：00:00:00.000"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    @staticmethod
    def extract_text_only(subtitles: List[SubtitleEntry]) -> str:
        """
        提取字幕纯文本（用于 LLM 分析）
        
        Args:
            subtitles: 字幕条目列表
            
        Returns:
            str: 合并后的文本内容
        """
        texts = [item['text'] for item in subtitles if item.get('text')]
        return ' '.join(texts)

