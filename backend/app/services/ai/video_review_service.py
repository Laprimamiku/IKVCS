"""
视频综合审核服务

职责：
1. 整合帧审核和字幕审核
2. 根据审核结果决定视频状态
3. 更新视频状态到数据库

审核逻辑：
- 明显违规（暴力、血腥等）-> status=3（拒绝）
- 疑似内容 -> status=1（审核中）
- 没有问题 -> status=2（已发布）
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.video import Video
from app.services.video.frame_extractor import frame_extractor
from app.services.ai.image_review_service import image_review_service
from app.services.ai.subtitle_review_service import subtitle_review_service
from app.services.video.subtitle_parser import SubtitleParser

logger = logging.getLogger(__name__)


class VideoReviewService:
    """视频综合审核服务"""
    
    def __init__(self):
        self.frame_extractor = frame_extractor
        self.image_reviewer = image_review_service
        self.subtitle_reviewer = subtitle_review_service
        self.subtitle_parser = SubtitleParser()
    
    async def review_video(
        self,
        video_id: int,
        video_path: str,
        subtitle_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        审核视频
        
        参数:
            video_id: 视频ID
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径（可选）
        
        返回:
            Dict: 审核结果
                - status: int - 最终状态（1=审核中, 2=已发布, 3=拒绝）
                - frame_review: Dict - 帧审核结果
                - subtitle_review: Dict - 字幕审核结果
                - final_score: int - 综合评分
        """
        logger.info(f"开始 AI 初审: video_id={video_id}（字幕+抽帧并行处理，GPU 加速已启用）")
        
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"视频不存在: video_id={video_id}")
                return {"status": 3, "error": "视频不存在"}
            
            # 并行执行帧审核（Moondream）和字幕审核（qwen2.5:0.5b-instruct）
            # 充分利用 GPU 资源，但通过并发控制避免过度占用
            logger.info(f"开始并行审核: 帧审核（Moondream）+ 字幕审核（qwen2.5:0.5b-instruct）")
            frame_review_task = self._review_frames(video_id, video_path)
            subtitle_review_task = self._review_subtitle(subtitle_path) if subtitle_path else None
            
            # 等待审核完成
            frame_review = await frame_review_task
            subtitle_review = await subtitle_review_task if subtitle_review_task else None
            
            # 输出字幕审核总结
            if subtitle_review:
                logger.info("=" * 80)
                logger.info(f"[SubtitleReview] 字幕审核总结 (video_id={video_id})")
                logger.info("-" * 80)
                logger.info(f"评分: {subtitle_review.get('score', 'N/A')} 分")
                logger.info(f"状态: {'❌ 违规' if subtitle_review.get('is_violation') else '⚠️ 疑似' if subtitle_review.get('is_suspicious') else '✅ 正常'}")
                logger.info(f"违规类型: {subtitle_review.get('violation_type', 'none')}")
                logger.info(f"描述: {subtitle_review.get('description', '无描述')}")
                logger.info("=" * 80)
            else:
                logger.info("[SubtitleReview] 未进行字幕审核（无字幕文件或审核失败）")
            
            # 综合判断
            final_status, final_score = self._determine_status(frame_review, subtitle_review)
            
            # 构建审核报告（包含统计信息和最终结论）
            frame_violation_ratio = frame_review.get("violation_ratio", 0)
            frame_suspicious_ratio = frame_review.get("suspicious_ratio", 0)
            
            # 生成最终结论
            conclusion = self._generate_conclusion(
                frame_review, subtitle_review, final_status, final_score
            )
            
            review_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "video_id": video_id,
                "final_score": final_score,
                "final_status": final_status,
                "conclusion": conclusion,  # 最终结论
                "frame_review": {
                    "total_frames": frame_review.get("total_frames", 0),
                    "reviewed_frames": frame_review.get("reviewed_frames", 0),
                    "violation_count": frame_review.get("violation_count", 0),
                    "suspicious_count": frame_review.get("suspicious_count", 0),
                    "normal_count": frame_review.get("normal_count", 0),
                    "violation_ratio": frame_violation_ratio,
                    "suspicious_ratio": frame_suspicious_ratio,
                    "avg_score": frame_review.get("avg_score", 100),
                    "min_score": frame_review.get("min_score", 100),
                    "has_violation": frame_review.get("has_violation", False),
                    "has_suspicious": frame_review.get("has_suspicious", False),
                },
                "subtitle_review": subtitle_review if subtitle_review else None,
            }
            
            # 更新视频状态和审核信息
            video.status = final_status
            video.review_score = final_score
            video.review_status = final_status  # 1=审核中, 2=通过, 3=拒绝
            video.review_report = json.dumps(review_report, ensure_ascii=False)
            db.commit()
            
            logger.info(f"视频审核完成: video_id={video_id}, status={final_status}, score={final_score}")
            
            return {
                "status": final_status,
                "frame_review": frame_review,
                "subtitle_review": subtitle_review,
                "final_score": final_score,
                "review_report": review_report
            }
            
        except Exception as e:
            logger.error(f"审核视频失败: {e}", exc_info=True)
            db.rollback()
            # 审核失败，设置为审核中，等待人工处理
            try:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.status = 1  # 审核中
                    db.commit()
            except:
                pass
            return {"status": 1, "error": str(e)}
        finally:
            db.close()
    
    async def review_frames_only(
        self,
        video_id: int,
        video_path: str
    ) -> Dict[str, Any]:
        """
        仅审核视频帧（不审核字幕）
        
        参数:
            video_id: 视频ID
            video_path: 视频文件路径
        
        返回:
            Dict: 帧审核结果
        """
        logger.info(f"开始仅审核视频帧: video_id={video_id}")
        
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"视频不存在: video_id={video_id}")
                return {"error": "视频不存在"}
            
            # 仅审核帧
            frame_review = await self._review_frames(video_id, video_path)
            
            # 更新审核报告（保留原有的字幕审核结果）
            review_report = {}
            if video.review_report:
                try:
                    review_report = json.loads(video.review_report) if isinstance(video.review_report, str) else video.review_report
                except:
                    review_report = {}
            
            # 更新帧审核结果
            review_report["frame_review"] = {
                "total_frames": frame_review.get("total_frames", 0),
                "reviewed_frames": frame_review.get("reviewed_frames", 0),
                "violation_count": frame_review.get("violation_count", 0),
                "suspicious_count": frame_review.get("suspicious_count", 0),
                "normal_count": frame_review.get("normal_count", 0),
                "violation_ratio": frame_review.get("violation_ratio", 0),
                "suspicious_ratio": frame_review.get("suspicious_ratio", 0),
                "avg_score": frame_review.get("avg_score", 100),
                "min_score": frame_review.get("min_score", 100),
                "has_violation": frame_review.get("has_violation", False),
                "has_suspicious": frame_review.get("has_suspicious", False),
            }
            review_report["timestamp"] = datetime.utcnow().isoformat()
            review_report["video_id"] = video_id
            
            # 如果有字幕审核结果，重新计算综合评分
            subtitle_review = review_report.get("subtitle_review")
            if subtitle_review:
                final_status, final_score = self._determine_status(frame_review, subtitle_review)
                review_report["final_score"] = final_score
                review_report["final_status"] = final_status
                review_report["conclusion"] = self._generate_conclusion(frame_review, subtitle_review, final_status, final_score)
            else:
                # 仅帧审核，使用帧审核结果
                review_report["final_score"] = frame_review.get("avg_score", 100)
                review_report["final_status"] = 1  # 审核中
                review_report["conclusion"] = f"仅完成帧审核。共审核 {frame_review.get('total_frames', 0)} 帧，平均评分 {frame_review.get('avg_score', 100)} 分。"
            
            video.review_report = json.dumps(review_report, ensure_ascii=False)
            db.commit()
            
            logger.info(f"帧审核完成: video_id={video_id}")
            return frame_review
            
        except Exception as e:
            logger.error(f"帧审核失败: {e}", exc_info=True)
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()
    
    async def review_subtitle_only(
        self,
        video_id: int,
        subtitle_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        仅审核字幕（不审核帧）
        
        参数:
            video_id: 视频ID
            subtitle_path: 字幕文件路径（可选，如果不提供则从视频记录中获取）
        
        返回:
            Dict: 字幕审核结果
        """
        logger.info(f"开始仅审核字幕: video_id={video_id}")
        
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"视频不存在: video_id={video_id}")
                return {"error": "视频不存在"}
            
            # 如果没有提供字幕路径，从视频记录中获取
            if not subtitle_path:
                subtitle_path = video.subtitle_url
            
            # 仅审核字幕
            subtitle_review = await self._review_subtitle(subtitle_path)
            
            # 更新审核报告（保留原有的帧审核结果）
            review_report = {}
            if video.review_report:
                try:
                    review_report = json.loads(video.review_report) if isinstance(video.review_report, str) else video.review_report
                except:
                    review_report = {}
            
            # 更新字幕审核结果
            if subtitle_review:
                review_report["subtitle_review"] = subtitle_review
            else:
                review_report["subtitle_review"] = None
            
            review_report["timestamp"] = datetime.utcnow().isoformat()
            review_report["video_id"] = video_id
            
            # 如果有帧审核结果，重新计算综合评分
            frame_review = review_report.get("frame_review")
            if frame_review:
                final_status, final_score = self._determine_status(frame_review, subtitle_review)
                review_report["final_score"] = final_score
                review_report["final_status"] = final_status
                review_report["conclusion"] = self._generate_conclusion(frame_review, subtitle_review, final_status, final_score)
            else:
                # 仅字幕审核，使用字幕审核结果
                if subtitle_review:
                    review_report["final_score"] = subtitle_review.get("score", 100)
                    review_report["final_status"] = 1  # 审核中
                    review_report["conclusion"] = f"仅完成字幕审核。评分 {subtitle_review.get('score', 100)} 分。"
                else:
                    review_report["final_score"] = 100
                    review_report["final_status"] = 1
                    review_report["conclusion"] = "字幕审核失败或字幕文件不存在。"
            
            video.review_report = json.dumps(review_report, ensure_ascii=False)
            db.commit()
            
            logger.info(f"字幕审核完成: video_id={video_id}")
            return subtitle_review
            
        except Exception as e:
            logger.error(f"字幕审核失败: {e}", exc_info=True)
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()
    
    async def _review_frames(
        self,
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
            frames = self.frame_extractor.extract_frames(
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
            import os
            from app.core.config import settings
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
                    return await self.image_reviewer.review_image(full_path)
            
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
    
    async def _review_subtitle(
        self,
        subtitle_path: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        审核字幕内容（使用 qwen2.5:0.5b-instruct）
        
        参数:
            subtitle_path: 字幕文件路径（支持 SRT/VTT/JSON/ASS 格式）
        
        返回:
            Dict: 字幕审核结果（格式同 SubtitleReviewService.review_subtitle）
        """
        if not subtitle_path:
            logger.info("[SubtitleReview] 未提供字幕文件路径，跳过字幕审核")
            return None
        
        try:
            # 解析字幕文件，提取文本
            import os
            from app.core.config import settings
            
            # 处理字幕路径
            # 字幕文件可能已经是绝对路径，或者相对路径
            if os.path.isabs(subtitle_path):
                # 已经是绝对路径，直接使用
                full_path = subtitle_path
            elif subtitle_path.startswith("/"):
                # 相对路径，如 /uploads/subtitles/xxx.json
                full_path = os.path.join(settings.STORAGE_ROOT, subtitle_path.lstrip("/"))
            else:
                # 可能是相对路径，如 storage\uploads\subtitles\xxx.json
                # 检查是否已经包含 storage 前缀
                if subtitle_path.startswith("storage") or subtitle_path.startswith("./storage"):
                    # 已经包含 storage 前缀，直接拼接 STORAGE_ROOT
                    # 去掉 storage 前缀，然后拼接
                    if subtitle_path.startswith("./storage"):
                        relative_path = subtitle_path.replace("./storage", "").lstrip("/\\")
                    else:
                        relative_path = subtitle_path.replace("storage", "").lstrip("/\\")
                    full_path = os.path.normpath(os.path.join(settings.STORAGE_ROOT, relative_path))
                else:
                    # 直接文件名，从 subtitles 目录查找
                    full_path = os.path.join(settings.UPLOAD_SUBTITLE_DIR, subtitle_path)
            
            # 规范化路径（处理 Windows 路径分隔符）
            full_path = os.path.normpath(full_path)
            
            if not os.path.exists(full_path):
                logger.warning(f"[SubtitleReview] 字幕文件不存在: {full_path} (原始路径: {subtitle_path})")
                return None
            
            # 获取文件扩展名，用于日志
            file_ext = os.path.splitext(full_path)[1].lower()
            logger.info(f"[SubtitleReview] 开始审核字幕文件: {full_path} (格式: {file_ext})")
            
            # 解析字幕（支持 JSON 格式，qwen2.5:0.5b-instruct 可以直接读取 JSON 内容）
            subtitles = self.subtitle_parser.parse_subtitle_file(full_path)
            if not subtitles:
                logger.warning(f"[SubtitleReview] 字幕文件解析失败或为空: {full_path}")
                return None
            
            logger.info(f"[SubtitleReview] 成功解析字幕文件，共 {len(subtitles)} 条字幕")
            
            # 合并所有字幕文本（qwen2.5:0.5b-instruct 可以直接处理 JSON 格式的文本）
            subtitle_text = "\n".join([sub.get('text', '') if isinstance(sub, dict) else sub.text for sub in subtitles])
            
            if not subtitle_text.strip():
                logger.warning(f"[SubtitleReview] 字幕文本为空: {full_path}")
                return None
            
            # 记录字幕文本长度（用于调试）
            text_length = len(subtitle_text)
            logger.info(f"[SubtitleReview] 字幕文本长度: {text_length} 字符，开始调用 qwen2.5:0.5b-instruct 审核")
            
            # 审核字幕
            result = await self.subtitle_reviewer.review_subtitle(subtitle_text)
            
            if result:
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
                    f"[SubtitleReview] 字幕审核完成 - {status_label} | "
                    f"评分: {score} | 类型: {violation_type} | "
                    f"描述: {description}"
                )
            else:
                logger.warning(f"[SubtitleReview] 字幕审核返回空结果: {full_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"[SubtitleReview] 字幕审核失败: {e}", exc_info=True)
            return None
    
    def _determine_status(
        self,
        frame_review: Dict[str, Any],
        subtitle_review: Optional[Dict[str, Any]]
    ) -> tuple[int, int]:
        """
        根据审核结果决定视频状态（使用违规比例和加权评分）
        
        返回:
            tuple: (status, score)
                - status: 1=审核中, 2=已发布, 3=拒绝
                - score: 综合评分（0-100）
        """
        # 帧审核结果
        frame_violation_ratio = frame_review.get("violation_ratio", 0)  # 违规帧比例（百分比）
        frame_suspicious_ratio = frame_review.get("suspicious_ratio", 0)  # 疑似帧比例（百分比）
        frame_avg_score = frame_review.get("avg_score", 100)  # 平均评分
        frame_has_violation = frame_review.get("has_violation", False)
        
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
            return (3, final_score)  # 拒绝
        
        # 2. 如果违规帧比例 5-10%，或疑似帧比例 > 20%，需要人工审核
        if (5 <= frame_violation_ratio <= 10) or frame_suspicious_ratio > 20 or subtitle_has_suspicious:
            return (1, final_score)  # 审核中
        
        # 3. 如果综合评分过低（<60），需要人工审核
        if final_score < 60:
            return (1, final_score)  # 审核中
        
        # 4. 其他情况，正常发布
        return (2, final_score)  # 已发布
    
    def _generate_conclusion(
        self,
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


# 全局实例
video_review_service = VideoReviewService()

