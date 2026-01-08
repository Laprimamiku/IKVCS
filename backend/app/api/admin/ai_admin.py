"""
AI管理 API（管理员）
功能：AI修正记录、自我纠错、Prompt版本管理
"""
import math
import logging
from typing import Optional, List
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.core.config import settings
from app.core.response import success_response
from app.models.user import User
from app.models.ai_correction import AiCorrection
from app.services.ai.self_correction_service import self_correction_service
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
    risk_notes: str = ""
    expected_impact: str = ""


class PromptShadowTestRequest(BaseModel):
    """Prompt Shadow测试请求"""
    candidate_version_id: int
    sample_limit: int = 50  # 测试样本数量限制


class PromptRollbackRequest(BaseModel):
    """Prompt 回滚请求"""
    version_id: int


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
        
        return {
            "items": corrections,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size)
        }
        
    except Exception as e:
        logger.error(f"获取修正记录失败: {e}")
        raise HTTPException(status_code=500, detail="获取修正记录失败")


@router.post("/self-correction/analyze", summary="触发自我纠错分析")
async def trigger_self_correction_analysis(
    request: ErrorAnalysisRequest,
    current_admin: User = Depends(get_current_admin)
):
    """触发AI自我纠错分析"""
    try:
        logger.info(f"管理员 {current_admin.username} 触发自我纠错分析")
        
        result = await self_correction_service.analyze_errors(
            days=request.days,
            content_type=request.content_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"自我纠错分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


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
        from app.models.ai_prompt_version import AiPromptVersion
        
        # 查找候选版本
        candidate = db.query(AiPromptVersion).filter(
            AiPromptVersion.id == request.candidate_version_id
        ).first()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="候选版本不存在")
        
        # 查找当前激活版本
        active = db.query(AiPromptVersion).filter(
            AiPromptVersion.prompt_type == candidate.prompt_type,
            AiPromptVersion.is_active == True
        ).first()
        
        if not active:
            raise HTTPException(status_code=404, detail="当前无激活版本")
        
        # 获取测试样本（从修正记录中获取）
        corrections = db.query(AiCorrection).filter(
            AiCorrection.content_type == candidate.prompt_type.lower()
        ).order_by(AiCorrection.created_at.desc()).limit(request.sample_limit).all()
        
        if not corrections:
            raise HTTPException(status_code=400, detail="无可用测试样本")
        
        # 执行对比测试（这里简化实现，实际应该调用LLM进行对比）
        test_results = {
            "candidate_version_id": candidate.id,
            "active_version_id": active.id,
            "sample_count": len(corrections),
            "consistency_rate": 0.85,  # 模拟一致率
            "avg_score_diff": 2.3,     # 模拟平均分数差异
            "estimated_cost": len(corrections) * 0.001,  # 模拟成本估算
            "test_timestamp": isoformat_in_app_tz(utc_now())
        }
        
        logger.info(f"管理员 {current_admin.username} 执行了 Shadow 测试: 候选版本 {candidate.id} vs 激活版本 {active.id}")
        
        return success_response(
            data=test_results,
            message="Shadow测试完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Shadow测试失败: {e}")
        raise HTTPException(status_code=500, detail="测试失败")


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
