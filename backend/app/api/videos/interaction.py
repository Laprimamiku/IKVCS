"""
视频互动 API

功能：
1. 点赞/取消点赞视频
2. 收藏/取消收藏视频
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException
from app.models.user import User
from app.models.video import Video

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{video_id}/like", response_model=dict)
async def like_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    点赞/取消点赞视频（RESTful 风格路由）
    
    如果已点赞则取消点赞，如果未点赞则点赞
    立即同步更新数据库的 like_count 字段
    """
    from app.services.cache.redis_service import redis_service
    
    # 检查视频是否存在
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 检查是否已点赞
    key = f"likes:video:{video_id}"
    is_liked = redis_service.redis.sismember(key, current_user.id)
    
    if is_liked:
        # 取消点赞
        await redis_service.remove_like(current_user.id, "video", video_id)
        count = await redis_service.get_like_count("video", video_id)
        
        # 立即同步更新数据库的 like_count
        video.like_count = count
        db.commit()
        
        return {"is_liked": False, "like_count": count}
    else:
        # 点赞
        await redis_service.add_like(current_user.id, "video", video_id)
        count = await redis_service.get_like_count("video", video_id)
        
        # 立即同步更新数据库的 like_count
        video.like_count = count
        db.commit()
        
        return {"is_liked": True, "like_count": count}


@router.post("/{video_id}/collect", response_model=dict)
async def collect_video(
    video_id: int,
    request_data: dict = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    收藏/取消收藏视频（RESTful 风格路由）
    
    如果已收藏则取消收藏，如果未收藏则收藏到指定文件夹（folder_id 为 None 表示未分类）
    
    参数：
    - video_id: 视频ID
    - request_data: 请求体，包含 folder_id（可选，None 表示未分类）
    """
    from app.models.interaction import UserCollection
    
    # 从请求体获取 folder_id
    folder_id = None
    if request_data:
        folder_id = request_data.get('folder_id')
    
    # 如果提供了 folder_id，验证文件夹是否存在且属于当前用户
    if folder_id is not None:
        from app.models.collection_folder import CollectionFolder
        folder = db.query(CollectionFolder).filter(
            CollectionFolder.id == folder_id,
            CollectionFolder.user_id == current_user.id
        ).first()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
    
    # 检查是否已收藏
    exists = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id,
        UserCollection.video_id == video_id
    ).first()
    
    if exists:
        # 取消收藏
        db.delete(exists)
        db.query(Video).filter(Video.id == video_id).update(
            {Video.collect_count: Video.collect_count - 1}
        )
        db.commit()
        # 获取最新收藏数
        video = db.query(Video).filter(Video.id == video_id).first()
        return {"is_collected": False, "collect_count": video.collect_count if video else 0}
    else:
        # 如果 folder_id 为 None，自动创建或获取"默认收藏夹"
        if folder_id is None:
            from app.models.collection_folder import CollectionFolder
            default_folder = db.query(CollectionFolder).filter(
                CollectionFolder.user_id == current_user.id,
                CollectionFolder.name == "默认收藏夹"
            ).first()
            
            if not default_folder:
                # 创建默认收藏夹
                default_folder = CollectionFolder(
                    user_id=current_user.id,
                    name="默认收藏夹",
                    description="系统自动创建的默认收藏夹"
                )
                db.add(default_folder)
                db.commit()
                db.refresh(default_folder)
            
            folder_id = default_folder.id
        
        # 收藏到指定文件夹
        new_collection = UserCollection(
            user_id=current_user.id, 
            video_id=video_id,
            folder_id=folder_id
        )
        db.add(new_collection)
        db.query(Video).filter(Video.id == video_id).update(
            {Video.collect_count: Video.collect_count + 1}
        )
        db.commit()
        # 获取最新收藏数
        video = db.query(Video).filter(Video.id == video_id).first()
        return {"is_collected": True, "collect_count": video.collect_count if video else 0}

