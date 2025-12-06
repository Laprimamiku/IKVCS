"""
视频管理 API

这个文件的作用：
1. 获取视频列表（GET /api/v1/videos）
2. 获取视频详情（GET /api/v1/videos/{video_id}）
3. 测试转码功能（POST /api/v1/videos/{video_id}/transcode）- 仅用于测试

类比 Java：
    相当于 Spring Boot 的 VideoController
    
需求：5.1-5.5
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.video import Video
from pydantic import BaseModel

router = APIRouter()


class VideoStatusResponse(BaseModel):
    """视频状态响应"""
    video_id: int
    title: str
    status: int
    status_text: str
    video_url: Optional[str]
    duration: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": 1,
                "title": "测试视频",
                "status": 1,
                "status_text": "审核中",
                "video_url": "/videos/hls/1/master.m3u8",
                "duration": 120
            }
        }


class TranscodeTestRequest(BaseModel):
    """转码测试请求"""
    video_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": 1
            }
        }


class TranscodeTestResponse(BaseModel):
    """转码测试响应"""
    message: str
    video_id: int
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "转码任务已启动",
                "video_id": 1,
                "status": "transcoding"
            }
        }


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取视频状态
    
    用于测试：查看视频转码状态
    
    状态说明：
    - 0: 转码中
    - 1: 审核中
    - 2: 已发布
    - 3: 已拒绝
    - -1: 转码失败
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视频 {video_id} 不存在"
        )
    
    # 状态文本映射
    status_map = {
        0: "转码中",
        1: "审核中",
        2: "已发布",
        3: "已拒绝",
        -1: "转码失败"
    }
    
    return VideoStatusResponse(
        video_id=video.id,
        title=video.title,
        status=video.status,
        status_text=status_map.get(video.status, "未知状态"),
        video_url=video.video_url,
        duration=video.duration
    )


@router.post("/{video_id}/transcode", response_model=TranscodeTestResponse)
async def test_transcode(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试转码功能（仅用于开发测试）
    
    ⚠️ 注意：这个接口仅用于测试转码功能
    正常流程中，转码会在上传完成后自动触发
    
    使用场景：
    1. 测试转码功能是否正常
    2. 重新转码失败的视频
    3. 开发调试
    
    前提条件：
    - 视频必须已经上传完成（有对应的 upload_session）
    - 原始视频文件必须存在
    
    测试步骤：
    1. 先完成视频上传（调用 /api/v1/upload/finish）
    2. 获取返回的 video_id
    3. 调用此接口触发转码
    4. 轮询 /api/v1/videos/{video_id}/status 查看转码状态
    """
    # 检查视频是否存在
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视频 {video_id} 不存在"
        )
    
    # 检查是否有对应的上传会话
    from app.models.upload import UploadSession
    upload_session = db.query(UploadSession).filter(
        UploadSession.video_id == video_id
    ).first()
    
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"视频 {video_id} 没有对应的上传会话，无法转码"
        )
    
    # 更新视频状态为转码中
    video.status = 0
    db.commit()
    
    # 触发转码任务
    from app.services.transcode_service import TranscodeService
    background_tasks.add_task(TranscodeService.transcode_video, video_id)
    
    return TranscodeTestResponse(
        message="转码任务已启动，请稍后查询视频状态",
        video_id=video_id,
        status="transcoding"
    )
