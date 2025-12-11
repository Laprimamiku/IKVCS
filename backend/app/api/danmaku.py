"""
弹幕 API
需求：7.1, 7.2, 7.3, 7.4, 7.5
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.danmaku import Danmaku
from app.services.redis_service import RedisService

router = APIRouter()
redis_service = RedisService()

# ==================== Pydantic Schemas ====================

class DanmakuCreate(BaseModel):
    content: str
    video_time: float
    color: str = "#FFFFFF"

class DanmakuResponse(BaseModel):
    id: int
    video_id: int
    user_id: int
    content: str
    video_time: float
    color: str
    created_at: datetime
    # 暂时不返回 AI 分分，除非是管理员接口

    class Config:
        from_attributes = True

# ==================== API Endpoints ====================

# 模拟 LLM 分析任务
async def analyze_danmaku_content(danmaku_id: int):
    """后台任务：调用 LLM 分析弹幕内容"""
    # TODO: 实现真正的 LLM 调用
    # 1. 获取弹幕内容
    # 2. 调用 LLMService
    # 3. 更新数据库中的 ai_score 和 ai_category
    pass

@router.post("/videos/{video_id}/danmakus", response_model=DanmakuResponse)
async def send_danmaku(
    video_id: int,
    danmaku_in: DanmakuCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    发送弹幕
    1. 保存到 MySQL
    2. 发布到 Redis (触发 WebSocket 广播)
    3. 触发 AI 异步分析
    """
    # 1. 保存到数据库
    db_danmaku = Danmaku(
        video_id=video_id,
        user_id=current_user.id,
        content=danmaku_in.content,
        video_time=danmaku_in.video_time,
        color=danmaku_in.color
    )
    db.add(db_danmaku)
    db.commit()
    db.refresh(db_danmaku)
    
    # 2. 构造消息并发布到 Redis
    # 注意：发送给前端的数据结构应与前端播放器要求一致
    message = {
        "id": db_danmaku.id,
        "text": db_danmaku.content,
        "time": db_danmaku.video_time,
        "color": db_danmaku.color,
        "user_id": current_user.id,
        "is_me": False # 前端接收时判断
    }
    
    await redis_service.publish_danmaku(video_id, message)
    
    # 3. 触发后台 AI 分析任务
    background_tasks.add_task(analyze_danmaku_content, db_danmaku.id)
    
    return db_danmaku

@router.get("/videos/{video_id}/danmakus", response_model=List[DanmakuResponse])
def get_danmakus(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    获取视频的历史弹幕
    """
    # 简单的全量获取，实际生产中可能需要按时间段分片获取或限制数量
    danmakus = db.query(Danmaku).filter(
        Danmaku.video_id == video_id,
        Danmaku.is_deleted == False
    ).order_by(Danmaku.video_time).all()
    
    return danmakus