"""
大纲验证和优化模块

职责：验证大纲时间信息，确保覆盖整个视频
"""
import logging
from typing import List, Dict, Any

from app.core.types import SubtitleEntry, OutlineEntry

logger = logging.getLogger(__name__)


def validate_and_fill_times(
    outline: List[OutlineEntry],
    subtitles: List[SubtitleEntry]
) -> List[OutlineEntry]:
    """验证和补充时间信息，确保覆盖整个视频"""
    if not subtitles:
        return outline
    
    video_end_time = subtitles[-1].get('end_time', 0)
    result: List[OutlineEntry] = []
    
    # 如果大纲为空或最后一个章节的时间点太早，记录警告
    if outline:
        last_time = max(item.get('start_time', 0) for item in outline)
        if last_time < video_end_time * 0.7:  # 如果最后一个章节不到视频70%的位置
            logger.warning(
                f"[OutlineValidator] 大纲可能未覆盖整个视频："
                f"最后一个章节时间 {last_time:.1f}s，视频结束时间 {video_end_time:.1f}s"
            )
    
    for item in outline:
        start_time = item.get('start_time', 0)
        
        # 如果时间不在字幕范围内，尝试根据描述匹配
        if start_time == 0 or start_time > video_end_time:
            # 根据标题或描述在字幕中查找匹配的时间点
            title = item.get('title', '')
            description = item.get('description', '')
            for subtitle in subtitles:
                subtitle_text = subtitle.get('text', '').lower()
                if title.lower() in subtitle_text or (description and description.lower() in subtitle_text):
                    start_time = subtitle['start_time']
                    break
        
        # 确保时间在有效范围内
        if start_time < 0:
            start_time = 0
        if start_time > video_end_time:
            # 如果超过视频结束时间，调整到合理位置（倒数5-10%的时间段）
            start_time = max(video_end_time * 0.9, video_end_time - 60)  # 至少提前1分钟或10%
        
        # 检查是否是最后一个章节，如果是，确保不是最后一秒
        is_last_chapter = (item == outline[-1]) if outline else False
        if is_last_chapter:
            # 最后一个章节应该在倒数5-15%的时间段，不能是最后一秒
            min_last_time = video_end_time * 0.85
            max_last_time = video_end_time * 0.95
            if start_time >= video_end_time * 0.98:  # 如果太接近结束（98%以后）
                # 调整到合理位置
                start_time = max(min_last_time, video_end_time * 0.9)
                logger.warning(
                    f"[OutlineValidator] 最后一个章节时间 {start_time:.1f}s 太接近结束，"
                    f"调整为 {start_time:.1f}s"
                )
        
        # 计算结束时间（下一个章节的开始时间，或视频结束时间）
        end_time = None
        if result:
            # 如果已有结果，当前章节的结束时间是下一个章节的开始时间
            pass  # 会在后面处理
        else:
            # 第一个章节，查找下一个章节的开始时间
            next_item = None
            for next_outline in outline:
                if next_outline.get('start_time', 0) > start_time:
                    next_item = next_outline
                    break
            if next_item:
                end_time = next_item.get('start_time', 0)
            elif subtitles:
                end_time = subtitles[-1].get('end_time', start_time + 60)
        
        # 确保 key_points 是数组格式
        key_points = item.get('key_points', [])
        if isinstance(key_points, str):
            # 如果是字符串，尝试解析为数组
            try:
                import json
                key_points = json.loads(key_points)
            except:
                # 如果解析失败，按逗号分割
                key_points = [p.strip() for p in key_points.split(',') if p.strip()]
        elif not isinstance(key_points, list):
            # 如果不是列表，转换为列表
            key_points = []
        
        result.append({
            'title': item.get('title', '未知章节'),
            'start_time': float(start_time),
            'description': item.get('description', ''),
            'key_points': key_points,  # 关键知识点/内容点（确保是数组）
            'end_time': float(end_time) if end_time else None
        })
    
    # 补充结束时间
    for i, item in enumerate(result):
        if not item.get('end_time'):
            if i < len(result) - 1:
                item['end_time'] = result[i + 1]['start_time']
            elif subtitles:
                item['end_time'] = subtitles[-1].get('end_time', item['start_time'] + 60)
            else:
                item['end_time'] = item['start_time'] + 60
    
    # 验证关键点数量（后处理检查）
    total_key_points = sum(len(item.get('key_points', [])) for item in result)
    video_minutes = video_end_time / 60
    
    if video_minutes <= 15 and total_key_points < 5:
        logger.warning(
            f"[OutlineValidator] 关键点数量不足：视频 {video_minutes:.1f} 分钟，"
            f"应该有至少5个关键点，实际只有 {total_key_points} 个。"
            f"这可能是由于本地模型（0.5B）理解能力有限导致的。"
        )
    
    return result


def merge_outlines(
    outlines: List[Dict[str, Any]],
    subtitles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """合并和去重大纲"""
    if not outlines:
        return []
    
    # 按时间排序
    outlines.sort(key=lambda x: x.get('start_time', 0))
    
    # 去重：如果两个章节时间太接近（<30秒），合并为一个
    merged = []
    for outline in outlines:
        if not merged:
            merged.append(outline)
        else:
            last_outline = merged[-1]
            last_time = last_outline.get('start_time', 0)
            current_time = outline.get('start_time', 0)
            
            if current_time - last_time < 30:
                # 时间太接近，合并描述和关键点
                logger.debug(f"[OutlineValidator] 合并章节: {last_time:.1f}s 和 {current_time:.1f}s")
                last_outline['description'] = f"{last_outline.get('description', '')} | {outline.get('description', '')}"
                
                # 确保 key_points 是数组格式
                last_key_points = last_outline.get('key_points', [])
                current_key_points = outline.get('key_points', [])
                
                # 如果 key_points 是字符串，转换为数组
                if isinstance(last_key_points, str):
                    last_key_points = [p.strip() for p in last_key_points.split(',') if p.strip()]
                if isinstance(current_key_points, str):
                    current_key_points = [p.strip() for p in current_key_points.split(',') if p.strip()]
                
                # 合并并去重
                if not isinstance(last_key_points, list):
                    last_key_points = []
                if not isinstance(current_key_points, list):
                    current_key_points = []
                
                last_outline['key_points'] = list(set(
                    last_key_points + current_key_points
                ))
            else:
                merged.append(outline)
    
    # 验证和补充时间信息
    merged = validate_and_fill_times(merged, subtitles)
    
    return merged

