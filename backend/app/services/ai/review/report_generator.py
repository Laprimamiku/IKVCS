"""
报告生成模块

职责：生成审核报告和最终结论
"""
from typing import Dict, Any, Optional


def generate_conclusion(
    frame_review: Dict[str, Any],
    subtitle_review: Optional[Dict[str, Any]],
    final_status: int,
    final_score: float
) -> str:
    """
    生成最终审核结论
    
    返回:
        str: 审核结论文本
    """
    frame_violation_ratio = frame_review.get("violation_ratio", 0)
    frame_suspicious_ratio = frame_review.get("suspicious_ratio", 0)
    frame_avg_score = frame_review.get("avg_score", 100)
    total_frames = frame_review.get("total_frames", 0)
    
    if final_status == 3:  # 拒绝
        if frame_violation_ratio > 10:
            return f"视频包含违规内容。共审核 {total_frames} 帧，其中 {frame_review.get('violation_count', 0)} 帧（{frame_violation_ratio}%）被标记为违规。建议拒绝发布。"
        else:
            return f"字幕内容违规。综合评分 {final_score} 分，建议拒绝发布。"
    elif final_status == 1:  # 审核中
        if frame_suspicious_ratio > 20:
            return f"视频包含疑似违规内容。共审核 {total_frames} 帧，其中 {frame_review.get('suspicious_count', 0)} 帧（{frame_suspicious_ratio}%）被标记为疑似违规。需要人工审核。"
        elif 5 <= frame_violation_ratio <= 10:
            return f"视频包含少量违规内容。共审核 {total_frames} 帧，其中 {frame_review.get('violation_count', 0)} 帧（{frame_violation_ratio}%）被标记为违规。需要人工审核。"
        else:
            return f"综合评分 {final_score} 分，低于安全阈值。需要人工审核。"
    else:  # 已发布
        return f"视频内容正常。共审核 {total_frames} 帧，平均评分 {frame_avg_score} 分，综合评分 {final_score} 分。可以发布。"

