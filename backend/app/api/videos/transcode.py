"""
视频转码 API（开发调试专用）

功能：
1. 触发转码（开发/调试专用接口）
"""
import logging
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.video import TranscodeTestResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{video_id}/transcode", response_model=TranscodeTestResponse)
async def test_transcode(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    触发转码（开发/调试专用接口）
    
    注意：此接口仅用于开发和调试，生产环境应通过上传流程自动触发转码
    """
    # 仅在开发环境允许使用此接口
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此接口仅在开发环境可用"
        )
    
    from app.services.video.video_status_service import VideoStatusService
    from app.services.transcode import TranscodeService
    
    # 调用 Service 层处理转码触发逻辑
    status_info = VideoStatusService.trigger_transcode(db, video_id)
    
    # 启动后台转码任务
    background_tasks.add_task(TranscodeService.transcode_video, video_id)
    
    return TranscodeTestResponse(**status_info)

