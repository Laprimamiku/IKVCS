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
from app.services.cache.redis_service import RedisService
from app.services.ai.llm_service import llm_service  # <--- 导入新写的服务
from app.schemas.danmaku import DanmakuCreateRequest, DanmakuResponse as DanmakuResponseSchema

router = APIRouter()
redis_service = RedisService()

# ==================== Pydantic Schemas ====================

# 使用 schema 层的定义
DanmakuCreate = DanmakuCreateRequest
DanmakuResponse = DanmakuResponseSchema

# ==================== API Endpoints ====================

# 注意：LLM 分析任务已由 llm_service.process_danmaku_task 实现
# 此函数已废弃，保留仅为向后兼容

@router.post("/videos/{video_id}/danmakus", response_model=DanmakuResponse)
async def send_danmaku(
    video_id: int,
    danmaku_in: DanmakuCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    发送弹幕：保存 -> 广播 -> 触发AI分析
    1. 保存到 MySQL
    2. 发布到 Redis (触发 WebSocket 广播)
    3. 触发 AI 异步分析
    """
    # 调用 Service 层处理弹幕创建逻辑
    from app.services.danmaku.danmaku_service import DanmakuService
    
    db_danmaku = DanmakuService.create_danmaku(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        danmaku_data=danmaku_in
    )
    
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
    background_tasks.add_task(llm_service.process_danmaku_task, db_danmaku.id)
    
    return db_danmaku

@router.get("/videos/{video_id}/danmakus", response_model=List[DanmakuResponse])
async def get_danmakus(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    获取视频的历史弹幕
    """
    # 调用 Service 层处理弹幕查询逻辑
    from app.services.danmaku.danmaku_service import DanmakuService
    
    danmakus = DanmakuService.get_danmaku_list(db, video_id)
    return danmakus


@router.post("/videos/{video_id}/danmakus/{danmaku_id}/like", response_model=dict)
async def like_danmaku(
    video_id: int,
    danmaku_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    点赞/取消点赞弹幕（RESTful 风格路由）
    
    如果已点赞则取消点赞，如果未点赞则点赞
    使用 Redis 存储点赞状态，不更新数据库（保持轻量）
    """
    from app.services.cache.redis_service import redis_service
    
    # 调用 Service 层检查弹幕是否存在
    from app.services.danmaku.danmaku_service import DanmakuService
    
    danmaku = DanmakuService.get_danmaku_by_id(db, danmaku_id, video_id)
    if not danmaku:
        raise HTTPException(status_code=404, detail="弹幕不存在")
    
    # 检查是否已点赞
    key = f"likes:danmaku:{danmaku_id}"
    is_liked = redis_service.redis.sismember(key, current_user.id)
    
    if is_liked:
        # 取消点赞
        await redis_service.remove_like(current_user.id, "danmaku", danmaku_id)
        count = await redis_service.get_like_count("danmaku", danmaku_id)
        return {"is_liked": False, "like_count": count}
    else:
        # 点赞
        await redis_service.add_like(current_user.id, "danmaku", danmaku_id)
        count = await redis_service.get_like_count("danmaku", danmaku_id)
        return {"is_liked": True, "like_count": count}