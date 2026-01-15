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
from app.core.app_constants import DEFAULT_PAGE_SIZE
from app.models.user import User
from app.schemas.user import UserResponse, MessageResponse
from app.services.admin.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportHandleRequest(BaseModel):
    action: str  # delete_target | ignore | disable | request_review
    admin_note: Optional[str] = None


class TargetSnapshotVideo(BaseModel):
    """视频目标快照"""
    id: int
    title: str
    cover_url: Optional[str]
    video_url: Optional[str]
    uploader: Optional[dict]
    status: int
    review_status: int
    created_at: Optional[str]


class TargetSnapshotComment(BaseModel):
    """评论目标快照"""
    id: int
    content: str
    video_id: int
    user: Optional[dict]
    created_at: Optional[str]


class TargetSnapshotDanmaku(BaseModel):
    """弹幕目标快照"""
    id: int
    content: str
    video_id: int
    video_time: float
    user: Optional[dict]
    created_at: Optional[str]


class ReportItemResponse(BaseModel):
    id: int
    target_type: str
    target_id: int
    reason: str
    description: Optional[str]
    status: int
    created_at: datetime
    reporter: UserResponse
    target_snapshot: Optional[dict] = None  # 目标内容快照（视频/评论/弹幕）
    admin_target_url: Optional[str] = None  # 管理端跳转链接
    public_watch_url: Optional[str] = None  # 公开访问链接

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    items: list[ReportItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=ReportListResponse, summary="获取举报列表")
async def get_reports(
    status: int = Query(0, description="0=待处理,1=已处理,2=已忽略"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取举报列表（包含目标内容预览）"""
    response_data = AdminService.get_reports_response(db, status, page, page_size)
    
    # 转换为 Pydantic 模型
    items = [ReportItemResponse(**item) for item in response_data["items"]]
    
    return ReportListResponse(
        items=items,
        total=response_data["total"],
        page=response_data["page"],
        page_size=response_data["page_size"],
        total_pages=response_data["total_pages"]
    )


@router.post("/{report_id}/handle", response_model=MessageResponse, summary="处理举报")
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

