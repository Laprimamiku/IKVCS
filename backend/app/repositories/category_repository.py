"""
分类 Repository
提供分类相关的数据访问方法
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.repository import BaseRepository
from app.models.video import Category


class CategoryRepository(BaseRepository):
    """分类 Repository"""
    model = Category
    
    @classmethod
    def get_all_categories(cls, db: Session) -> List[Category]:
        """
        获取所有分类
        
        Args:
            db: 数据库会话
            
        Returns:
            List[Category]: 分类列表
        """
        return db.query(Category).order_by(Category.id.asc()).all()
    
    @classmethod
    def get_by_name(
        cls,
        db: Session,
        name: str
    ) -> Optional[Category]:
        """
        根据名称查询分类
        
        Args:
            db: 数据库会话
            name: 分类名称
            
        Returns:
            Optional[Category]: 分类对象，不存在返回None
        """
        return db.query(Category).filter(Category.name == name).first()

