"""
AI管理 API（管理员）
功能：AI修正记录、自我纠错、Prompt版本管理
"""
import math
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from sqlalchemy import func, case, and_, or_

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.core.error_handler import handle_api_errors
from app.core.config import settings
from app.core.response import success_response
from app.models.user import User
from app.models.ai_correction import AiCorrection
from app.models.ai_prompt_task import AiPromptTask
from app.models.ai_prompt_experiment import AiPromptExperiment
from app.models.video import Video
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.services.ai.self_correction_service import self_correction_service
from app.services.ai.prompt_workflow_service import prompt_workflow_service
from app.schemas.user import MessageResponse
from app.services.cache.redis_service import redis_service
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


# Schema定义
class CorrectionCreateRequest(BaseModel):
    """创建修正记录请求"""
    content: str
    content_type: str  # "comment" 或 "danmaku"
    original_result: dict
    corrected_result: dict
    correction_reason: str
    # 新增：可复现性字段（可选）
    prompt_version_id: Optional[int] = None
    model_config_snapshot: Optional[dict] = None
    decision_trace_snapshot: Optional[dict] = None


class CorrectionResponse(BaseModel):
    """修正记录响应"""
    id: int
    content: str
    content_type: str
    original_result: dict
    corrected_result: dict
    correction_reason: str
    corrected_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ErrorAnalysisRequest(BaseModel):
    """错误分析请求"""
    days: int = 7
    content_type: Optional[str] = None  # "comment", "danmaku" 或 None


class PromptUpdateRequest(BaseModel):
    """Prompt更新请求"""
    prompt_type: str  # "COMMENT" 或 "DANMAKU"
    new_prompt: str
    update_reason: str


class PromptPublishRequest(BaseModel):
    """Prompt发布请求"""
    version_id: int


class PromptCreateDraftRequest(BaseModel):
    """创建草案 Prompt 版本请求"""
    prompt_type: str
    draft_content: str
    sample_ids: List[int] = Field(default_factory=list)
    risk_notes: List[str] = Field(default_factory=list)
    expected_impact: str = ""


class PromptShadowTestRequest(BaseModel):
    """Prompt Shadow测试请求"""
    candidate_version_id: int
    sample_limit: int = 50  # 测试样本数量限制
    model_source: str = "auto"
    dataset_source: str = "corrections"
    task_id: Optional[int] = None
    save_experiment: bool = True


class PromptRollbackRequest(BaseModel):
    """Prompt 回滚请求"""
    version_id: int


class PromptTaskCreateRequest(BaseModel):
    """Prompt 工作流任务创建请求"""
    name: str
    prompt_type: str
    goal: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)
    dataset_source: str = "corrections"
    sample_min: int = 20
    is_active: bool = True


class PromptTaskUpdateRequest(BaseModel):
    """Prompt 工作流任务更新请求"""
    name: Optional[str] = None
    goal: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    dataset_source: Optional[str] = None
    sample_min: Optional[int] = None
    is_active: Optional[bool] = None


class MetricsResponse(BaseModel):
    date: str
    metrics: dict


