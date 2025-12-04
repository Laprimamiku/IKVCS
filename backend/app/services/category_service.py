"""
分类业务逻辑服务

这个文件处理分类相关的业务逻辑
相当于 Java 的 @Service 层

需求：6.1, 6.2, 6.3
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from typing import List

from app.models.video import Category, Video
from app.schemas.category import CategoryCreateRequest


class CategoryService:
    """
    分类服务类
    
    类比 Java：
        @Service
        public class CategoryService {
            @Autowired
            private CategoryRepository categoryRepository;
            
            public List<Category> getAllCategories() { ... }
            public Category createCategory(CategoryCreateDTO dto) { ... }
            public void deleteCategory(Integer id) { ... }
        }
    
    为什么使用类而不是函数：
        - 方便管理相关的业务逻辑
        - 可以在 __init__ 中注入依赖（如果需要）
        - 符合面向对象设计原则
    """
    
    @staticmethod
    def get_all_categories(db: Session) -> List[Category]:
        """
        获取所有分类
        
        需求：6.1
        
        为什么这样写：
            - 按创建时间倒序排列（最新的在前面）
            - 返回所有字段（前端需要完整信息）
        """
        categories = db.query(Category).order_by(Category.created_at.desc()).all()
        return categories
    
    @staticmethod
    def create_category(db: Session, category_data: CategoryCreateRequest) -> Category:
        """
        创建分类
        
        需求：6.2
        
        流程：
        1. 检查分类名称是否已存在
        2. 创建分类记录
        3. 保存到数据库
        4. 返回分类对象
        
        为什么这样写：
            - 分类名称必须唯一（避免重复）
            - 使用 HTTPException 返回友好的错误信息
            - 使用 db.refresh() 获取自增 ID
        """
        # 1. 检查分类名称是否已存在
        existing_category = db.query(Category).filter(
            Category.name == category_data.name
        ).first()
        
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分类名称 '{category_data.name}' 已存在"
            )
        
        # 2. 创建分类对象
        new_category = Category(
            name=category_data.name,
            description=category_data.description
        )
        
        # 3. 保存到数据库
        db.add(new_category)
        db.commit()
        db.refresh(new_category)  # 刷新以获取自增 ID 和创建时间
        
        # 4. 返回分类对象
        return new_category
    
    @staticmethod
    def delete_category(db: Session, category_id: int) -> None:
        """
        删除分类
        
        需求：6.3
        
        流程：
        1. 检查分类是否存在
        2. 检查分类下是否有视频
        3. 如果有视频，拒绝删除
        4. 如果没有视频，删除分类
        
        为什么这样写：
            - 删除保护：防止误删除有视频的分类
            - 使用 count() 而不是 all()（性能更好）
            - 使用 CASCADE 删除会导致视频丢失分类（不安全）
        """
        # 1. 检查分类是否存在
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"分类 ID {category_id} 不存在"
            )
        
        # 2. 检查分类下是否有视频
        video_count = db.query(func.count(Video.id)).filter(
            Video.category_id == category_id
        ).scalar()
        
        if video_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分类 '{category.name}' 下有 {video_count} 个视频，无法删除"
            )
        
        # 3. 删除分类
        db.delete(category)
        db.commit()
    
    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Category:
        """
        根据 ID 获取分类
        
        辅助方法，用于其他服务调用
        
        为什么需要这个方法：
            - 创建视频时需要验证分类是否存在
            - 统一的错误处理逻辑
        """
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"分类 ID {category_id} 不存在"
            )
        return category
