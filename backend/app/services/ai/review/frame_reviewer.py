"""
帧审核模块

职责：审核视频帧，返回审核结果
支持云端和本地模型双模式
"""
import asyncio
import logging
import os
from typing import Dict, Any, Optional

from app.core.config import settings
from app.services.video.frame_extractor import frame_extractor
from app.services.ai.image_review_service import image_review_service

logger = logging.getLogger(__name__)


async def review_frames(
    video_id: int,
    video_path: str,
    use_cloud_override: Optional[bool] = None,
    max_frames: Optional[int] = None,
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
            interval=None,  # 根据视频时长自动调整
            max_frames=max_frames,
        )
        
        if not frames:
            logger.warning(f"未提取到帧: video_id={video_id}, video_path={video_path}")
            # 无帧/抽帧失败属于不确定状态：为避免误放行，按“疑似/需人工复核”降级
            return {
                "total_frames": 0,
                "reviewed_frames": 0,
                "violation_count": 0,
                "suspicious_count": 1,
                "normal_count": 0,
                "violation_ratio": 0,
                "suspicious_ratio": 100,
                "avg_score": 60,
                "min_score": 60,
                "has_violation": False,
                "has_suspicious": True,
                "error": "未提取到帧，无法完成帧审核"
            }
        
        # 视觉模型名称（展示用）
        vision_model_name = settings.LLM_VISION_MODEL or settings.LLM_MODEL or "unknown"

        # 按需覆写是否使用云端模型（预算控制）
        vision_mode = getattr(settings, "VISION_MODE", "hybrid").lower()
        if vision_mode == "off":
            logger.info("[Vision] VISION_MODE=off，跳过帧审核")
            return {
                "total_frames": len(frames),
                "reviewed_frames": 0,
                "violation_count": 0,
                "suspicious_count": 0,
                "normal_count": 0,
                "violation_ratio": 0,
                "suspicious_ratio": 0,
                "avg_score": 100,
                "min_score": 100,
                "has_violation": False,
                "has_suspicious": False,
            }
        has_cloud_key = bool(getattr(settings, "LLM_VISION_API_KEY", "") or settings.LLM_API_KEY)
        if vision_mode == "cloud_only" and not has_cloud_key:
            logger.error("[CloudVision] VISION_MODE=cloud_only 但未配置云端密钥，帧审核将标记为需人工复核")
            total_frames = len(frames)
            return {
                "total_frames": total_frames,
                "reviewed_frames": 0,
                "violation_count": 0,
                "suspicious_count": total_frames,
                "normal_count": 0,
                "violation_ratio": 0,
                "suspicious_ratio": 100 if total_frames > 0 else 0,
                "avg_score": 60,
                "min_score": 60,
                "has_violation": False,
                "has_suspicious": True,
            }
        base_use_cloud = vision_mode in ("cloud_only", "hybrid") and has_cloud_key
        use_cloud = base_use_cloud if use_cloud_override is None else use_cloud_override
        cloud_limit = getattr(settings, "CLOUD_MAX_CALLS_PER_VIDEO", 0) or 0
        if use_cloud and cloud_limit > 0 and len(frames) > cloud_limit:
            logger.warning(
                f"[CloudVision] 超出每视频云端上限({cloud_limit})，本次帧审核降级为本地/跳过云端。video_id={video_id}, frames={len(frames)}"
            )
            use_cloud = False

        # 云端模型并发控制（网络请求优化）
        if use_cloud:
            max_concurrent = getattr(settings, 'CLOUD_FRAME_REVIEW_MAX_CONCURRENT', 5)
            logger.info(f"[CloudVision] 开始审核 {len(frames)} 帧，并发数: {max_concurrent}（云端模型: {vision_model_name}）")
        else:
            # 本地模型GPU资源管理（已注释，保留配置）
            # 限制并发审核数量，避免超出模型算力（GPU 资源管理）
            # 针对 4GB 显存（如 RTX 3050），默认并发数为 3，避免 GPU OOM
            max_concurrent = getattr(settings, 'FRAME_REVIEW_MAX_CONCURRENT', 3)
            # logger.info(f"[LocalVision] 开始审核 {len(frames)} 帧，并发数: {max_concurrent}（本地视觉模型）")
            logger.info(f"[LocalModel] 开始审核 {len(frames)} 帧，并发数: {max_concurrent}（本地模型: {vision_model_name}）")
        
        # 准备帧路径列表
        frame_paths = []
        for frame_info in frames:
            frame_path = frame_info["frame_path"]
            if os.path.isabs(frame_path):
                full_path = frame_path
            else:
                storage_root = settings.STORAGE_ROOT
                if not os.path.isabs(storage_root):
                    storage_root = os.path.abspath(storage_root)
                full_path = os.path.normpath(os.path.join(storage_root, frame_path))
            frame_paths.append(full_path)
        
        # 云端模型：使用批量审核（图片拼接）
        # 本地模型：使用单张审核（保持原有逻辑）
        if use_cloud:
            # 检查是否启用批量审核
            use_batch = getattr(settings, 'FRAME_BATCH_REVIEW_ENABLED', True)
            if use_batch:
                logger.info(f"[FrameReview] 🚀 使用批量审核模式（图片拼接）: {len(frame_paths)}帧")
                batch_results = await image_review_service.review_images_batch(frame_paths)
                logger.info(f"[FrameReview] ✅ 批量审核完成: 收到{len(batch_results)}个结果")
            else:
                # 回退到单张审核（使用信号量控制并发）
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def review_frame_with_semaphore(full_path, frame_num):
                    """带信号量控制的帧审核"""
                    async with semaphore:
                        return await image_review_service.review_image(full_path)
                
                tasks = [
                    review_frame_with_semaphore(path, idx + 1)
                    for idx, path in enumerate(frame_paths)
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # 本地模型：使用信号量控制并发
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def review_frame_with_semaphore(full_path, frame_num):
                """带信号量控制的帧审核"""
                async with semaphore:
                    return await image_review_service.review_image(full_path)
            
            tasks = [
                review_frame_with_semaphore(path, idx + 1)
                for idx, path in enumerate(frame_paths)
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        review_results = []
        frame_details = []  # 存储每帧的详细信息
        
        # 记录每帧的详细评价
        model_name = f"CloudVision({vision_model_name})" if use_cloud else f"LocalModel({vision_model_name})"
        for idx, (frame_info, result) in enumerate(zip(frames, batch_results)):
                frame_num = idx + 1
                frame_path = frame_info["frame_path"]
                if isinstance(result, Exception):
                    logger.warning(f"[{model_name}] 帧 {frame_num}/{len(frames)} 审核异常: {frame_path} - {result}")
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
                        status_label = "违规"
                    elif is_suspicious:
                        status_label = "疑似"
                    else:
                        status_label = "正常"
                    
                    logger.info(
                        f"[{model_name}] 帧 {frame_num}/{len(frames)} - {status_label} | "
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
                    logger.warning(f"[{model_name}] 帧 {frame_num}/{len(frames)} 审核返回空结果: {frame_path}")
                    frame_details.append({
                        "frame_num": frame_num,
                        "frame_path": frame_path,
                        "status": "empty",
                        "error": "审核返回空结果"
                    })
        
        review_results = batch_results
        logger.info(f"已审核 {len(frames)}/{len(frames)} 帧（{'云端模型' if use_cloud else '本地模型'}处理完成）")
        
        # 统计结果
        violation_count = 0
        suspicious_count = 0
        normal_count = 0
        scores = []
        reviewed_count = 0
        failure_count = 0
        
        for result in review_results:
            if isinstance(result, Exception):
                failure_count += 1
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
            else:
                failure_count += 1
        
        # 空结果/失败按“疑似”计入（避免因配置/网络问题误放行）
        suspicious_count += failure_count

        # 计算统计信息
        total_frames = len(frames)
        violation_ratio = violation_count / total_frames if total_frames > 0 else 0
        suspicious_ratio = suspicious_count / total_frames if total_frames > 0 else 0
        avg_score = sum(scores) / len(scores) if scores else 60
        min_score = min(scores) if scores else 60
        max_score = max(scores) if scores else 60
        
        # 输出审核总结
        logger.info("=" * 80)
        logger.info(f"[{model_name}] 视频帧审核总结 (video_id={video_id})")
        logger.info("-" * 80)
        logger.info(f"总帧数: {total_frames} | 已审核: {reviewed_count} | 审核失败: {total_frames - reviewed_count}")
        logger.info(f"违规帧: {violation_count} ({round(violation_ratio * 100, 2)}%) | "
                   f"疑似帧: {suspicious_count} ({round(suspicious_ratio * 100, 2)}%) | "
                   f"正常帧: {normal_count} ({round((normal_count / total_frames * 100) if total_frames > 0 else 0, 2)}%)")
        logger.info(f"评分统计: 平均 {round(avg_score, 1)} 分 | 最低 {round(min_score, 1)} 分 | 最高 {round(max_score, 1)} 分")
        logger.info(f"审核结论: {'存在违规内容' if violation_count > 0 else '存在疑似内容' if suspicious_count > 0 else '内容正常'}")
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
        # 审核异常属于不确定状态：为避免误放行，按“疑似/需人工复核”降级
        return {
            "total_frames": 0,
            "reviewed_frames": 0,
            "violation_count": 0,
            "suspicious_count": 1,
            "normal_count": 0,
            "violation_ratio": 0,
            "suspicious_ratio": 100,
            "avg_score": 60,
            "min_score": 60,
            "has_violation": False,
            "has_suspicious": True,
            "error": str(e)
        }

