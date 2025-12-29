"""
评论 API
需求：9.1, 9.2, 9.3, 10.1, 10.2
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.common import PageResult
from app.services.comment.comment_service import CommentService
from app.services.ai.llm_service import llm_service  # 导入 LLM 服务

router = APIRouter()

@router.post("/videos/{video_id}/comments", response_model=CommentResponse)
async def create_comment(
    video_id: int,
    comment_in: CommentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    发表评论 (支持根评论和回复)
    并触发 AI 智能分析
    """
    # 调用 Service 层处理评论创建逻辑
    new_comment = CommentService.create_comment(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        comment_data=comment_in
    )
    
    # 3. 🚀 触发 AI 异步分析任务 (核心集成点)
    # 这会调用我们之前写的 process_comment_task，更新 ai_score 和 ai_label
    background_tasks.add_task(llm_service.process_comment_task, new_comment.id)
    
    return new_comment

@router.get("/videos/{video_id}/comments", response_model=PageResult[CommentResponse])
def list_comments(
    video_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("new", regex="^(new|hot)$"),
    db: Session = Depends(get_db)
):
    """
    获取视频评论列表 (仅一级评论)
    """
    # 调用 Service 层处理评论查询逻辑
    items, total = CommentService.get_comment_list(
        db=db,
        video_id=video_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        parent_id=None  # 只查根评论
    )
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/comments/{comment_id}/replies", response_model=PageResult[CommentResponse])
def list_replies(
    comment_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    获取某条评论的子回复
    """
    # 先查一下父评论，确认视频ID
    parent = CommentService.get_comment_by_id(db, comment_id)
    if not parent:
        raise HTTPException(status_code=404, detail="评论不存在")
        
    # 调用 Service 层处理回复查询逻辑
    items, total = CommentService.get_comment_list(
        db=db,
        video_id=parent.video_id,
        page=page,
        page_size=page_size,
        sort_by="new",
        parent_id=comment_id
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除评论 (软删除)
    """
    comment = CommentService.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    # 权限检查：只有作者或管理员可以删除 (此处简化为只检查作者)
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该评论")
        
    CommentService.delete_comment(db, comment_id)
    
    return {"success": True, "message": "评论已删除"}


@router.post("/comments/{comment_id}/like", response_model=dict)
async def like_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    点赞/取消点赞评论（RESTful 风格路由）
    
    如果已点赞则取消点赞，如果未点赞则点赞
    立即同步更新数据库的 like_count 字段
    """
    from app.services.cache.redis_service import redis_service
    
    # 检查评论是否存在
    comment = CommentService.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    # 检查是否已点赞
    key = f"likes:comment:{comment_id}"
    is_liked = redis_service.redis.sismember(key, current_user.id)
    
    if is_liked:
        # 取消点赞
        await redis_service.remove_like(current_user.id, "comment", comment_id)
        count = await redis_service.get_like_count("comment", comment_id)
        
        # 立即同步更新数据库的 like_count
        comment.like_count = count
        db.commit()
        
        return {"is_liked": False, "like_count": count}
    else:
        # 点赞
        await redis_service.add_like(current_user.id, "comment", comment_id)
        count = await redis_service.get_like_count("comment", comment_id)
        
        # 立即同步更新数据库的 like_count
        comment.like_count = count
        db.commit()
        
        return {"is_liked": True, "like_count": count}