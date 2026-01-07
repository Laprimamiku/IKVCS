from sqlalchemy.orm import Session, joinedload, noload
from sqlalchemy import desc, func
from typing import List, Optional, Tuple

from app.core.repository import BaseRepository
from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate

class CommentRepository(BaseRepository):
    """评论 Repository"""
    model = Comment
    
    @classmethod
    def create_comment(
        cls,
        db: Session,
        video_id: int,
        user_id: int,
        obj_in: CommentCreate
    ) -> Comment:
        """
        创建评论
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            user_id: 用户ID
            obj_in: 评论创建数据
            
        Returns:
            Comment: 创建的评论对象
        """
        db_comment = Comment(
            video_id=video_id,
            user_id=user_id,
            parent_id=obj_in.parent_id,
            reply_to_user_id=obj_in.reply_to_user_id,
            content=obj_in.content,
            # AI 字段默认为 None，等待异步任务更新
            ai_score=None,
            ai_label=None
        )
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment

    @classmethod
    def get_by_id_with_relations(
        cls,
        db: Session,
        id: int
    ) -> Optional[Comment]:
        """
        获取单条评论（包含用户和回复目标用户信息）
        
        Args:
            db: 数据库会话
            id: 评论ID
            
        Returns:
            Optional[Comment]: 评论对象，不存在返回 None
        """
        return db.query(Comment).options(
            joinedload(Comment.user),
            joinedload(Comment.reply_to_user)
        ).filter(
            Comment.id == id, 
            Comment.is_deleted == False
        ).first()
    
    # 保持向后兼容的别名
    @classmethod
    def get(cls, db: Session, id: int) -> Optional[Comment]:
        """获取单条评论（向后兼容方法）"""
        return cls.get_by_id_with_relations(db, id)

    @classmethod
    def get_list(
        cls,
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
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            skip: 跳过数量
            limit: 限制数量
            sort_by: 排序方式，"new" 或 "hot"
            parent_id: 父评论ID，None表示只查根评论
            
        Returns:
            Tuple[List[Comment], int]: (评论列表, 总数)
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

        # 优化：先获取总数（清除 ORDER BY，避免无意义的排序开销）
        total = query.order_by(None).count()

        # 预加载用户信息，避免 N+1 查询
        query = query.options(
            joinedload(Comment.user),
            joinedload(Comment.reply_to_user),
            # 列表接口不需要递归加载 replies，避免 Pydantic 序列化触发 N+1
            noload(Comment.replies),
        )
        
        # 分页
        items = query.offset(skip).limit(limit).all()

        # 批量统计 reply_count，避免每条评论单独查一次 replies（N+1）
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
        
        return items, total

    @classmethod
    def soft_delete(cls, db: Session, id: int) -> bool:
        """
        软删除评论
        
        Args:
            db: 数据库会话
            id: 评论ID
            
        Returns:
            bool: 是否删除成功
        """
        comment = cls.get_by_id_with_relations(db, id)
        if not comment:
            return False
        
        comment.is_deleted = True
        db.commit()
        return True
    
    # 保持向后兼容的别名
    @classmethod
    def delete(cls, db: Session, id: int) -> bool:
        """软删除（向后兼容方法）"""
        return cls.soft_delete(db, id)

# 保持向后兼容的单例实例
comment_repository = CommentRepository()
