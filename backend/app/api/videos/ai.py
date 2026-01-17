"""
视频 AI 功能 API

功能：
1. 生成视频大纲
2. 获取视频AI分析报告
3. 生成视频摘要
"""
import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc, and_, or_

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.exceptions import ResourceNotFoundException, ForbiddenException, ValidationException
from fastapi import HTTPException, status
from app.core.response import success_response
from app.core.config import settings
from app.models.user import User
from app.models.video import Video
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.services.cache.redis_service import redis_service
from app.services.ai.llm_service import llm_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{video_id}/outline/generate", response_model=dict)
async def generate_video_outline(
    video_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动触发生成视频大纲（需要登录，仅上传者可操作）
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以生成大纲")
    
    if not video.subtitle_url:
        raise ValidationException(message="视频没有字幕文件，无法生成大纲")

    status_key = f"outline:status:{video_id}"
    progress_key = f"outline:progress:{video_id}"
    lock_ttl_seconds = 2 * 60 * 60
    progress_ttl_seconds = 24 * 60 * 60

    if redis_service.redis.get(status_key):
        return success_response(
            data={"video_id": video_id, "status": "running"},
            message="Outline generation is already running.",
        )

    if video.outline and not force:
        return success_response(
            data={
                "video_id": video_id,
                "status": "completed",
                "confirm_required": True,
            },
            message="Outline already exists. Confirm to run again.",
        )
    
    # 异步生成大纲
    from app.services.video.outline_service import OutlineService

    def _set_progress(progress: int, message: str, status: str) -> None:
        payload = {"progress": progress, "message": message, "status": status}
        try:
            redis_service.redis.setex(
                progress_key,
                progress_ttl_seconds,
                json.dumps(payload),
            )
        except Exception as exc:
            logger.warning(f"Failed to update outline progress: {progress_key}, error={exc}")

    try:
        redis_service.redis.setex(status_key, lock_ttl_seconds, "running")
    except Exception as exc:
        logger.warning(f"Failed to set outline status: {status_key}, error={exc}")

    _set_progress(1, "Outline generation started", "running")
    
    async def generate_and_save():
        # 使用新的数据库会话保存
        from app.core.database import SessionLocal
        db_session = SessionLocal()
        try:
            logger.info(f"[视频 {video_id}] 开始生成大纲...")
            
            # 直接删除原有大纲（不保留）
            video_obj = db_session.query(Video).filter(Video.id == video_id).first()
            if video_obj:
                video_obj.outline = None  # 直接删除
                db_session.commit()
            
            async def progress_callback(progress: int, _message: str):
                _set_progress(progress, f"Outline progress {progress}%", "running")

            outline = await OutlineService.extract_outline(
                video_id,
                video.subtitle_url,
                progress_callback=progress_callback,
            )
            
            # 保存新大纲（仅当生成成功时保存，失败则不保存）
            video_obj = db_session.query(Video).filter(Video.id == video_id).first()
            if video_obj:
                if outline and len(outline) > 0:
                    # 生成成功，保存新大纲
                    video_obj.outline = json.dumps(outline, ensure_ascii=False)
                    db_session.commit()
                    logger.info(f"[视频 {video_id}] 视频大纲已生成完毕，共 {len(outline)} 个章节")
                    _set_progress(100, "Outline generation completed", "completed")
                else:
                    # 生成失败，不保存（保持为 None）
                    db_session.commit()
                    logger.error(f"[视频 {video_id}] 视频大纲生成出错：生成结果为空")
                    _set_progress(100, "Outline generation returned empty result", "failed")
        except Exception as e:
            logger.error(f"[视频 {video_id}] 视频大纲生成出错：{str(e)}", exc_info=True)
            _set_progress(0, "Outline generation failed", "failed")
            # 确保大纲被删除
            try:
                video_obj = db_session.query(Video).filter(Video.id == video_id).first()
                if video_obj:
                    video_obj.outline = None
                    db_session.commit()
            except:
                pass
        finally:
            db_session.close()
            try:
                redis_service.redis.delete(status_key)
            except Exception as exc:
                logger.warning(f"Failed to clear outline status: {status_key}, error={exc}")
    
    background_tasks.add_task(generate_and_save)
    
    return success_response(
        data={"video_id": video_id, "status": "started"},
        message="Outline generation task started."
    )


@router.get("/{video_id}/ai-analysis", summary="获取视频AI分析报告")
async def get_video_ai_analysis(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. 鉴权：只有作者能看
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权查看此报告")

    # 2. 检查数据量 (评论 + 弹幕)
    comment_count = db.query(Comment).filter(Comment.video_id == video_id).count()
    danmaku_count = db.query(Danmaku).filter(Danmaku.video_id == video_id).count()
    total_count = comment_count + danmaku_count


    thresholds = {
        "risk_score": 40,
        "severe_risk_score": 20,
        "low_quality_score": 60,
        "highlight_score": 85,
        "positive_score": 75,
        "neutral_range": [40, 75],
    }

    def _safe_rate(numerator: int, denominator: int) -> float:
        if not denominator:
            return 0.0
        return round(numerator / denominator, 4)

    def _clamp_score(value: float) -> int:
        return max(0, min(100, int(round(value))))

    def _module_flags() -> dict:
        mode = (getattr(settings, "LLM_MODE", "off") or "off").lower()
        local_enabled = mode in {"local_only", "hybrid"} or bool(getattr(settings, "LOCAL_LLM_ENABLED", False))
        cloud_enabled = mode in {"cloud_only", "hybrid"} and bool(getattr(settings, "LLM_API_KEY", ""))
        return {
            "rule_filter": True,
            "exact_cache": True,
            "semantic_cache": bool(getattr(settings, "AI_SEMANTIC_CACHE_TTL", 0)),
            "local_model": local_enabled,
            "cloud_model": cloud_enabled,
            "multi_agent": bool(getattr(settings, "MULTI_AGENT_ENABLED", False)),
            "queue_enabled": bool(getattr(settings, "AI_ANALYSIS_QUEUE_ENABLED", False)),
            "token_saving": bool(getattr(settings, "TOKEN_SAVE_ENABLED", False)),
        }

    if total_count == 0:
        return success_response(
            data={
                "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
                "risks": [],
                "summary": "暂无数据：该视频尚未产生足够的互动（评论/弹幕），无法进行AI智能分析。",
                "expert_results": [],
                "conflict_resolved": False,
                "model_info": {"mode": "off", "models": []},
                "prompt_version": None,
                "cost": {"calls": 0, "estimated_tokens": 0},
                "decision_trace_summary": {"rule_hits": 0, "cache_hits": 0, "llm_calls": 0},
                "governance": {
                    "philosophy": "视频是对象、AI是工具、社区是落点",
                    "overview": {
                        "total_interactions": 0,
                        "ai_coverage_rate": 0,
                        "quality_score": 0,
                        "risk_score": 0,
                        "governance_score": 0,
                        "risk_rate": 0,
                        "low_quality_rate": 0,
                        "highlight_rate": 0,
                    },
                    "distribution": {
                        "score_buckets": {"0_39": 0, "40_59": 0, "60_79": 0, "80_100": 0},
                    },
                    "quality": {
                        "highlight_count": 0,
                        "high_quality_count": 0,
                        "low_quality_count": 0,
                        "avg_score": 0,
                    },
                    "risk": {"risk_count": 0, "severe_risk_count": 0},
                    "exposure": {"highlight_count": 0, "items": []},
                    "sources": {"distribution": {}, "coverage_rate": 0},
                    "ablation": _module_flags(),
                    "thresholds": thresholds,
                    "computed_at": datetime.utcnow().isoformat() + "Z",
                }
            },
            message="暂无分析数据"
        )

    # 3. 统计情感分布 (基于 ai_score)
    # score < 40: 负面/争议
    # 40 <= score <= 75: 中性/普通
    # score > 75: 正面/优质
    
    # 3.1 弹幕统计
    danmaku_stats = db.query(
        func.sum(case((Danmaku.ai_score < 40, 1), else_=0)).label("negative"),
        func.sum(case((Danmaku.ai_score.between(40, 75), 1), else_=0)).label("neutral"),
        func.sum(case((Danmaku.ai_score > 75, 1), else_=0)).label("positive")
    ).filter(Danmaku.video_id == video_id).first()

    # 3.2 评论统计
    comment_stats = db.query(
        func.sum(case((Comment.ai_score < 40, 1), else_=0)).label("negative"),
        func.sum(case((Comment.ai_score.between(40, 75), 1), else_=0)).label("neutral"),
        func.sum(case((Comment.ai_score > 75, 1), else_=0)).label("positive")
    ).filter(Comment.video_id == video_id).first()

    # 合并统计
    positive = (danmaku_stats.positive or 0) + (comment_stats.positive or 0)
    neutral = (danmaku_stats.neutral or 0) + (comment_stats.neutral or 0)
    negative = (danmaku_stats.negative or 0) + (comment_stats.negative or 0)


    risk_threshold = thresholds["risk_score"]
    severe_threshold = thresholds["severe_risk_score"]
    low_quality_threshold = thresholds["low_quality_score"]
    highlight_threshold = thresholds["highlight_score"]
    positive_threshold = thresholds["positive_score"]

    danmaku_scored = db.query(func.count()).filter(
        Danmaku.video_id == video_id,
        Danmaku.ai_score.isnot(None)
    ).scalar() or 0
    comment_scored = db.query(func.count()).filter(
        Comment.video_id == video_id,
        Comment.ai_score.isnot(None)
    ).scalar() or 0
    ai_scored_count = danmaku_scored + comment_scored

    danmaku_avg = db.query(func.avg(Danmaku.ai_score)).filter(
        Danmaku.video_id == video_id,
        Danmaku.ai_score.isnot(None)
    ).scalar() or 0
    comment_avg = db.query(func.avg(Comment.ai_score)).filter(
        Comment.video_id == video_id,
        Comment.ai_score.isnot(None)
    ).scalar() or 0
    avg_score = 0
    if ai_scored_count:
        avg_score = round(
            (float(danmaku_avg or 0) * danmaku_scored + float(comment_avg or 0) * comment_scored) / ai_scored_count,
            2,
        )

    danmaku_risk_total = db.query(func.count()).filter(
        Danmaku.video_id == video_id,
        Danmaku.ai_score < risk_threshold,
    ).scalar() or 0
    comment_risk_total = db.query(func.count()).filter(
        Comment.video_id == video_id,
        Comment.ai_score < risk_threshold,
    ).scalar() or 0
    risk_total = danmaku_risk_total + comment_risk_total

    danmaku_severe_total = db.query(func.count()).filter(
        Danmaku.video_id == video_id,
        Danmaku.ai_score < severe_threshold,
    ).scalar() or 0
    comment_severe_total = db.query(func.count()).filter(
        Comment.video_id == video_id,
        Comment.ai_score < severe_threshold,
    ).scalar() or 0
    severe_total = danmaku_severe_total + comment_severe_total

    danmaku_low_quality = db.query(func.count()).filter(
        Danmaku.video_id == video_id,
        and_(Danmaku.ai_score >= risk_threshold, Danmaku.ai_score < low_quality_threshold),
    ).scalar() or 0
    comment_low_quality = db.query(func.count()).filter(
        Comment.video_id == video_id,
        and_(Comment.ai_score >= risk_threshold, Comment.ai_score < low_quality_threshold),
    ).scalar() or 0
    low_quality_total = danmaku_low_quality + comment_low_quality

    danmaku_highlight_count = db.query(func.count()).filter(
        Danmaku.video_id == video_id,
        or_(Danmaku.is_highlight == True, Danmaku.ai_score >= highlight_threshold),
    ).scalar() or 0
    comment_highlight_count = db.query(func.count()).filter(
        Comment.video_id == video_id,
        Comment.ai_score >= highlight_threshold,
    ).scalar() or 0
    highlight_total = danmaku_highlight_count + comment_highlight_count

    danmaku_bucket_stats = db.query(
        func.sum(case((Danmaku.ai_score < 40, 1), else_=0)).label("b0"),
        func.sum(case((and_(Danmaku.ai_score >= 40, Danmaku.ai_score < 60), 1), else_=0)).label("b40"),
        func.sum(case((and_(Danmaku.ai_score >= 60, Danmaku.ai_score < 80), 1), else_=0)).label("b60"),
        func.sum(case((Danmaku.ai_score >= 80, 1), else_=0)).label("b80"),
    ).filter(Danmaku.video_id == video_id).first()

    comment_bucket_stats = db.query(
        func.sum(case((Comment.ai_score < 40, 1), else_=0)).label("b0"),
        func.sum(case((and_(Comment.ai_score >= 40, Comment.ai_score < 60), 1), else_=0)).label("b40"),
        func.sum(case((and_(Comment.ai_score >= 60, Comment.ai_score < 80), 1), else_=0)).label("b60"),
        func.sum(case((Comment.ai_score >= 80, 1), else_=0)).label("b80"),
    ).filter(Comment.video_id == video_id).first()

    score_buckets = {
        "0_39": int((danmaku_bucket_stats.b0 or 0) + (comment_bucket_stats.b0 or 0)),
        "40_59": int((danmaku_bucket_stats.b40 or 0) + (comment_bucket_stats.b40 or 0)),
        "60_79": int((danmaku_bucket_stats.b60 or 0) + (comment_bucket_stats.b60 or 0)),
        "80_100": int((danmaku_bucket_stats.b80 or 0) + (comment_bucket_stats.b80 or 0)),
    }

    def _source_distribution(model):
        rows = db.query(model.ai_source, func.count()).filter(
            model.video_id == video_id
        ).group_by(model.ai_source).all()
        counts = {}
        for source, cnt in rows:
            key = source or "unknown"
            counts[key] = counts.get(key, 0) + int(cnt or 0)
        return counts

    source_counts = _source_distribution(Danmaku)
    for key, val in _source_distribution(Comment).items():
        source_counts[key] = source_counts.get(key, 0) + val

    ai_coverage_rate = _safe_rate(ai_scored_count, total_count)
    risk_rate = _safe_rate(risk_total, total_count)
    low_quality_rate = _safe_rate(low_quality_total, total_count)
    highlight_rate = _safe_rate(highlight_total, total_count)
    positive_rate = _safe_rate(score_buckets.get("80_100", 0), total_count)

    quality_score = _clamp_score((positive_rate * 0.6 + highlight_rate * 0.4) * 100)
    risk_score = _clamp_score((1 - risk_rate) * 100)
    governance_score = _clamp_score(quality_score * 0.6 + risk_score * 0.4)

    actions = []
    if risk_rate >= 0.12:
        actions.append(
            {
                "type": "risk",
                "title": "风险占比较高",
                "detail": f"风险率 {risk_rate:.0%}，建议加强人工抽检与重点巡检。",
            }
        )
    if highlight_rate <= 0.05 and total_count >= 50:
        actions.append(
            {
                "type": "highlight",
                "title": "高质量互动偏少",
                "detail": "建议通过社区激励提升高质量互动，并同步提升曝光权重。",
            }
        )
    if ai_coverage_rate < 0.8 and total_count >= 20:
        actions.append(
            {
                "type": "coverage",
                "title": "AI覆盖不足",
                "detail": "部分互动尚未分析，可等待队列或手动触发重算。",
            }
        )

    danmaku_highlights = db.query(Danmaku).filter(
        Danmaku.video_id == video_id,
        or_(Danmaku.is_highlight == True, Danmaku.ai_score >= highlight_threshold),
    ).order_by(desc(Danmaku.ai_score), desc(Danmaku.created_at)).limit(5).all()

    comment_highlights = db.query(Comment).filter(
        Comment.video_id == video_id,
        Comment.ai_score >= highlight_threshold,
    ).order_by(desc(Comment.ai_score), desc(Comment.created_at)).limit(5).all()

    highlight_items = []
    for d in danmaku_highlights:
        highlight_items.append({
            "type": "danmaku",
            "content": d.content,
            "score": d.ai_score,
            "time": d.created_at,
            "reason": d.ai_reason or "高质量弹幕",
            "source": getattr(d, "ai_source", "unknown"),
            "confidence": getattr(d, "ai_confidence", 0.5) or 0.5,
        })
    for c in comment_highlights:
        conf = getattr(c, "ai_confidence", None)
        highlight_items.append({
            "type": "comment",
            "content": c.content,
            "score": c.ai_score,
            "time": c.created_at,
            "reason": c.ai_reason or "高质量评论",
            "source": getattr(c, "ai_source", "unknown"),
            "confidence": (conf / 100.0) if conf else 0.5,
        })

    highlight_items.sort(key=lambda x: ((x.get("score") or 0), x.get("time")), reverse=True)
    highlight_items = highlight_items[:8]

    # 4. 获取风险/高亮内容 (从两张表获取，合并排序)
    danmaku_risks = db.query(Danmaku).filter(
        Danmaku.video_id == video_id,
        Danmaku.ai_score < 30
    ).order_by(desc(Danmaku.created_at)).limit(5).all()

    comment_risks = db.query(Comment).filter(
        Comment.video_id == video_id,
        Comment.ai_score < 30
    ).order_by(desc(Comment.created_at)).limit(5).all()

    # 合并并按时间倒序
    combined_risks = []
    for d in danmaku_risks:
        combined_risks.append({
            "content": d.content,
            "reason": d.ai_reason or "弹幕低分预警",
            "score": d.ai_score,
            "time": d.created_at,
            "source": getattr(d, "ai_source", "unknown"),
            "confidence": getattr(d, "ai_confidence", 0.5)
        })
    for c in comment_risks:
        combined_risks.append({
            "content": c.content,
            "reason": c.ai_reason or "评论低分预警",
            "score": c.ai_score,
            "time": c.created_at,
            "source": getattr(c, "ai_source", "unknown"),
            "confidence": getattr(c, "ai_confidence", 50) / 100.0 if getattr(c, "ai_confidence") else 0.5
        })
    
    # 再次排序取前5
    combined_risks.sort(key=lambda x: x['time'], reverse=True)
    final_risks = combined_risks[:5]

    # 5. 动态生成陪审团数据 (模拟逻辑)
    # 基于情感分布动态调整专家评分
    
    # Meme Expert: 正面内容越多，评分越高
    meme_score = 60 + min(35, int((positive / total_count) * 40)) if total_count > 0 else 80
    
    # Emotion Expert: 负面内容越少，评分越高
    emotion_score = 100 - min(40, int((negative / total_count) * 100)) if total_count > 0 else 90
    
    # Legal Expert: 风险内容越多，评分越低
    legal_score = max(50, _clamp_score(100 - int(risk_rate * 120)))

    expert_results = [
        {"agent": "Meme Expert", "score": meme_score, "opinion": "社区梗与互动氛围检测中...", "safe": True},
        {"agent": "Emotion Expert", "score": emotion_score, "opinion": "情感倾向与对立情绪分析中...", "safe": True},
        {"agent": "Legal Expert", "score": legal_score, "opinion": "合规性与潜在风险扫描中...", "safe": legal_score > 60}
    ]
    
    sentiment_desc = "积极" if positive > negative else "需关注"
    summary = (
        f"基于 {total_count} 条互动（{comment_count}条评论，{danmaku_count}条弹幕）分析，"
        f"整体氛围{sentiment_desc}。发现{risk_total} 条潜在风险互动，"
        f"{highlight_total} 条高质量互动可优先曝光。"
    )

    # 6. 新增：模型信息和成本统计
    from app.core.model_registry import model_registry
    available_models = model_registry.get_available_models()
    model_info = {
        "mode": llm_service.mode,
        "models": [{"type": k, "name": v.name, "base_url": v.base_url} for k, v in available_models.items()]
    }
    
    # 7. 新增：获取当前激活的Prompt版本
    from app.models.ai_prompt_version import AiPromptVersion
    active_danmaku_prompt = db.query(AiPromptVersion).filter(
        AiPromptVersion.prompt_type == "DANMAKU",
        AiPromptVersion.is_active == True
    ).first()
    active_comment_prompt = db.query(AiPromptVersion).filter(
        AiPromptVersion.prompt_type == "COMMENT", 
        AiPromptVersion.is_active == True
    ).first()
    
    prompt_version = {
        "danmaku": {"id": active_danmaku_prompt.id, "created_at": active_danmaku_prompt.created_at} if active_danmaku_prompt else None,
        "comment": {"id": active_comment_prompt.id, "created_at": active_comment_prompt.created_at} if active_comment_prompt else None
    }
    
    # 8. 新增：成本统计（从cost_tracker获取）
    cost_info = llm_service.cost_tracker.get(video_id, {"calls": 0, "chars": 0})
    
    # 9. 新增：决策轨迹摘要（从Redis获取埋点数据）
    try:
        today = datetime.utcnow().strftime("%Y%m%d")
        metrics_keys = [f"ai:metrics:{today}:rule_hit", f"ai:metrics:{today}:exact_hit", 
                       f"ai:metrics:{today}:cloud_call", f"ai:metrics:{today}:local_call"]
        # 使用mget获取多个值，如果失败则逐个获取
        try:
            metrics_values = await redis_service.async_redis.mget(*metrics_keys)
            if metrics_values is None:
                metrics_values = [None] * len(metrics_keys)
        except Exception:
            # 如果mget失败，逐个获取
            metrics_values = []
            for key in metrics_keys:
                try:
                    val = await redis_service.async_redis.get(key)
                    metrics_values.append(val)
                except Exception:
                    metrics_values.append(None)
        
        decision_trace_summary = {
            "rule_hits": int(metrics_values[0] or 0) if metrics_values and len(metrics_values) > 0 else 0,
            "cache_hits": int(metrics_values[1] or 0) if metrics_values and len(metrics_values) > 1 else 0, 
            "cloud_calls": int(metrics_values[2] or 0) if metrics_values and len(metrics_values) > 2 else 0,
            "local_calls": int(metrics_values[3] or 0) if metrics_values and len(metrics_values) > 3 else 0
        }
    except Exception as e:
        logger.warning(f"获取决策轨迹摘要失败: {e}")
        decision_trace_summary = {"rule_hits": 0, "cache_hits": 0, "cloud_calls": 0, "local_calls": 0}

    governance = {
        "philosophy": "视频是对象、AI是工具、社区是落点",
        "overview": {
            "total_interactions": total_count,
            "ai_coverage_rate": ai_coverage_rate,
            "quality_score": quality_score,
            "risk_score": risk_score,
            "governance_score": governance_score,
            "risk_rate": risk_rate,
            "low_quality_rate": low_quality_rate,
            "highlight_rate": highlight_rate,
            "auto_review_saving_rate": _safe_rate(total_count - risk_total, total_count),
            "avg_score": avg_score,
        },
        "distribution": {
            "score_buckets": score_buckets,
        },
        "quality": {
            "highlight_count": highlight_total,
            "high_quality_count": score_buckets.get("80_100", 0),
            "low_quality_count": low_quality_total,
            "avg_score": avg_score,
        },
        "risk": {
            "risk_count": risk_total,
            "severe_risk_count": severe_total,
        },
        "exposure": {
            "highlight_count": highlight_total,
            "items": highlight_items,
        },
        "sources": {
            "distribution": source_counts,
            "coverage_rate": ai_coverage_rate,
        },
        "actions": actions,
        "ablation": _module_flags(),
        "thresholds": thresholds,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }

    return {
        "sentiment": {
            "positive": positive,
            "neutral": neutral,
            "negative": negative
        },
        "risks": final_risks,
        "summary": summary,
        "expert_results": expert_results,
        "conflict_resolved": False,
        "model_info": model_info,
        "prompt_version": prompt_version,
        "cost": {
            "calls": cost_info["calls"],
            "estimated_tokens": cost_info["chars"] // 4  # 粗略估算token数
        },
        "decision_trace_summary": decision_trace_summary,
        "governance": governance
    }


@router.get("/{video_id}/ai-analysis/items", summary="获取AI分析明细（弹幕/评论）")
async def get_ai_analysis_items(
    video_id: int,
    item_type: Optional[str] = None,  # danmaku/comment
    filter: Optional[str] = None,     # risk/highlight
    score_lt: Optional[int] = None,
    score_gt: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 鉴权：作者或管理员
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权查看此报告")

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    items = []
    total = 0

    def apply_filters(query, model):
        nonlocal total
        if filter == "risk":
            query = query.filter(model.ai_score < 40)
        if filter == "highlight":
            # 弹幕用 is_highlight / 评论用高分近似
            if hasattr(model, "is_highlight"):
                query = query.filter(model.is_highlight == True)
            else:
                query = query.filter(model.ai_score >= 80)
        if score_lt is not None:
            query = query.filter(model.ai_score < score_lt)
        if score_gt is not None:
            query = query.filter(model.ai_score > score_gt)
        total = query.count()
        return (
            query.order_by(model.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    # danmaku
    if item_type in (None, "danmaku"):
        q = db.query(Danmaku).filter(Danmaku.video_id == video_id)
        danmaku_list = apply_filters(q, Danmaku)
        for d in danmaku_list:
            # 解析决策轨迹获取详细来源信息
            ai_trace = None
            source_detail = getattr(d, "ai_source", None) or "unknown"
            model_detail = getattr(d, "ai_model", None)
            
            # 如果有ai_trace，解析获取更详细的来源信息
            if hasattr(d, "ai_trace") and d.ai_trace:
                try:
                    ai_trace = json.loads(d.ai_trace) if isinstance(d.ai_trace, str) else d.ai_trace
                    # 从trace中提取更详细的来源信息
                    if isinstance(ai_trace, list):
                        for step in ai_trace:
                            if step.get("step") == "rule_hit":
                                source_detail = "rule_hit"
                            elif step.get("step") == "cache_exact_hit":
                                source_detail = "cache_exact"
                            elif step.get("step") == "cache_semantic_hit":
                                source_detail = "cache_semantic"
                            elif step.get("step") == "local_model_call":
                                source_detail = "local_model"
                                model_detail = step.get("model_name") or model_detail
                            elif step.get("step") == "cloud_model_call":
                                source_detail = "cloud_llm"
                                model_detail = step.get("model_name") or model_detail
                except Exception:
                    pass
            
            items.append({
                "id": d.id,
                "type": "danmaku",
                "content": d.content,
                "score": d.ai_score,
                "ai_category": getattr(d, "ai_category", None),
                "ai_reason": getattr(d, "ai_reason", None),
                "ai_confidence": getattr(d, "ai_confidence", 0.5),
                "ai_source": source_detail,
                "ai_model": model_detail,
                "ai_prompt_version_id": getattr(d, "ai_prompt_version_id", None),
                "is_highlight": getattr(d, "is_highlight", False),
                "created_at": d.created_at,
            })

    # comment
    if item_type in (None, "comment"):
        q = db.query(Comment).filter(Comment.video_id == video_id)
        comment_list = apply_filters(q, Comment)
        for c in comment_list:
            # 解析决策轨迹获取详细来源信息
            ai_trace = None
            source_detail = getattr(c, "ai_source", None) or "unknown"
            model_detail = getattr(c, "ai_model", None)
            
            # 如果有ai_trace，解析获取更详细的来源信息
            if hasattr(c, "ai_trace") and c.ai_trace:
                try:
                    ai_trace = json.loads(c.ai_trace) if isinstance(c.ai_trace, str) else c.ai_trace
                    # 从trace中提取更详细的来源信息
                    if isinstance(ai_trace, list):
                        for step in ai_trace:
                            if step.get("step") == "rule_hit":
                                source_detail = "rule_hit"
                            elif step.get("step") == "cache_exact_hit":
                                source_detail = "cache_exact"
                            elif step.get("step") == "cache_semantic_hit":
                                source_detail = "cache_semantic"
                            elif step.get("step") == "local_model_call":
                                source_detail = "local_model"
                                model_detail = step.get("model_name") or model_detail
                            elif step.get("step") == "cloud_model_call":
                                source_detail = "cloud_llm"
                                model_detail = step.get("model_name") or model_detail
                except Exception:
                    pass
            
            items.append({
                "id": c.id,
                "type": "comment",
                "content": c.content,
                "score": c.ai_score,
                "ai_label": getattr(c, "ai_label", None),
                "ai_reason": getattr(c, "ai_reason", None),
                "ai_confidence": getattr(c, "ai_confidence", 50) / 100.0 if getattr(c, "ai_confidence") else 0.5,
                "ai_source": source_detail,
                "ai_model": model_detail,
                "ai_prompt_version_id": getattr(c, "ai_prompt_version_id", None),
                "is_highlight": getattr(c, "ai_score", 0) >= 80,
                "created_at": c.created_at,
            })

    # 合并后按时间排序
    items.sort(key=lambda x: x["created_at"], reverse=True)
    # 截断到当前分页大小（因为两类合并后可能超过）
    items = items[:page_size]

    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/{video_id}/ai-analysis/recompute", summary="触发AI分析重算（异步占位）")
async def trigger_ai_analysis_recompute(
    video_id: int,
    scope: str = "recent",  # recent/all
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权触发重算")

    redis_client = redis_service.redis
    progress_key = f"analysis:progress:{video_id}"
    payload = {
        "status": "queued",
        "progress": 0,
        "scope": scope,
        "limit": limit,
        "message": "重算任务已排队（占位，需后台任务实现）"
    }
    try:
        redis_client.setex(progress_key, 600, json.dumps(payload, default=str))
    except Exception as e:
        logger.error(f"设置重算进度失败: {e}")
    return success_response(data=payload, message="已排队重算（占位实现）")


@router.post("/{video_id}/ai-analysis/jury", summary="手动触发多智能体复核（仅上传者/管理员）")
async def trigger_ai_analysis_jury(
    video_id: int,
    scope: str = "recent",  # recent/all
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动触发多智能体复核，默认仅处理最近数据，上传者/管理员可用。
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权触发多智能体复核")

    # 获取弹幕与评论
    danmaku_query = (
        db.query(Danmaku)
        .filter(Danmaku.video_id == video_id, Danmaku.is_deleted == False)  # noqa: E712
        .order_by(Danmaku.created_at.desc())
    )
    comment_query = (
        db.query(Comment)
        .filter(Comment.video_id == video_id)
        .order_by(Comment.created_at.desc())
    )
    if scope != "all":
        danmakus = danmaku_query.limit(limit).all()
        comments = comment_query.limit(limit).all()
    else:
        danmakus = danmaku_query.all()
        comments = comment_query.all()

    processed = 0
    errors = 0

    async def _apply_result_for_danmaku(d):
        nonlocal processed, errors
        try:
            result = await llm_service.analyze_content(d.content, "danmaku", force_jury=True)
            d.ai_score = result.get("score", 60)
            d.ai_category = result.get("category", "普通")
            d.ai_reason = result.get("reason")
            d.ai_confidence = result.get("confidence", 0.5)
            d.ai_source = result.get("source")
            d.ai_prompt_version_id = result.get("prompt_version_id")
            d.ai_model = result.get("model_name")
            trace = result.get("decision_trace")
            d.ai_trace = json.dumps(trace, ensure_ascii=False) if trace else None
            d.is_highlight = result.get("is_highlight", False) or d.ai_score >= 90
            processed += 1
        except Exception as e:
            logger.error(f"Jury 复核弹幕失败 id={d.id}: {e}")
            errors += 1

    async def _apply_result_for_comment(c):
        nonlocal processed, errors
        try:
            result = await llm_service.analyze_content(c.content, "comment", force_jury=True)
            c.ai_score = result.get("score", 60)
            c.ai_label = result.get("label", "普通")
            c.ai_reason = result.get("reason")
            conf = result.get("confidence", 0.5)
            c.ai_confidence = int(conf * 100) if conf is not None else None
            c.ai_source = result.get("source")
            c.ai_prompt_version_id = result.get("prompt_version_id")
            c.ai_model = result.get("model_name")
            trace = result.get("decision_trace")
            c.ai_trace = json.dumps(trace, ensure_ascii=False) if trace else None
            processed += 1
        except Exception as e:
            logger.error(f"Jury 复核评论失败 id={c.id}: {e}")
            errors += 1

    # 顺序执行，避免占用过多资源
    for d in danmakus:
        await _apply_result_for_danmaku(d)
        db.commit()
    for c in comments:
        await _apply_result_for_comment(c)
        db.commit()

    return success_response(
        data={
            "processed": processed,
            "errors": errors,
            "danmaku_total": len(danmakus),
            "comment_total": len(comments),
            "scope": scope,
            "limit": limit,
        },
        message="已完成多智能体复核"
    )


@router.get("/{video_id}/ai-analysis/progress", summary="查询AI分析重算进度")
async def get_ai_analysis_progress(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权查看进度")

    progress_key = f"analysis:progress:{video_id}"
    try:
        val = redis_service.redis.get(progress_key)
        if not val:
            return success_response(
                data={"status": "idle", "progress": 0, "message": "未找到进行中的任务"}
            )
        return success_response(data=json.loads(val))
    except Exception as e:
        logger.error(f"查询重算进度失败: {e}")
        return success_response(
            data={"status": "unknown", "progress": 0, "message": "查询失败"}
        )


@router.post("/{video_id}/summary", summary="生成视频摘要")
async def generate_video_summary(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    生成视频摘要和核心知识点
    
    基于字幕（权重70%）、弹幕（权重20%）、评论（权重10%）生成摘要
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 权限检查：只有上传者或管理员可以触发生成
    if current_user and video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("只有视频上传者或管理员可以生成摘要")
    
    # 异步生成摘要（避免阻塞）
    from app.services.video.summary_service import summary_service
    background_tasks.add_task(summary_service.generate_summary, video_id)
    
    return success_response(
        data={},
        message="摘要生成任务已启动，请稍后查询"
    )


@router.post("/{video_id}/summary/realtime", summary="实时生成视频摘要（不保存）")
async def generate_realtime_summary(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    实时生成视频摘要（不保存到数据库）
    
    返回结构化摘要，包含：问题背景、研究方法、主要发现、最终结论
    任何人都可以调用此接口
    """
    from app.services.video.summary_service import summary_service
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    try:
        # 获取视频内容数据
        content_data = summary_service._collect_content(video, db)
        
        # 生成结构化摘要
        structured_summary = await summary_service._generate_structured_summary(content_data)
        
        return success_response(
            data=structured_summary,
            message="摘要生成成功"
        )
    except Exception as e:
        logger.error(f"实时生成摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成摘要失败: {str(e)}"
        )


@router.put("/{video_id}/ai-analysis/highlight/{item_type}/{item_id}", summary="更新内容高亮状态")
async def update_highlight_status(
    video_id: int,
    item_type: str,  # "danmaku" 或 "comment"
    item_id: int,
    is_highlight: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动更新内容的高亮状态（仅上传者/管理员）
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权修改此内容的高亮状态")
    
    if item_type == "danmaku":
        item = db.query(Danmaku).filter(
            Danmaku.id == item_id,
            Danmaku.video_id == video_id
        ).first()
        if not item:
            raise ResourceNotFoundException(resource="弹幕", resource_id=item_id)
        item.is_highlight = is_highlight
    elif item_type == "comment":
        item = db.query(Comment).filter(
            Comment.id == item_id,
            Comment.video_id == video_id
        ).first()
        if not item:
            raise ResourceNotFoundException(resource="评论", resource_id=item_id)
        # 评论没有is_highlight字段，通过ai_score来标记（>=85视为高亮）
        # 这里我们可以在Comment模型中添加is_highlight字段，或者通过其他方式标记
        # 暂时先返回错误，提示评论不支持手动修改高亮
        raise ValidationException("评论的高亮状态由AI评分决定，暂不支持手动修改")
    else:
        raise ValidationException(f"不支持的内容类型: {item_type}")
    
    db.commit()
    
    return success_response(
        data={"item_id": item_id, "item_type": item_type, "is_highlight": is_highlight},
        message="高亮状态已更新"
    )
