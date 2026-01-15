"""
状态判断模块

职责：根据帧审核和字幕审核结果，决定视频最终状态
"""
from typing import Dict, Any, Optional
from app.core.video_constants import VideoStatus


def determine_status(
    frame_review: Dict[str, Any],
    subtitle_review: Optional[Dict[str, Any]]
) -> tuple[int, int]:
    """
    根据审核结果决定视频状态（使用违规比例和加权评分）
    
    返回:
        tuple: (status, score)
            - status: VideoStatus 枚举值
            - score: 综合评分（0-100）
    """
    # 帧审核结果
    frame_violation_ratio = frame_review.get("violation_ratio", 0)  # 违规帧比例（百分比）
    frame_suspicious_ratio = frame_review.get("suspicious_ratio", 0)  # 疑似帧比例（百分比）
    frame_avg_score = frame_review.get("avg_score", 100)  # 平均评分
    
    # 字幕审核结果
    subtitle_has_violation = False
    subtitle_has_suspicious = False
    subtitle_score = 100
    
    if subtitle_review:
        subtitle_has_violation = subtitle_review.get("is_violation", False)
        subtitle_has_suspicious = subtitle_review.get("is_suspicious", False)
        subtitle_score = subtitle_review.get("score", 100)
    
    # 综合评分：帧审核和字幕审核的加权平均（帧审核权重70%，字幕审核权重30%）
    final_score = round(frame_avg_score * 0.7 + subtitle_score * 0.3, 1)
    
    # 判断状态（优先使用违规比例）
    # 1. 如果违规帧比例 > 10%，直接拒绝
    if frame_violation_ratio > 10 or subtitle_has_violation:
        return (VideoStatus.REJECTED, final_score)
    
    # 2. 如果违规帧比例 5-10%，或疑似帧比例 > 20%，需要人工审核
    if (5 <= frame_violation_ratio <= 10) or frame_suspicious_ratio > 20 or subtitle_has_suspicious:
        return (VideoStatus.REVIEWING, final_score)
    
    # 3. 如果综合评分过低（<60），需要人工审核
    if final_score < 60:
        return (VideoStatus.REVIEWING, final_score)
    
    # 4. 其他情况，正常发布
    return (VideoStatus.PUBLISHED, final_score)

