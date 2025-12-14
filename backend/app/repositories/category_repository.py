# backend/app/repositories/category_repository.py

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.video import Category, Video
from app.schemas.category import CategoryCreate, CategoryUpdate

class CategoryRepository:
    
    @classmethod
    def get_all(cls, db: Session) -> List[Category]:
        """获取所有分类"""
        return db.query(Category).all()

    @classmethod
    def get_by_id(cls, db: Session, category_id: int) -> Optional[Category]:
        return db.query(Category).filter(Category.id == category_id).first()

    @classmethod
    def get_by_name(cls, db: Session, name: str) -> Optional[Category]:
        return db.query(Category).filter(Category.name == name).first()

    @classmethod
    def create(cls, db: Session, category_in: CategoryCreate) -> Category:
        """创建分类"""
        db_category = Category(
            name=category_in.name,
            description=category_in.description
        )
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category

    @classmethod
    def update(cls, db: Session, db_category: Category, category_in: CategoryUpdate) -> Category:
        """更新分类"""
        if category_in.name is not None:
            db_category.name = category_in.name
        if category_in.description is not None:
            db_category.description = category_in.description
        
        db.commit()
        db.refresh(db_category)
        return db_category

    @classmethod
    def delete(cls, db: Session, category_id: int) -> bool:
        """
        删除分类
        注意：如果有视频属于该分类，数据库外键约束通常会阻止删除
        """
        db_category = cls.get_by_id(db, category_id)
        if not db_category:
            return False
            
        db.delete(db_category)
        db.commit()
        return True
        
    @classmethod
    def has_videos(cls, db: Session, category_id: int) -> bool:
        """检查分类下是否有视频"""
        return db.query(Video).filter(Video.category_id == category_id).first() is not None