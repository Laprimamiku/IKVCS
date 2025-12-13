from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import List, Optional, Tuple

from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate

class CommentRepository:
    def create(self, db: Session, video_id: int, user_id: int, obj_in: CommentCreate) -> Comment:
        """创建评论"""
        db_comment = Comment(
            video_id=video_id,
            user_id=user_id,
            parent_id=obj_in.parent_id,
            content=obj_in.content,
            # AI 字段默认为 None，等待异步任务更新
            ai_score=None,
            ai_label=None
        )
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment

    def get(self, db: Session, id: int) -> Optional[Comment]:
        """获取单条评论"""
        return db.query(Comment).filter(
            Comment.id == id, 
            Comment.is_deleted == False
        ).first()

    def get_list(
        self, 
        db: Session, 
        video_id: int, 
        skip: int = 0, 
        limit: int = 20, 
        sort_by: str = "new",  # "new" | "hot"
        parent_id: Optional[int] = None
    ) -> Tuple[List[Comment], int]:
        """
        获取评论列表
        - 支持按视频筛选
        - 支持只看根评论 (parent_id=None)
        - 支持排序
        """
        query = db.query(Comment).filter(
            Comment.video_id == video_id,
            Comment.is_deleted == False,
            Comment.parent_id == parent_id  # 默认只查根评论
        )

        # 排序逻辑
        if sort_by == "hot":
            # 按点赞数倒序，其次按时间倒序
            query = query.order_by(Comment.like_count.desc(), Comment.created_at.desc())
        else:
            # 默认按时间倒序
            query = query.order_by(Comment.created_at.desc())

        # 获取总数
        total = query.count()

        # 预加载用户信息，避免 N+1 查询
        query = query.options(joinedload(Comment.user))
        
        # 分页
        items = query.offset(skip).limit(limit).all()
        
        return items, total

    def delete(self, db: Session, id: int) -> bool:
        """软删除"""
        comment = self.get(db, id)
        if not comment:
            return False
        
        comment.is_deleted = True
        db.commit()
        return True

comment_repository = CommentRepository()