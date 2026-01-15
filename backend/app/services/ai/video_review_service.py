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
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.model_registry import model_registry
from app.core.video_constants import VideoStatus, ReviewStatus
from app.models.video import Video
from app.utils.json_utils import parse_review_report, safe_json_dumps, dump_json_field
from app.services.video.frame_extractor import frame_extractor
from app.services.ai.image_review_service import image_review_service
from app.services.ai.subtitle_review_service import subtitle_review_service
from app.services.video.subtitle_parser import SubtitleParser
from app.services.ai.review.frame_reviewer import review_frames as review_frames_module
from app.services.ai.review.status_determiner import determine_status
from app.services.ai.review.report_generator import generate_conclusion
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now

logger = logging.getLogger(__name__)


class VideoReviewService:
    """视频综合审核服务"""
    
    def __init__(self):
        self.frame_extractor = frame_extractor
        self.image_reviewer = image_review_service
        self.subtitle_reviewer = subtitle_review_service
        self.subtitle_parser = SubtitleParser()
        
        # 使用新的模式配置（单一事实来源：LLM_MODE / VISION_MODE）
        self.llm_mode = getattr(settings, "LLM_MODE", "hybrid").lower()
        self.vision_mode = getattr(settings, "VISION_MODE", "hybrid").lower()

        self.use_cloud_text = self.llm_mode in ("cloud_only", "hybrid") and bool(settings.LLM_API_KEY)
        self.use_local_text = self.llm_mode in ("local_only", "hybrid")

        self.use_cloud_vision = self.vision_mode in ("cloud_only", "hybrid") and bool(
            getattr(settings, "LLM_VISION_API_KEY", "") or settings.LLM_API_KEY
        )
        self.use_local_vision = self.vision_mode in ("local_only", "hybrid") and not self.use_cloud_vision
        
        # 两阶段审核配置
        self.two_stage_enabled = bool(getattr(settings, "TWO_STAGE_REVIEW_ENABLED", True))
        self.stage1_max_frames = int(getattr(settings, "TWO_STAGE_STAGE1_MAX_FRAMES", 8) or 8)
        self.stage2_trigger_min_score = int(getattr(settings, "TWO_STAGE_STAGE2_TRIGGER_MIN_SCORE", 85) or 85)
        
        # 成本控制配置
        self.max_frames_per_video = getattr(settings, 'MAX_FRAMES_PER_VIDEO', 50)
        self.max_cloud_calls_per_video = getattr(settings, 'CLOUD_MAX_CALLS_PER_VIDEO', 0)
        self.max_cloud_chars_per_video = getattr(settings, 'CLOUD_MAX_INPUT_CHARS_PER_VIDEO', 8000)

    def _get_model_info(self) -> Dict[str, Any]:
        """统一生成模型信息（避免硬编码模型名，便于前端展示/日志排查）"""
        vision_model_name = getattr(settings, "LLM_VISION_MODEL", "") or settings.LLM_MODEL or "unknown"
        cloud_text_model = settings.LLM_MODEL or "unknown"
        local_text_model = settings.LOCAL_LLM_MODEL or "unknown"

        if self.llm_mode == "off":
            text_display = "文本模型(off)"
        elif self.llm_mode == "cloud_only":
            text_display = f"云端文本模型({cloud_text_model})"
        elif self.llm_mode == "local_only":
            text_display = f"本地文本模型({local_text_model})"
        else:
            parts: list[str] = []
            if model_registry.is_available("local_text"):
                parts.append(f"本地({local_text_model})")
            if model_registry.is_available("cloud_text"):
                parts.append(f"云端({cloud_text_model})")
            text_display = f"混合文本模型({' -> '.join(parts)})" if parts else "混合文本模型(未配置)"

        if self.vision_mode == "off":
            vision_display = "视觉模型(off)"
        else:
            vision_display = (
                f"云端视觉模型({vision_model_name})" if self.use_cloud_vision else f"本地视觉模型({vision_model_name})"
            )

        return {
            "llm_mode": self.llm_mode,
            "vision_mode": self.vision_mode,
            "cloud_text_model": cloud_text_model,
            "local_text_model": local_text_model,
            "vision_model": vision_model_name,
            "text_model_display": text_display,
            "vision_model_display": vision_display,
            "use_cloud_llm": self.use_cloud_text,
            "use_local_llm": self.use_local_text,
            "use_cloud_vision": self.use_cloud_vision,
        }

    def _subtitle_rule_screen(self, subtitle_path: Optional[str]) -> Optional[Dict[str, Any]]:
        """Stage 1：字幕规则初筛（低成本）"""
        if not subtitle_path:
            return None

        try:
            entries = self.subtitle_parser.parse_subtitle_file(subtitle_path)
        except Exception as e:
            return {
                "method": "rule",
                "is_suspicious": True,
                "risk_score": 60,
                "hits": [],
                "description": f"字幕解析失败，建议进入精审: {e}",
            }

        text = " ".join([str(x.get("text", "")).strip() for x in entries if x.get("text")]).strip()
        if not text:
            return {"method": "rule", "is_suspicious": False, "risk_score": 0, "hits": [], "description": "字幕为空"}

        sample = text[:8000]
        lowered = sample.lower()

        keyword_groups = {
            "violence": ["杀", "砍", "枪", "刀", "爆炸", "血", "打死", "开枪", "自杀"],
            "porn": ["裸体", "裸露", "成人视频", "性行为", "约炮"],
            "political": ["台独", "法轮功", "恐怖主义"],
            "other": ["毒品", "吸毒", "贩毒"],
        }

        hits: list[dict] = []
        for group, keywords in keyword_groups.items():
            for kw in keywords:
                if kw.lower() in lowered:
                    hits.append({"group": group, "keyword": kw})

        if not hits:
            return {"method": "rule", "is_suspicious": False, "risk_score": 0, "hits": [], "description": "规则未命中"}

        # 命中即进入精审（默认给出中高风险分）
        return {
            "method": "rule",
            "is_suspicious": True,
            "risk_score": 70,
            "hits": hits[:20],
            "description": f"规则命中 {len(hits)} 项，进入精审",
        }
    
    async def review_video(
        self,
        video_id: int,
        video_path: str,
        subtitle_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """审核视频（两阶段：低成本初筛 + 精审；单一路径）"""
        model_info = self._get_model_info()
        logger.info(
            f"开始 AI 初审(two-stage): video_id={video_id}, llm_mode={model_info['llm_mode']}, vision_mode={model_info['vision_mode']}"
        )

        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"视频不存在: video_id={video_id}")
                return {"status": 3, "error": "视频不存在"}

            # Stage 1: 抽帧初筛（控成本）
            stage1_max_frames = max(1, self.stage1_max_frames)
            stage1_frame_review = await review_frames_module(
                video_id, video_path, use_cloud_override=self.use_cloud_vision, max_frames=stage1_max_frames
            )
            stage1_subtitle_rule = self._subtitle_rule_screen(subtitle_path)

            need_full_frame_review = (
                (not self.two_stage_enabled)
                or bool(stage1_frame_review.get("has_violation"))
                or bool(stage1_frame_review.get("has_suspicious"))
                or int(stage1_frame_review.get("min_score", 100)) < self.stage2_trigger_min_score
            )

            need_subtitle_llm = bool(subtitle_path) and (
                (not self.two_stage_enabled)
                or need_full_frame_review
                or bool(stage1_subtitle_rule and stage1_subtitle_rule.get("is_suspicious"))
            )

            # Stage 2: 精审（仅在必要时对帧做全量；字幕按需调用）
            frame_review = stage1_frame_review
            if need_full_frame_review:
                frame_review = await review_frames_module(
                    video_id, video_path, use_cloud_override=self.use_cloud_vision, max_frames=None
                )

            subtitle_review = None
            if need_subtitle_llm and subtitle_path:
                subtitle_review = await self._review_subtitle(subtitle_path)

            # 综合判断
            final_status, final_score = determine_status(frame_review, subtitle_review)
            conclusion = generate_conclusion(frame_review, subtitle_review, final_status, final_score)

            review_report = {
                "timestamp": isoformat_in_app_tz(utc_now()),
                "video_id": video_id,
                "review_type": "two_stage",
                "final_score": final_score,
                "final_status": final_status,
                "conclusion": conclusion,
                "model_info": model_info,
                "stage1": {
                    "max_frames": stage1_max_frames,
                    "frame_review": stage1_frame_review,
                    "subtitle_rule": stage1_subtitle_rule,
                },
                "stage2": {
                    "full_frame_review": need_full_frame_review,
                    "subtitle_llm": need_subtitle_llm,
                },
                "frame_review": frame_review,
                "subtitle_review": subtitle_review if subtitle_review else None,
            }

            video.status = final_status
            video.review_score = final_score
            video.review_status = final_status
            video.review_report = dump_json_field(review_report)
            db.commit()

            logger.info(f"视频审核完成: video_id={video_id}, status={final_status}, score={final_score}")
            return {
                "status": final_status,
                "frame_review": frame_review,
                "subtitle_review": subtitle_review,
                "final_score": final_score,
                "review_report": review_report,
            }

        except Exception as e:
            logger.error(f"审核视频失败: {e}", exc_info=True)
            db.rollback()
            try:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.status = 1
                    db.commit()
            except Exception:
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
            
            model_info = self._get_model_info()
            # 仅审核帧
            frame_review = await review_frames_module(
                video_id, video_path, use_cloud_override=self.use_cloud_vision, max_frames=None
            )
            
            # 更新审核报告（保留原有的字幕审核结果）
            review_report = parse_review_report(video.review_report, default={})
            
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
            review_report["timestamp"] = isoformat_in_app_tz(utc_now())
            review_report["video_id"] = video_id
            
            # 更新模型信息
            review_report["model_info"] = model_info
            
            # 如果有字幕审核结果，重新计算综合评分
            subtitle_review = review_report.get("subtitle_review")
            if subtitle_review:
                final_status, final_score = determine_status(frame_review, subtitle_review)
                review_report["final_score"] = final_score
                review_report["final_status"] = final_status
                review_report["conclusion"] = generate_conclusion(frame_review, subtitle_review, final_status, final_score)
            else:
                # 仅帧审核，使用帧审核结果
                review_report["final_score"] = frame_review.get("avg_score", 100)
                review_report["final_status"] = 1  # 审核中
                review_report["conclusion"] = f"仅完成帧审核。共审核 {frame_review.get('total_frames', 0)} 帧，平均评分 {frame_review.get('avg_score', 100)} 分。"
            
            video.review_report = dump_json_field(review_report)
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
            
            model_info = self._get_model_info()
            # 如果没有提供字幕路径，从视频记录中获取
            if not subtitle_path:
                subtitle_path = video.subtitle_url
            
            # 仅审核字幕
            subtitle_review = await self._review_subtitle(subtitle_path)
            
            # 更新审核报告（保留原有的帧审核结果）
            review_report = parse_review_report(video.review_report, default={})
            
            # 更新字幕审核结果
            if subtitle_review:
                review_report["subtitle_review"] = subtitle_review
            else:
                review_report["subtitle_review"] = None
            
            review_report["timestamp"] = isoformat_in_app_tz(utc_now())
            review_report["video_id"] = video_id
            
            # 更新模型信息
            review_report["model_info"] = model_info
            
            # 如果有帧审核结果，重新计算综合评分
            frame_review = review_report.get("frame_review")
            if frame_review:
                final_status, final_score = determine_status(frame_review, subtitle_review)
                review_report["final_score"] = final_score
                review_report["final_status"] = final_status
                review_report["conclusion"] = generate_conclusion(frame_review, subtitle_review, final_status, final_score)
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
            
            video.review_report = dump_json_field(review_report)
            db.commit()
            
            logger.info(f"字幕审核完成: video_id={video_id}")
            return subtitle_review
            
        except Exception as e:
            logger.error(f"字幕审核失败: {e}", exc_info=True)
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()
    
    async def _review_subtitle(
        self,
        subtitle_path: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        审核字幕内容（支持云端/本地模型）
        
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
            
            # 解析字幕（支持 JSON 格式，云端/本地模型都可以直接读取 JSON 内容）
            subtitles = self.subtitle_parser.parse_subtitle_file(full_path)
            if not subtitles:
                logger.warning(f"[SubtitleReview] 字幕文件解析失败或为空: {full_path}")
                return None
            
            logger.info(f"[SubtitleReview] 成功解析字幕文件，共 {len(subtitles)} 条字幕")
            
            # 合并所有字幕文本（云端/本地模型都可以直接处理 JSON 格式的文本）
            subtitle_text = "\n".join([sub.get('text', '') if isinstance(sub, dict) else sub.text for sub in subtitles])
            
            if not subtitle_text.strip():
                logger.warning(f"[SubtitleReview] 字幕文本为空: {full_path}")
                return None
            
            # 记录字幕文本长度（用于调试）
            text_length = len(subtitle_text)
            model_info = self._get_model_info()
            logger.info(f"[SubtitleReview] 字幕文本长度: {text_length} 字符，开始调用 {model_info['text_model_display']} 审核")
            
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
                    status_label = "违规"
                elif is_suspicious:
                    status_label = "疑似"
                else:
                    status_label = "正常"
                
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
    

# 全局实例
video_review_service = VideoReviewService()
