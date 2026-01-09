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
    page_size: int = Query(20, ge=1),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取举报列表（包含目标内容预览）"""
    reports, total = AdminService.get_reports(db, status, page, page_size)
    
    # 构建响应项，添加跳转链接
    items = []
    for report in reports:
        # 构建管理端和公开访问链接
        admin_target_url = None
        public_watch_url = None
        
        if report.target_type == "VIDEO":
            admin_target_url = f"/admin/videos/{report.target_id}"
            public_watch_url = f"/videos/{report.target_id}"
        elif report.target_type == "COMMENT":
            snapshot = getattr(report, 'target_snapshot', None)
            if snapshot and 'video_id' in snapshot:
                admin_target_url = f"/admin/videos/{snapshot['video_id']}"
                public_watch_url = f"/videos/{snapshot['video_id']}"
        elif report.target_type == "DANMAKU":
            snapshot = getattr(report, 'target_snapshot', None)
            if snapshot and 'video_id' in snapshot:
                admin_target_url = f"/admin/videos/{snapshot['video_id']}"
                public_watch_url = f"/videos/{snapshot['video_id']}"
        
        # 构建响应项
        item_dict = {
            "id": report.id,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "reason": report.reason,
            "description": report.description,
            "status": report.status,
            "created_at": report.created_at,
            "reporter": report.reporter,
            "target_snapshot": getattr(report, 'target_snapshot', None),
            "admin_target_url": admin_target_url,
            "public_watch_url": public_watch_url
        }
        items.append(ReportItemResponse(**item_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


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

