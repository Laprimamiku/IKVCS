"""
帧审核模块

职责：审核视频帧，返回审核结果
"""
import asyncio
import logging
import os
from typing import Dict, Any

from app.core.config import settings
from app.services.video.frame_extractor import frame_extractor
from app.services.ai.image_review_service import image_review_service

logger = logging.getLogger(__name__)


async def review_frames(
    video_id: int,
    video_path: str
) -> Dict[str, Any]:
    """
    审核视频帧
    
    返回:
        Dict: 帧审核结果
            - total_frames: int - 总帧数
            - reviewed_frames: int - 已审核帧数
            - violation_count: int - 违规帧数
            - suspicious_count: int - 疑似帧数
            - min_score: int - 最低评分
            - has_violation: bool - 是否有明显违规
            - has_suspicious: bool - 是否有疑似内容
    """
    try:
        # 提取帧（使用均匀采样策略，根据视频时长动态调整）
        frames = frame_extractor.extract_frames(
            video_path=video_path,
            video_id=video_id,
            strategy="uniform",  # 使用均匀采样策略
            interval=None  # 根据视频时长自动调整
        )
        
        if not frames:
            logger.warning(f"未提取到帧: video_id={video_id}, video_path={video_path}")
            # 返回完整的默认结果，包含所有必要字段
            return {
                "total_frames": 0,
                "reviewed_frames": 0,
                "violation_count": 0,
                "suspicious_count": 0,
                "normal_count": 0,
                "violation_ratio": 0,
                "suspicious_ratio": 0,
                "avg_score": 100,
                "min_score": 100,
                "has_violation": False,
                "has_suspicious": False
            }
        
        # 限制并发审核数量，避免超出模型算力（GPU 资源管理）
        # 针对 4GB 显存（如 RTX 3050），默认并发数为 3，避免 GPU OOM
        max_concurrent = getattr(settings, 'FRAME_REVIEW_MAX_CONCURRENT', 3)
        logger.info(f"[Moondream] 开始审核 {len(frames)} 帧，并发数: {max_concurrent}（GPU 加速已启用，显存限制: 3GB）")
        
        # 使用信号量控制并发，实现流水线处理，避免 GPU 负载剧烈波动
        # 这样可以保持 GPU 负载相对平稳，减少从 0% 到 100% 的剧烈变化
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def review_frame_with_semaphore(frame_info, frame_num):
            """带信号量控制的帧审核，确保 GPU 负载平稳"""
            async with semaphore:
                frame_path = frame_info["frame_path"]
                # frame_path 已经是相对于 STORAGE_ROOT 的路径（如：frames/24/frame_0001.jpg）
                # 需要构建绝对路径，避免在 image_review_service 中重复拼接
                if os.path.isabs(frame_path):
                    # 已经是绝对路径，直接使用
                    full_path = frame_path
                else:
                    # 拼接 STORAGE_ROOT 和相对路径，然后规范化
                    # 注意：如果 STORAGE_ROOT 是相对路径（如 ./storage），需要先转换为绝对路径
                    storage_root = settings.STORAGE_ROOT
                    if not os.path.isabs(storage_root):
                        # 如果 STORAGE_ROOT 是相对路径，转换为绝对路径
                        storage_root = os.path.abspath(storage_root)
                    full_path = os.path.normpath(os.path.join(storage_root, frame_path))
                return await image_review_service.review_image(full_path)
        
        # 创建所有任务（使用信号量控制，实现流水线处理）
        # 这样可以保持 GPU 负载相对平稳，避免批处理导致的负载波动
        review_results = []
        frame_details = []  # 存储每帧的详细信息
        
        # 使用 asyncio.gather 并行处理所有帧，但通过信号量控制并发数
        # 这样 GPU 负载会更平稳，不会出现批处理间隔导致的 0% 负载
        tasks = [
            review_frame_with_semaphore(frame_info, idx + 1)
            for idx, frame_info in enumerate(frames)
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 记录每帧的详细评价
        for idx, (frame_info, result) in enumerate(zip(frames, batch_results)):
                frame_num = idx + 1
                frame_path = frame_info["frame_path"]
                if isinstance(result, Exception):
                    logger.warning(f"[Moondream] 帧 {frame_num}/{len(frames)} 审核异常: {frame_path} - {result}")
                    frame_details.append({
                        "frame_num": frame_num,
                        "frame_path": frame_path,
                        "status": "error",
                        "error": str(result)
                    })
                elif result:
                    score = result.get("score", 100)
                    is_violation = result.get("is_violation", False)
                    is_suspicious = result.get("is_suspicious", False)
                    violation_type = result.get("violation_type", "none")
                    description = result.get("description", "无描述")
                    
                    # 确定状态标签
                    if is_violation:
                        status_label = "❌ 违规"
                    elif is_suspicious:
                        status_label = "⚠️ 疑似"
                    else:
                        status_label = "✅ 正常"
                    
                    logger.info(
                        f"[Moondream] 帧 {frame_num}/{len(frames)} - {status_label} | "
                        f"评分: {score} | 类型: {violation_type} | "
                        f"描述: {description} | 路径: {frame_path}"
                    )
                    
                    frame_details.append({
                        "frame_num": frame_num,
                        "frame_path": frame_path,
                        "status": status_label,
                        "score": score,
                        "is_violation": is_violation,
                        "is_suspicious": is_suspicious,
                        "violation_type": violation_type,
                        "description": description
                    })
                else:
                    logger.warning(f"[Moondream] 帧 {frame_num}/{len(frames)} 审核返回空结果: {frame_path}")
                    frame_details.append({
                        "frame_num": frame_num,
                        "frame_path": frame_path,
                        "status": "empty",
                        "error": "审核返回空结果"
                    })
        
        review_results = batch_results
        logger.info(f"已审核 {len(frames)}/{len(frames)} 帧（流水线处理完成）")
        
        # 统计结果
        violation_count = 0
        suspicious_count = 0
        normal_count = 0
        scores = []
        reviewed_count = 0
        
        for result in review_results:
            if isinstance(result, Exception):
                continue
            
            if result:
                reviewed_count += 1
                score = result.get("score", 100)
                scores.append(score)
                
                if result.get("is_violation", False):
                    violation_count += 1
                elif result.get("is_suspicious", False):
                    suspicious_count += 1
                else:
                    normal_count += 1
        
        # 计算统计信息
        total_frames = len(frames)
        violation_ratio = violation_count / total_frames if total_frames > 0 else 0
        suspicious_ratio = suspicious_count / total_frames if total_frames > 0 else 0
        avg_score = sum(scores) / len(scores) if scores else 100
        min_score = min(scores) if scores else 100
        max_score = max(scores) if scores else 100
        
        # 输出审核总结
        logger.info("=" * 80)
        logger.info(f"[Moondream] 视频帧审核总结 (video_id={video_id})")
        logger.info("-" * 80)
        logger.info(f"总帧数: {total_frames} | 已审核: {reviewed_count} | 审核失败: {total_frames - reviewed_count}")
        logger.info(f"违规帧: {violation_count} ({round(violation_ratio * 100, 2)}%) | "
                   f"疑似帧: {suspicious_count} ({round(suspicious_ratio * 100, 2)}%) | "
                   f"正常帧: {normal_count} ({round((normal_count / total_frames * 100) if total_frames > 0 else 0, 2)}%)")
        logger.info(f"评分统计: 平均 {round(avg_score, 1)} 分 | 最低 {round(min_score, 1)} 分 | 最高 {round(max_score, 1)} 分")
        logger.info(f"审核结论: {'❌ 存在违规内容' if violation_count > 0 else '⚠️ 存在疑似内容' if suspicious_count > 0 else '✅ 内容正常'}")
        logger.info("=" * 80)
        
        return {
            "total_frames": total_frames,
            "reviewed_frames": reviewed_count,
            "violation_count": violation_count,
            "suspicious_count": suspicious_count,
            "normal_count": normal_count,
            "violation_ratio": round(violation_ratio * 100, 2),  # 违规帧比例（百分比）
            "suspicious_ratio": round(suspicious_ratio * 100, 2),  # 疑似帧比例（百分比）
            "avg_score": round(avg_score, 1),  # 平均评分
            "min_score": round(min_score, 1),  # 最低评分
            "has_violation": violation_count > 0,
            "has_suspicious": suspicious_count > 0
        }
        
    except Exception as e:
        logger.error(f"帧审核失败: {e}", exc_info=True)
        return {
            "total_frames": 0,
            "reviewed_frames": 0,
            "violation_count": 0,
            "suspicious_count": 0,
            "min_score": 100,
            "has_violation": False,
            "has_suspicious": False,
            "error": str(e)
        }

