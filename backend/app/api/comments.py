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

    # 调试：快速确认评论列表是否触发 N+1（正常情况下不应再出现逐条 parent_id 查询）
    # logger.debug(f"[Comments] list video_id={video_id} items={len(items)} total={total}")
    
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
    from app.models.video import Video

    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    video = db.query(Video).filter(Video.id == comment.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 权限：评论作者 / 视频上传者 / 管理员
    if (
        current_user.role != "admin"
        and current_user.id not in (comment.user_id, video.uploader_id)
    ):
        raise HTTPException(status_code=403, detail="无权删除该评论")

    comment.is_deleted = True
    db.commit()
    return {"success": True, "message": "评论已删除"}


@router.post("/comments/{comment_id}/restore", response_model=dict)
def restore_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """恢复评论（软删除恢复）"""
    from app.models.video import Video

    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    video = db.query(Video).filter(Video.id == comment.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    if (
        current_user.role != "admin"
        and current_user.id not in (comment.user_id, video.uploader_id)
    ):
        raise HTTPException(status_code=403, detail="无权恢复该评论")

    comment.is_deleted = False
    db.commit()
    return {"success": True, "message": "评论已恢复"}


@router.get("/videos/{video_id}/comments/manage", response_model=PageResult[CommentResponse])
def list_comments_manage(
    video_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("new", regex="^(new|hot)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创作中心：获取评论列表（包含已删除评论）"""
    from sqlalchemy.orm import joinedload, noload
    from sqlalchemy import func
    from app.models.video import Video

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    if current_user.role != "admin" and current_user.id != video.uploader_id:
        raise HTTPException(status_code=403, detail="无权管理该视频评论")

    skip = (page - 1) * page_size
    query = (
        db.query(Comment)
        .filter(Comment.video_id == video_id, Comment.parent_id == None)
        .options(
            joinedload(Comment.user),
            joinedload(Comment.reply_to_user),
            noload(Comment.replies),
        )
    )

    if sort_by == "hot":
        query = query.order_by(Comment.like_count.desc(), Comment.created_at.desc())
    else:
        query = query.order_by(Comment.created_at.desc())

    total = query.order_by(None).count()
    items = query.offset(skip).limit(page_size).all()

    # reply_count：仅统计未删除回复
    if items:
        ids = [c.id for c in items]
        rows = (
            db.query(Comment.parent_id, func.count(Comment.id))
            .filter(Comment.parent_id.in_(ids), Comment.is_deleted == False)
            .group_by(Comment.parent_id)
            .all()
        )
        reply_counts = {parent_id: int(cnt) for parent_id, cnt in rows if parent_id is not None}
        for c in items:
            setattr(c, "reply_count", reply_counts.get(c.id, 0))

    total_pages = (total + page_size - 1) // page_size
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


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
