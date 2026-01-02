"""
评论服务
职责：处理评论创建、查询等业务逻辑
"""
from sqlalchemy.orm import Session
from typing import Tuple, List, Optional

from app.repositories.comment_repository import comment_repository
from app.models.comment import Comment
from app.schemas.comment import CommentCreate
from app.core.exceptions import ResourceNotFoundException


class CommentService:
    """评论服务"""
    
    @staticmethod
    def create_comment(
        db: Session,
        video_id: int,
        user_id: int,
        comment_data: CommentCreate
    ) -> Comment:
        """
        创建评论（支持根评论和回复）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            user_id: 用户ID
            comment_data: 评论数据
            
        Returns:
            Comment: 创建的评论对象
            
        Raises:
            ResourceNotFoundException: 父评论不存在或不属于该视频
        """
        # 如果是回复，检查父评论是否存在
        if comment_data.parent_id:
            parent = comment_repository.get(db, comment_data.parent_id)
            if not parent or parent.video_id != video_id:
                raise ResourceNotFoundException(
                    resource="父评论",
                    resource_id=comment_data.parent_id
                )
        
        # 创建评论
        new_comment = comment_repository.create(
            db=db,
            video_id=video_id,
            user_id=user_id,
            obj_in=comment_data
        )
        
        return new_comment
    
    @staticmethod
    def get_comment_list(
        db: Session,
        video_id: int,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "new",
        parent_id: Optional[int] = None
    ) -> Tuple[List[Comment], int]:
        """
        获取评论列表
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式（"new" 或 "hot"）
            parent_id: 父评论ID（可选，用于获取回复）
            
        Returns:
            Tuple[List[Comment], int]: (评论列表, 总数)
        """
        skip = (page - 1) * page_size
        return comment_repository.get_list(
            db=db,
            video_id=video_id,
            skip=skip,
            limit=page_size,
            sort_by=sort_by,
            parent_id=parent_id
        )
    
    @staticmethod
    def get_comment_by_id(db: Session, comment_id: int) -> Optional[Comment]:
        """
        根据ID获取单条评论
        
        Args:
            db: 数据库会话
            comment_id: 评论ID
            
        Returns:
            Optional[Comment]: 评论对象，如果不存在则返回 None
        """
        from sqlalchemy.orm import joinedload
        return db.query(Comment).options(
            joinedload(Comment.user),
            joinedload(Comment.reply_to_user)
        ).filter(
            Comment.id == comment_id,
            Comment.is_deleted == False
        ).first()





