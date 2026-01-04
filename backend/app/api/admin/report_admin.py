"""
举报管理 API（管理员）
功能：举报列表、处理举报
"""
import math
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.schemas.user import UserResponse, MessageResponse
from app.services.admin.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportHandleRequest(BaseModel):
    action: str  # delete_target | ignore
    admin_note: Optional[str] = None


class ReportItemResponse(BaseModel):
    id: int
    target_type: str
    target_id: int
    reason: str
    description: Optional[str]
    status: int
    created_at: datetime
    reporter: UserResponse

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    items: list[ReportItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/reports", response_model=ReportListResponse, summary="获取举报列表")
async def get_reports(
    status: int = Query(0, description="0=待处理,1=已处理,2=已忽略"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取举报列表"""
    reports, total = AdminService.get_reports(db, status, page, page_size)
    
    return {
        "items": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


@router.post("/reports/{report_id}/handle", response_model=MessageResponse, summary="处理举报")
async def handle_report(
    data: ReportHandleRequest,
    report_id: int = Path(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """处理举报"""
    AdminService.handle_report(
        db, report_id, data.action, admin.id, data.admin_note
    )
    
    return {"message": "举报已处理"}

