"""
AI管理 API（管理员）
功能：AI修正记录、自我纠错、Prompt版本管理
"""
import math
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.core.config import settings
from app.models.user import User
from app.models.ai_correction import AiCorrection
from app.services.ai.self_correction_service import self_correction_service
from app.schemas.user import MessageResponse

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


class PromptRollbackRequest(BaseModel):
    """Prompt 回滚请求"""
    version_id: int


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


@router.post("/prompts/rollback", summary="回滚Prompt版本")
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
    return {
        "local_llm": {
            "enabled": settings.LOCAL_LLM_ENABLED,
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

