"""
评论 Repository
提供评论相关的数据访问方法
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc

from app.core.repository import BaseRepository
from app.models.comment import Comment


class CommentRepository(BaseRepository):
    """评论 Repository"""
    model = Comment
    
    @classmethod
    def get_by_id_with_relations(
        cls,
        db: Session,
        comment_id: int
    ) -> Optional[Comment]:
        """
        根据ID查询评论（包含关联数据）
        
        Args:
            db: 数据库会话
            comment_id: 评论ID
            
        Returns:
            Optional[Comment]: 评论对象，不存在返回None
        """
        return db.query(Comment).options(
            joinedload(Comment.user),
            joinedload(Comment.video)
        ).filter(
            Comment.id == comment_id,
            Comment.is_deleted == False
        ).first()
    
    @classmethod
    def get_video_comments(
        cls,
        db: Session,
        video_id: int,
        page: int = 1,
        page_size: int = 20,
        parent_id: Optional[int] = None
    ) -> Tuple[List[Comment], int]:
        """
        获取视频的评论列表（支持分页）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            page: 页码（从1开始）
            page_size: 每页数量
            parent_id: 父评论ID（None表示获取顶级评论）
            
        Returns:
            Tuple[List[Comment], int]: (评论列表, 总数)
        """
        # 基础查询：未删除的评论
        query = db.query(Comment).options(
            joinedload(Comment.user)
        ).filter(
            Comment.video_id == video_id,
            Comment.is_deleted == False
        )
        
        # 筛选顶级评论或子评论
        if parent_id is None:
            query = query.filter(Comment.parent_id.is_(None))
        else:
            query = query.filter(Comment.parent_id == parent_id)
        
        # 获取总数
        total = query.count()
        
        # 分页查询（按创建时间倒序）
        offset = (page - 1) * page_size
        comments = query.order_by(desc(Comment.created_at)).offset(offset).limit(page_size).all()
        
        return comments, total
    
    @classmethod
    def get_user_comments(
        cls,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Comment], int]:
        """
        获取用户的评论列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            
        Returns:
            Tuple[List[Comment], int]: (评论列表, 总数)
        """
        # 基础查询：用户的未删除评论
        query = db.query(Comment).options(
            joinedload(Comment.video)
        ).filter(
            Comment.user_id == user_id,
            Comment.is_deleted == False
        )
        
        # 获取总数
        total = query.count()
        
        # 分页查询（按创建时间倒序）
        offset = (page - 1) * page_size
        comments = query.order_by(desc(Comment.created_at)).offset(offset).limit(page_size).all()
        
        return comments, total
    
    @classmethod
    def get_replies_count(
        cls,
        db: Session,
        comment_id: int
    ) -> int:
        """
        获取评论的回复数量
        
        Args:
            db: 数据库会话
            comment_id: 评论ID
            
        Returns:
            int: 回复数量
        """
        return db.query(Comment).filter(
            Comment.parent_id == comment_id,
            Comment.is_deleted == False
        ).count()
    
    @classmethod
    def soft_delete(
        cls,
        db: Session,
        comment_id: int
    ) -> bool:
        """
        软删除评论
        
        Args:
            db: 数据库会话
            comment_id: 评论ID
            
        Returns:
            bool: 是否成功
        """
        comment = cls.get_by_id(db, comment_id)
        if not comment:
            return False
        
        comment.is_deleted = True
        db.commit()
        return True
    
    @classmethod
    def increment_like_count(
        cls,
        db: Session,
        comment_id: int
    ) -> bool:
        """
        增加评论点赞数
        
        Args:
            db: 数据库会话
            comment_id: 评论ID
            
        Returns:
            bool: 是否成功
        """
        comment = cls.get_by_id(db, comment_id)
        if not comment:
            return False
        
        comment.like_count = (comment.like_count or 0) + 1
        db.commit()
        return True
    
    @classmethod
    def decrement_like_count(
        cls,
        db: Session,
        comment_id: int
    ) -> bool:
        """
        减少评论点赞数
        
        Args:
            db: 数据库会话
            comment_id: 评论ID
            
        Returns:
            bool: 是否成功
        """
        comment = cls.get_by_id(db, comment_id)
        if not comment or comment.like_count <= 0:
            return False
        
        comment.like_count -= 1
        db.commit()
        return True
    
    @classmethod
    def update_ai_analysis(
        cls,
        db: Session,
        comment_id: int,
        ai_score: int,
        ai_label: str
    ) -> bool:
        """
        更新评论的AI分析结果
        
        Args:
            db: 数据库会话
            comment_id: 评论ID
            ai_score: AI评分
            ai_label: AI标签
            
        Returns:
            bool: 是否成功
        """
        comment = cls.get_by_id(db, comment_id)
        if not comment:
            return False
        
        comment.ai_score = ai_score
        comment.ai_label = ai_label
        db.commit()
        return True
