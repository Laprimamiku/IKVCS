"""
互动 Repository（点赞、收藏）
提供互动相关的数据访问方法

注意：当前点赞功能已通过 Redis 实现，收藏功能通过 UserCollection 模型实现
此类保留为未来扩展使用
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.repository import BaseRepository
from app.models.interaction import UserCollection


class InteractionRepository(BaseRepository):
    """
    互动 Repository
    
    注意：点赞功能已通过 Redis 实现（见 redis_service），
    收藏功能通过 UserCollection 模型实现
    """
    model = None
    
    @classmethod
    def check_like_exists(
        cls,
        db: Session,
        user_id: int,
        target_type: str,
        target_id: int
    ) -> bool:
        """
        检查用户是否已点赞
        
        注意：当前点赞功能通过 Redis 实现，此方法保留为未来扩展
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            target_type: 目标类型（VIDEO/COMMENT）
            target_id: 目标ID
            
        Returns:
            bool: 是否已点赞
        """
        # 当前通过 Redis 实现，见 redis_service
        return False
    
    @classmethod
    def get_user_likes(
        cls,
        db: Session,
        user_id: int,
        target_type: Optional[str] = None
    ) -> List:
        """
        获取用户的点赞列表
        
        注意：当前点赞功能通过 Redis 实现，此方法保留为未来扩展
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            target_type: 目标类型（可选）
            
        Returns:
            List: 点赞列表
        """
        # 当前通过 Redis 实现，见 redis_service
        return []
    
    @classmethod
    def get_collection(
        cls,
        db: Session,
        user_id: int,
        video_id: int
    ) -> Optional[UserCollection]:
        """
        获取收藏记录
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            video_id: 视频ID
            
        Returns:
            Optional[UserCollection]: 收藏记录，不存在返回None
        """
        return db.query(UserCollection).filter(
            UserCollection.user_id == user_id,
            UserCollection.video_id == video_id
        ).first()
    
    @classmethod
    def create_collection(
        cls,
        db: Session,
        user_id: int,
        video_id: int
    ) -> UserCollection:
        """
        创建收藏记录
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            video_id: 视频ID
            
        Returns:
            UserCollection: 创建的收藏记录
        """
        new_collection = UserCollection(user_id=user_id, video_id=video_id)
        db.add(new_collection)
        db.commit()
        db.refresh(new_collection)
        return new_collection
    
    @classmethod
    def delete_collection(
        cls,
        db: Session,
        collection_id: int
    ) -> bool:
        """
        删除收藏记录
        
        Args:
            db: 数据库会话
            collection_id: 收藏记录ID
            
        Returns:
            bool: 是否删除成功
        """
        collection = db.query(UserCollection).filter(UserCollection.id == collection_id).first()
        if collection:
            db.delete(collection)
            db.commit()
            return True
        return False
    
    @classmethod
    def get_user_collections(
        cls,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[UserCollection]:
        """
        获取用户的收藏列表（支持分页）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            List[UserCollection]: 收藏列表
        """
        return db.query(UserCollection).filter(
            UserCollection.user_id == user_id
        ).order_by(UserCollection.created_at.desc()).offset(skip).limit(limit).all()


class CollectionRepository(BaseRepository):
    """
    收藏 Repository
    
    注意：收藏功能已通过 UserCollection 模型实现
    """
    model = UserCollection
    
    @classmethod
    def check_collection_exists(
        cls,
        db: Session,
        user_id: int,
        video_id: int
    ) -> bool:
        """
        检查用户是否已收藏视频
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            video_id: 视频ID
            
        Returns:
            bool: 是否已收藏
        """
        exists = db.query(UserCollection).filter(
            UserCollection.user_id == user_id,
            UserCollection.video_id == video_id
        ).first()
        return exists is not None
    
    @classmethod
    def get_user_collections(
        cls,
        db: Session,
        user_id: int
    ) -> List:
        """
        获取用户的收藏列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            List: 收藏列表
        """
        return db.query(UserCollection).filter(
            UserCollection.user_id == user_id
        ).all()