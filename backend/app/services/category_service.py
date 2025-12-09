"""
分类业务逻辑服务

这个文件处理分类相关的业务逻辑
相当于 Java 的 @Service 层

需求：6.1, 6.2, 6.3
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.models.video import Category, Video
from app.schemas.category import CategoryCreateRequest
from app.core.repository import BaseRepository
from app.core.exceptions import ResourceNotFoundException, ValidationException


class CategoryRepository(BaseRepository):
    """分类 Repository，继承通用 CRUD 方法"""
    model = Category


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
        
        使用 BaseRepository 的通用方法，减少重复代码
        """
        # 使用 BaseRepository 的通用查询方法
        return CategoryRepository.get_all(
            db=db,
            skip=0,
            limit=1000,  # 分类数量通常不多，设置一个较大的限制
            order_by="created_at.desc"
        )
    
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
        
        使用 BaseRepository 的通用创建方法，减少重复代码
        """
        # 1. 检查分类名称是否已存在
        existing_category = db.query(Category).filter(
            Category.name == category_data.name
        ).first()
        
        if existing_category:
            raise ValidationException(
                message=f"分类名称 '{category_data.name}' 已存在"
            )
        
        # 2. 使用 BaseRepository 的通用创建方法
        return CategoryRepository.create(
            db=db,
            obj_data={
                "name": category_data.name,
                "description": category_data.description
            }
        )
    
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
        
        使用 BaseRepository 的通用方法进行基础操作，业务逻辑保留在 Service 层
        """
        # 1. 检查分类是否存在（使用 BaseRepository）
        category = CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ResourceNotFoundException(resource="分类", resource_id=category_id)
        
        # 2. 检查分类下是否有视频（业务逻辑）
        video_count = db.query(func.count(Video.id)).filter(
            Video.category_id == category_id
        ).scalar()
        
        if video_count > 0:
            raise ValidationException(
                message=f"分类 '{category.name}' 下有 {video_count} 个视频，无法删除"
            )
        
        # 3. 使用 BaseRepository 的通用删除方法
        CategoryRepository.delete(db, category_id)
    
    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Category:
        """
        根据 ID 获取分类
        
        辅助方法，用于其他服务调用
        
        使用 BaseRepository 的通用方法，减少重复代码
        """
        category = CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ResourceNotFoundException(resource="分类", resource_id=category_id)
        return category
