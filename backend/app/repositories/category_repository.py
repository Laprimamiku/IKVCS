# backend/app/repositories/category_repository.py

from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.repository import BaseRepository
from app.models.video import Category, Video
from app.schemas.category import CategoryCreate, CategoryUpdate

class CategoryRepository(BaseRepository):
    """分类 Repository"""
    model = Category
    
    @classmethod
    def get_all(cls, db: Session) -> List[Category]:
        """
        获取所有分类
        
        Args:
            db: 数据库会话
            
        Returns:
            List[Category]: 分类列表
        """
        return db.query(Category).all()

    @classmethod
    def get_by_name(cls, db: Session, name: str) -> Optional[Category]:
        """
        根据名称查询分类
        
        Args:
            db: 数据库会话
            name: 分类名称
            
        Returns:
            Optional[Category]: 分类对象，不存在返回 None
        """
        return db.query(Category).filter(Category.name == name).first()

    @classmethod
    def create_category(
        cls,
        db: Session,
        category_in: Optional[CategoryCreate] = None,
        obj_data: Optional[dict] = None
    ) -> Category:
        """
        创建分类
        
        Args:
            db: 数据库会话
            category_in: 分类创建数据（Pydantic Schema）
            obj_data: 分类数据字典（可选，用于直接传入字典）
            
        Returns:
            Category: 创建的分类对象
        """
        if obj_data:
            db_category = Category(
                name=obj_data.get("name"),
                description=obj_data.get("description")
            )
        elif category_in:
            db_category = Category(
                name=category_in.name,
                description=category_in.description
            )
        else:
            raise ValueError("必须提供 category_in 或 obj_data")
        
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category
    
    # 保持向后兼容的别名
    @classmethod
    def create(cls, db: Session, category_in: CategoryCreate = None, obj_data: dict = None) -> Category:
        """创建分类（向后兼容方法）"""
        return cls.create_category(db, category_in, obj_data)

    @classmethod
    def update_category(
        cls,
        db: Session,
        db_category: Category,
        category_in: CategoryUpdate
    ) -> Category:
        """
        更新分类
        
        Args:
            db: 数据库会话
            db_category: 分类对象
            category_in: 分类更新数据
            
        Returns:
            Category: 更新后的分类对象
        """
        if category_in.name is not None:
            db_category.name = category_in.name
        if category_in.description is not None:
            db_category.description = category_in.description
        
        db.commit()
        db.refresh(db_category)
        return db_category
    
    # 保持向后兼容的别名
    @classmethod
    def update(cls, db: Session, db_category: Category, category_in: CategoryUpdate) -> Category:
        """更新分类（向后兼容方法）"""
        return cls.update_category(db, db_category, category_in)
        
    @classmethod
    def has_videos(cls, db: Session, category_id: int) -> bool:
        """检查分类下是否有视频"""
        return db.query(Video).filter(Video.category_id == category_id).first() is not None