@router.post("/corrections", response_model=CorrectionResponse, summary="提交AI修正记录")
async def create_correction(
    correction_in: CorrectionCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员提交AI分析修正记录"""
    try:
        correction = AiCorrection(
            content=correction_in.content,
            content_type=correction_in.content_type,
            original_result=correction_in.original_result,
            corrected_result=correction_in.corrected_result,
            correction_reason=correction_in.correction_reason,
            prompt_version_id=correction_in.prompt_version_id,
            model_config_snapshot=correction_in.model_config_snapshot,
            decision_trace_snapshot=correction_in.decision_trace_snapshot,
            corrected_by=current_admin.id
        )
        
        db.add(correction)
        db.commit()
        db.refresh(correction)
        
        logger.info(f"管理员 {current_admin.username} 提交了AI修正记录: {correction.id}")
        
        return correction
        
    except Exception as e:
        logger.error(f"创建修正记录失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="创建修正记录失败")


@router.get("/metrics", summary="获取AI埋点计数（每日分片）")
async def get_ai_metrics(
    target_date: Optional[str] = None,
    metrics: Optional[List[str]] = Query(None, description="指定需要的指标名称，默认取常用指标"),
    current_admin: User = Depends(get_current_admin),
):
    """
    返回指定日期的计数埋点，数据来源于 ai:metrics:{yyyymmdd}:{metric}
    """
    try:
        if target_date:
            try:
                datetime.strptime(target_date, "%Y%m%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="target_date 格式应为 YYYYMMDD")
            date_key = target_date
        else:
            date_key = datetime.utcnow().strftime("%Y%m%d")

        default_metrics = [
            "rule_hit",
            "exact_hit",
            "semantic_hit",
            "cloud_attempt",
            "cloud_call",
            "cloud_http_error",
            "cloud_http_4xx",
            "cloud_http_5xx",
            "cloud_http_429",
            "cloud_exception",
            "cloud_parse_error",
            "local_call",
            "jury_call",
            "llm_off",
        ]
        metric_names = metrics or default_metrics
        keys = [f"ai:metrics:{date_key}:{m}" for m in metric_names]
        values = await redis_service.async_redis.mget(*keys)
        data = {}
        for m, v in zip(metric_names, values):
            try:
                data[m] = int(v) if v is not None else 0
            except Exception:
                data[m] = 0

        return success_response(
            data={"date": date_key, "metrics": data},
            message="获取成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取AI指标失败")


@router.get("/config", summary="查看AI配置概览")
async def get_ai_config_overview(
    current_admin: User = Depends(get_current_admin),
):
    """
    提供当前 AI 关键配置，用于前端展示（脱敏）。
    """
    try:
        mode = getattr(settings, "LLM_MODE", "hybrid").lower()
        vision_mode = getattr(settings, "VISION_MODE", "hybrid").lower()
        use_cloud_llm = mode in ("cloud_only", "hybrid") and bool(settings.LLM_API_KEY)
        use_local_llm = mode in ("local_only", "hybrid")
        use_cloud_vision = vision_mode in ("cloud_only", "hybrid") and bool(
            getattr(settings, "LLM_VISION_API_KEY", "") or settings.LLM_API_KEY
        )
        data = {
            "llm_mode": mode,
            "vision_mode": vision_mode,
            "use_cloud_llm": use_cloud_llm,
            "use_local_llm": use_local_llm,
            "use_cloud_vision": use_cloud_vision,
            "cloud_model": settings.LLM_MODEL,
            "local_model": settings.LOCAL_LLM_MODEL,
            "vision_model": settings.LLM_VISION_MODEL or settings.LLM_MODEL,
            "cloud_frame_review_max_concurrent": getattr(settings, "CLOUD_FRAME_REVIEW_MAX_CONCURRENT", None),
            "cloud_max_calls_per_video": getattr(settings, "CLOUD_MAX_CALLS_PER_VIDEO", None),
            "cloud_max_input_chars_per_video": getattr(settings, "CLOUD_MAX_INPUT_CHARS_PER_VIDEO", None),
            "frame_review_max_concurrent": getattr(settings, "FRAME_REVIEW_MAX_CONCURRENT", None),
            "multi_agent_enabled": settings.MULTI_AGENT_ENABLED,
            "multi_agent_conflict_threshold": settings.MULTI_AGENT_CONFLICT_THRESHOLD,
        }
        return success_response(data=data)
    except Exception as e:
        logger.error(f"获取AI配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取AI配置失败")


@router.get("/governance/overview", summary="获取AI智能治理总览")
async def get_ai_governance_overview(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=3, le=50),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """聚合平台层面的互动治理指标，用于管理端看板。"""
    end_time = utc_now()
    start_time = end_time - timedelta(days=days)

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

    risk_threshold = thresholds["risk_score"]
    severe_threshold = thresholds["severe_risk_score"]
    low_quality_threshold = thresholds["low_quality_score"]
    highlight_threshold = thresholds["highlight_score"]

    comment_total = (
        db.query(func.count())
        .filter(Comment.created_at >= start_time)
        .scalar()
        or 0
    )
    danmaku_total = (
        db.query(func.count())
        .filter(Danmaku.created_at >= start_time)
        .scalar()
        or 0
    )
    total_count = comment_total + danmaku_total

    comment_scored = (
        db.query(func.count())
        .filter(Comment.created_at >= start_time, Comment.ai_score.isnot(None))
        .scalar()
        or 0
    )
    danmaku_scored = (
        db.query(func.count())
        .filter(Danmaku.created_at >= start_time, Danmaku.ai_score.isnot(None))
        .scalar()
        or 0
    )
    ai_scored_count = comment_scored + danmaku_scored

    comment_avg = (
        db.query(func.avg(Comment.ai_score))
        .filter(Comment.created_at >= start_time, Comment.ai_score.isnot(None))
        .scalar()
        or 0
    )
    danmaku_avg = (
        db.query(func.avg(Danmaku.ai_score))
        .filter(Danmaku.created_at >= start_time, Danmaku.ai_score.isnot(None))
        .scalar()
        or 0
    )
    avg_score = 0
    if ai_scored_count:
        avg_score = round(
            (float(comment_avg or 0) * comment_scored + float(danmaku_avg or 0) * danmaku_scored)
            / ai_scored_count,
            2,
        )

    comment_risk_total = (
        db.query(func.count())
        .filter(Comment.created_at >= start_time, Comment.ai_score < risk_threshold)
        .scalar()
        or 0
    )
    danmaku_risk_total = (
        db.query(func.count())
        .filter(Danmaku.created_at >= start_time, Danmaku.ai_score < risk_threshold)
        .scalar()
        or 0
    )
    risk_total = comment_risk_total + danmaku_risk_total

    comment_severe_total = (
        db.query(func.count())
        .filter(Comment.created_at >= start_time, Comment.ai_score < severe_threshold)
        .scalar()
        or 0
    )
    danmaku_severe_total = (
        db.query(func.count())
        .filter(Danmaku.created_at >= start_time, Danmaku.ai_score < severe_threshold)
        .scalar()
        or 0
    )
    severe_total = comment_severe_total + danmaku_severe_total

    comment_low_quality = (
        db.query(func.count())
        .filter(
            Comment.created_at >= start_time,
            and_(Comment.ai_score >= risk_threshold, Comment.ai_score < low_quality_threshold),
        )
        .scalar()
        or 0
    )
    danmaku_low_quality = (
        db.query(func.count())
        .filter(
            Danmaku.created_at >= start_time,
            and_(Danmaku.ai_score >= risk_threshold, Danmaku.ai_score < low_quality_threshold),
        )
        .scalar()
        or 0
    )
    low_quality_total = comment_low_quality + danmaku_low_quality

    comment_highlight_count = (
        db.query(func.count())
        .filter(Comment.created_at >= start_time, Comment.ai_score >= highlight_threshold)
        .scalar()
        or 0
    )
    danmaku_highlight_count = (
        db.query(func.count())
        .filter(
            Danmaku.created_at >= start_time,
            or_(Danmaku.is_highlight == True, Danmaku.ai_score >= highlight_threshold),
        )
        .scalar()
        or 0
    )
    highlight_total = comment_highlight_count + danmaku_highlight_count

    comment_bucket_stats = db.query(
        func.sum(case((Comment.ai_score < 40, 1), else_=0)).label("b0"),
        func.sum(case((and_(Comment.ai_score >= 40, Comment.ai_score < 60), 1), else_=0)).label("b40"),
        func.sum(case((and_(Comment.ai_score >= 60, Comment.ai_score < 80), 1), else_=0)).label("b60"),
        func.sum(case((Comment.ai_score >= 80, 1), else_=0)).label("b80"),
    ).filter(Comment.created_at >= start_time).first()

    danmaku_bucket_stats = db.query(
        func.sum(case((Danmaku.ai_score < 40, 1), else_=0)).label("b0"),
        func.sum(case((and_(Danmaku.ai_score >= 40, Danmaku.ai_score < 60), 1), else_=0)).label("b40"),
        func.sum(case((and_(Danmaku.ai_score >= 60, Danmaku.ai_score < 80), 1), else_=0)).label("b60"),
        func.sum(case((Danmaku.ai_score >= 80, 1), else_=0)).label("b80"),
    ).filter(Danmaku.created_at >= start_time).first()

    score_buckets = {
        "0_39": int((comment_bucket_stats.b0 or 0) + (danmaku_bucket_stats.b0 or 0)),
        "40_59": int((comment_bucket_stats.b40 or 0) + (danmaku_bucket_stats.b40 or 0)),
        "60_79": int((comment_bucket_stats.b60 or 0) + (danmaku_bucket_stats.b60 or 0)),
        "80_100": int((comment_bucket_stats.b80 or 0) + (danmaku_bucket_stats.b80 or 0)),
    }

    def _source_distribution(model):
        rows = (
            db.query(model.ai_source, func.count())
            .filter(model.created_at >= start_time)
            .group_by(model.ai_source)
            .all()
        )
        counts: Dict[str, int] = {}
        for source, cnt in rows:
            key = source or "unknown"
            counts[key] = counts.get(key, 0) + int(cnt or 0)
        return counts

    source_counts = _source_distribution(Comment)
    for key, val in _source_distribution(Danmaku).items():
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
                "detail": f"风险率 {risk_rate:.0%}，建议强化人工抽检与重点巡检。",
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

    def _collect_video_stats(model, highlight_expr) -> Dict[int, Dict[str, int]]:
        rows = db.query(
            model.video_id.label("video_id"),
            func.count().label("total"),
            func.sum(case((model.ai_score.isnot(None), 1), else_=0)).label("scored"),
            func.sum(case((model.ai_score < risk_threshold, 1), else_=0)).label("risk"),
            func.sum(case((model.ai_score < severe_threshold, 1), else_=0)).label("severe"),
            func.sum(case((highlight_expr, 1), else_=0)).label("highlight"),
            func.sum(
                case(
                    (
                        and_(model.ai_score >= risk_threshold, model.ai_score < low_quality_threshold),
                        1,
                    ),
                    else_=0,
                )
            ).label("low_quality"),
        ).filter(model.created_at >= start_time).group_by(model.video_id).all()

        result: Dict[int, Dict[str, int]] = {}
        for row in rows:
            result[int(row.video_id)] = {
                "total": int(row.total or 0),
                "scored": int(row.scored or 0),
                "risk": int(row.risk or 0),
                "severe": int(row.severe or 0),
                "highlight": int(row.highlight or 0),
                "low_quality": int(row.low_quality or 0),
            }
        return result

    comment_stats = _collect_video_stats(Comment, Comment.ai_score >= highlight_threshold)
    danmaku_stats = _collect_video_stats(
        Danmaku, or_(Danmaku.is_highlight == True, Danmaku.ai_score >= highlight_threshold)
    )

    video_stats: Dict[int, Dict[str, int]] = {}
    for vid, stats in comment_stats.items():
        video_stats.setdefault(vid, {"total": 0, "scored": 0, "risk": 0, "severe": 0, "highlight": 0, "low_quality": 0})
        for key, val in stats.items():
            video_stats[vid][key] += val
    for vid, stats in danmaku_stats.items():
        video_stats.setdefault(vid, {"total": 0, "scored": 0, "risk": 0, "severe": 0, "highlight": 0, "low_quality": 0})
        for key, val in stats.items():
            video_stats[vid][key] += val

    video_items: List[Dict[str, Any]] = []
    if video_stats:
        videos = (
            db.query(Video)
            .filter(Video.id.in_(list(video_stats.keys())))
            .all()
        )
        video_map = {v.id: v for v in videos}
        for vid, stats in video_stats.items():
            video = video_map.get(vid)
            if not video:
                continue
            total = stats["total"] or 0
            risk_rate_item = _safe_rate(stats["risk"], total)
            highlight_rate_item = _safe_rate(stats["highlight"], total)
            coverage_rate_item = _safe_rate(stats["scored"], total)
            low_quality_rate_item = _safe_rate(stats["low_quality"], total)
            quality_score_item = _clamp_score(
                (highlight_rate_item * 0.6 + (1 - low_quality_rate_item) * 0.4) * 100
            )
            risk_score_item = _clamp_score((1 - risk_rate_item) * 100)
            governance_score_item = _clamp_score(quality_score_item * 0.6 + risk_score_item * 0.4)
            video_items.append(
                {
                    "video_id": vid,
                    "title": video.title,
                    "cover_url": video.cover_url,
                    "created_at": isoformat_in_app_tz(video.created_at),
                    "status": video.status,
                    "review_status": video.review_status,
                    "uploader": {
                        "id": video.uploader.id if video.uploader else None,
                        "username": video.uploader.username if video.uploader else "",
                        "nickname": video.uploader.nickname if video.uploader else "",
                        "avatar": video.uploader.avatar if video.uploader else None,
                    },
                    "metrics": {
                        "total_interactions": total,
                        "risk_count": stats["risk"],
                        "severe_risk_count": stats["severe"],
                        "highlight_count": stats["highlight"],
                        "low_quality_count": stats["low_quality"],
                        "ai_coverage_rate": coverage_rate_item,
                        "risk_rate": risk_rate_item,
                        "highlight_rate": highlight_rate_item,
                        "governance_score": governance_score_item,
                    },
                }
            )

    risk_videos = sorted(
        video_items,
        key=lambda x: (x["metrics"]["risk_rate"], x["metrics"]["risk_count"]),
        reverse=True,
    )[:limit]
    highlight_videos = sorted(
        video_items,
        key=lambda x: (x["metrics"]["highlight_rate"], x["metrics"]["highlight_count"]),
        reverse=True,
    )[:limit]

    response = {
        "window": {
            "days": days,
            "start_at": isoformat_in_app_tz(start_time),
            "end_at": isoformat_in_app_tz(end_time),
        },
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
        "distribution": {"score_buckets": score_buckets},
        "quality": {
            "highlight_count": highlight_total,
            "high_quality_count": score_buckets.get("80_100", 0),
            "low_quality_count": low_quality_total,
            "avg_score": avg_score,
        },
        "risk": {"risk_count": risk_total, "severe_risk_count": severe_total},
        "sources": {"distribution": source_counts, "coverage_rate": ai_coverage_rate},
        "actions": actions,
        "ablation": _module_flags(),
        "thresholds": thresholds,
        "videos": {"risk": risk_videos, "highlight": highlight_videos},
        "computed_at": isoformat_in_app_tz(end_time),
    }

    return success_response(data=response)


@router.post("/correct", response_model=CorrectionResponse, summary="提交AI修正记录 (Frontend Alias)")
async def submit_correction(
    correction_in: CorrectionCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Frontend alias for create_correction"""
    return await create_correction(correction_in, current_admin, db)


@router.get("/corrections", summary="获取修正记录列表")
async def get_corrections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    content_type: Optional[str] = Query(None, description="内容类型过滤"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """获取AI修正记录列表"""
    try:
        query = db.query(AiCorrection)
        
        if content_type:
            query = query.filter(AiCorrection.content_type == content_type)
        
        total = query.count()
        offset = (page - 1) * page_size
        
        corrections = (
            query.order_by(AiCorrection.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        items = [CorrectionResponse.model_validate(item).model_dump() for item in corrections]
        payload = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size),
        }
        return success_response(data=jsonable_encoder(payload))

    except SQLAlchemyError as e:
        logger.error(f"获取修正记录失败: {e}", exc_info=True)
        payload = {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
        }
        return success_response(data=jsonable_encoder(payload), message="修正记录查询失败，已返回空数据")
    except Exception as e:
        logger.error(f"获取修正记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取修正记录失败")


@router.post("/self-correction/analyze", summary="触发自我纠错分析")
@handle_api_errors(default_message="自我纠错分析失败")
async def trigger_self_correction_analysis(
    request: ErrorAnalysisRequest,
    current_admin: User = Depends(get_current_admin)
):
    """触发AI自我纠错分析"""
    logger.info(f"管理员 {current_admin.username} 触发自我纠错分析")
    
    result = await self_correction_service.analyze_errors(
        days=request.days,
        content_type=request.content_type
    )
    
    return result


@router.post("/self-correction/update-prompt", response_model=MessageResponse, summary="更新System Prompt")
async def update_system_prompt(
    request: PromptUpdateRequest,
    current_admin: User = Depends(get_current_admin)
):
    """应用优化建议，更新System Prompt"""
    try:
        success = await self_correction_service.update_system_prompt(
            prompt_type=request.prompt_type,
            new_prompt=request.new_prompt,
            update_reason=request.update_reason,
            updated_by=current_admin.id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Prompt更新失败")
        
        logger.info(f"管理员 {current_admin.username} 更新了 {request.prompt_type} Prompt")
        
        return MessageResponse(
            message=f"System Prompt已更新并记录版本历史。注意：需要手动更新prompts.py文件以生效。"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新System Prompt失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/prompt-versions", summary="获取Prompt版本历史")
async def get_prompt_versions(
    prompt_type: Optional[str] = Query(None, description="Prompt类型过滤"),
    limit: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin)
):
    """查询Prompt版本历史"""
    try:
        versions = self_correction_service.get_prompt_history(
            prompt_type=prompt_type,
            limit=limit
        )
        
        return {
            "items": versions,
            "total": len(versions)
        }
        
    except Exception as e:
        logger.error(f"获取Prompt版本历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取版本历史失败")


@router.post("/prompts/create-draft", summary="创建草案Prompt版本")
async def create_draft_prompt(
    request: PromptCreateDraftRequest,
    current_admin: User = Depends(get_current_admin)
):
    """将自纠错分析结果保存为草案版本"""
    try:
        version_id = await self_correction_service.create_draft_version(
            prompt_type=request.prompt_type,
            draft_content=request.draft_content,
            sample_ids=request.sample_ids,
            risk_notes=request.risk_notes,
            expected_impact=request.expected_impact,
            created_by=current_admin.id
        )
        
        if not version_id:
            raise HTTPException(status_code=500, detail="创建草案版本失败")
        
        logger.info(f"管理员 {current_admin.username} 创建了草案Prompt版本 {version_id}")
        
        return success_response(
            data={"version_id": version_id},
            message="草案版本已创建"
        )
        
    except Exception as e:
        logger.error(f"创建草案Prompt失败: {e}")
        raise HTTPException(status_code=500, detail="创建草案失败")


@router.post("/prompts/publish", summary="发布Prompt版本")
async def publish_prompt(
    request: PromptPublishRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """发布候选Prompt版本为激活版本"""
    try:
        from app.models.ai_prompt_version import AiPromptVersion
        
        # 查找候选版本
        candidate = db.query(AiPromptVersion).filter(
            AiPromptVersion.id == request.version_id
        ).first()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="候选版本不存在")
        
        # 取消同类型的其他激活版本
        db.query(AiPromptVersion).filter(
            AiPromptVersion.prompt_type == candidate.prompt_type,
            AiPromptVersion.is_active == True
        ).update({"is_active": False})
        
        # 激活候选版本
        candidate.is_active = True
        candidate.updated_by = current_admin.id
        
        db.commit()
        
        logger.info(f"管理员 {current_admin.username} 发布了 {candidate.prompt_type} Prompt 版本 {candidate.id}")
        
        return success_response(
            data={"version_id": candidate.id, "prompt_type": candidate.prompt_type},
            message="Prompt版本已发布"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发布Prompt版本失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="发布失败")


@router.post("/prompts/shadow-test", summary="Shadow测试Prompt版本")
async def shadow_test_prompt(
    request: PromptShadowTestRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """使用修正样本对比测试候选版本与当前激活版本"""
    try:
        result = await prompt_workflow_service.run_prompt_test(
            db=db,
            candidate_version_id=request.candidate_version_id,
            sample_limit=request.sample_limit,
            model_source=request.model_source,
            dataset_source=request.dataset_source,
            task_id=request.task_id,
            admin_id=current_admin.id,
            save_experiment=request.save_experiment,
        )

        logger.info(
            "管理员 %s 执行了 Shadow 测试: 候选版本 %s",
            current_admin.username,
            request.candidate_version_id,
        )

        return success_response(
            data=result,
            message="Shadow测试完成"
        )

    except ValueError as e:
        logger.warning(f"Shadow测试失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Shadow测试失败: {e}")
        raise HTTPException(status_code=500, detail="测试失败")


@router.get("/prompt-workflow/tasks", summary="获取Prompt工作流任务")
async def get_prompt_workflow_tasks(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取或初始化Prompt工作流任务"""
    tasks = prompt_workflow_service.ensure_default_tasks(db, current_admin.id)
    items = [
        {
            "id": t.id,
            "name": t.name,
            "prompt_type": t.prompt_type,
            "goal": t.goal,
            "metrics": t.metrics or {},
            "dataset_source": t.dataset_source,
            "sample_min": t.sample_min,
            "is_active": t.is_active,
            "created_at": isoformat_in_app_tz(t.created_at),
            "updated_at": isoformat_in_app_tz(t.updated_at),
        }
        for t in tasks
    ]
    return success_response(data={"items": items, "total": len(items)})


@router.post("/prompt-workflow/tasks", summary="创建Prompt工作流任务")
async def create_prompt_workflow_task(
    request: PromptTaskCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    task = AiPromptTask(
        name=request.name,
        prompt_type=request.prompt_type,
        goal=request.goal,
        metrics=request.metrics,
        dataset_source=request.dataset_source,
        sample_min=request.sample_min,
        is_active=request.is_active,
        created_by=current_admin.id,
        updated_by=current_admin.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return success_response(
        data={
            "id": task.id,
            "name": task.name,
            "prompt_type": task.prompt_type,
            "goal": task.goal,
            "metrics": task.metrics or {},
            "dataset_source": task.dataset_source,
            "sample_min": task.sample_min,
            "is_active": task.is_active,
            "created_at": isoformat_in_app_tz(task.created_at),
            "updated_at": isoformat_in_app_tz(task.updated_at),
        },
        message="任务已创建"
    )


@router.put("/prompt-workflow/tasks/{task_id}", summary="更新Prompt工作流任务")
async def update_prompt_workflow_task(
    task_id: int,
    request: PromptTaskUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    task = db.query(AiPromptTask).filter(AiPromptTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if request.name is not None:
        task.name = request.name
    if request.goal is not None:
        task.goal = request.goal
    if request.metrics is not None:
        task.metrics = request.metrics
    if request.dataset_source is not None:
        task.dataset_source = request.dataset_source
    if request.sample_min is not None:
        task.sample_min = request.sample_min
    if request.is_active is not None:
        task.is_active = request.is_active

    task.updated_by = current_admin.id
    db.commit()
    db.refresh(task)
    return success_response(
        data={
            "id": task.id,
            "name": task.name,
            "prompt_type": task.prompt_type,
            "goal": task.goal,
            "metrics": task.metrics or {},
            "dataset_source": task.dataset_source,
            "sample_min": task.sample_min,
            "is_active": task.is_active,
            "created_at": isoformat_in_app_tz(task.created_at),
            "updated_at": isoformat_in_app_tz(task.updated_at),
        },
        message="任务已更新"
    )


@router.post("/prompt-workflow/test", summary="运行Prompt工作流测试")
async def run_prompt_workflow_test(
    request: PromptShadowTestRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """运行Prompt测试并返回评估结果"""
    try:
        result = await prompt_workflow_service.run_prompt_test(
            db=db,
            candidate_version_id=request.candidate_version_id,
            sample_limit=request.sample_limit,
            model_source=request.model_source,
            dataset_source=request.dataset_source,
            task_id=request.task_id,
            admin_id=current_admin.id,
            save_experiment=request.save_experiment,
        )
        return success_response(data=result, message="测试完成")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/prompt-workflow/experiments", summary="获取Prompt工作流实验列表")
async def get_prompt_workflow_experiments(
    task_id: Optional[int] = Query(None),
    prompt_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(AiPromptExperiment)
    if task_id:
        query = query.filter(AiPromptExperiment.task_id == task_id)
    if prompt_type:
        query = query.filter(AiPromptExperiment.prompt_type == prompt_type)

    experiments = query.order_by(AiPromptExperiment.created_at.desc()).limit(limit).all()
    items = [
        {
            "id": exp.id,
            "task_id": exp.task_id,
            "prompt_type": exp.prompt_type,
            "candidate_version_id": exp.candidate_version_id,
            "active_version_id": exp.active_version_id,
            "model_source": exp.model_source,
            "dataset_source": exp.dataset_source,
            "sample_limit": exp.sample_limit,
            "sample_count": exp.sample_count,
            "status": exp.status,
            "metrics": exp.metrics or {},
            "created_at": isoformat_in_app_tz(exp.created_at),
        }
        for exp in experiments
    ]
    return success_response(data={"items": items, "total": len(items)})


@router.get("/prompt-workflow/experiments/{experiment_id}", summary="获取Prompt工作流实验详情")
async def get_prompt_workflow_experiment_detail(
    experiment_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    experiment = db.query(AiPromptExperiment).filter(AiPromptExperiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")

    return success_response(
        data={
            "id": experiment.id,
            "task_id": experiment.task_id,
            "prompt_type": experiment.prompt_type,
            "candidate_version_id": experiment.candidate_version_id,
            "active_version_id": experiment.active_version_id,
            "model_source": experiment.model_source,
            "dataset_source": experiment.dataset_source,
            "sample_limit": experiment.sample_limit,
            "sample_count": experiment.sample_count,
            "status": experiment.status,
            "metrics": experiment.metrics or {},
            "sample_details": experiment.sample_details or [],
            "created_at": isoformat_in_app_tz(experiment.created_at),
        }
    )


@router.get("/prompts/versions", summary="获取Prompt版本列表")
async def get_prompt_versions(
    prompt_type: Optional[str] = Query(None, description="Prompt类型过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取Prompt版本列表"""
    try:
        from app.models.ai_prompt_version import AiPromptVersion
        
        query = db.query(AiPromptVersion)
        
        if prompt_type:
            query = query.filter(AiPromptVersion.prompt_type == prompt_type)
        
        total = query.count()
        offset = (page - 1) * page_size
        
        versions = (
            query.order_by(AiPromptVersion.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        return success_response(
            data={
                "items": [
                    {
                        "id": v.id,
                        "prompt_type": v.prompt_type,
                        "prompt_content": v.prompt_content[:200] + "..." if len(v.prompt_content) > 200 else v.prompt_content,
                        "update_reason": v.update_reason,
                        "is_active": v.is_active,
                        "created_at": isoformat_in_app_tz(v.created_at),
                        "updated_by": v.updated_by
                    } for v in versions
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": math.ceil(total / page_size)
            }
        )
        
    except Exception as e:
        logger.error(f"获取Prompt版本列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取版本列表失败")
async def rollback_prompt(
    request: PromptRollbackRequest,
    current_admin: User = Depends(get_current_admin)
):
    """回滚到指定Prompt版本"""
    try:
        success = await self_correction_service.rollback_prompt(
            version_id=request.version_id,
            rollback_by=current_admin.id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="版本不存在或回滚失败")
        
        logger.info(
            f"[Admin] 管理员 {current_admin.username} 回滚Prompt到版本 {request.version_id}"
        )
        
        return {"message": "Prompt 已回滚"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] 回滚Prompt失败: {e}")
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


@router.get("/config", summary="获取AI系统配置")
async def get_ai_config(
    current_admin: User = Depends(get_current_admin)
):
    """获取AI系统当前配置"""
    mode = getattr(settings, "LLM_MODE", "hybrid").lower()
    return {
        "local_llm": {
            "enabled": mode in ("local_only", "hybrid"),
            "model": settings.LOCAL_LLM_MODEL,
            "threshold_high": settings.LOCAL_LLM_THRESHOLD_HIGH,
            "threshold_low": settings.LOCAL_LLM_THRESHOLD_LOW
        },
        "multi_agent": {
            "enabled": settings.MULTI_AGENT_ENABLED,
            "conflict_threshold": settings.MULTI_AGENT_CONFLICT_THRESHOLD
        },
        "self_correction": {
            "enabled": settings.SELF_CORRECTION_ENABLED,
            "min_samples": settings.SELF_CORRECTION_MIN_SAMPLES,
            "auto_update": settings.SELF_CORRECTION_AUTO_UPDATE,
            "analysis_days": settings.SELF_CORRECTION_ANALYSIS_DAYS
        }
    }
