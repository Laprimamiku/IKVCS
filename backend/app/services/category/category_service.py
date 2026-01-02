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
from app.schemas.category import CategoryCreate
from app.repositories.category_repository import CategoryRepository
from app.core.exceptions import ResourceNotFoundException, ValidationException


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
    
    # 临时分类名称常量
    TEMP_CATEGORY_NAME = "临时分类"
    
    @staticmethod
    def get_all_categories(db: Session) -> List[Category]:
        """
        获取所有分类
        
        需求：6.1
        
        使用 BaseRepository 的通用方法，减少重复代码
        """
        # 使用 Repository 的专用方法
        return CategoryRepository.get_all(db)
    
    @staticmethod
    def get_public_categories(db: Session) -> List[Category]:
        """
        获取公开分类（排除临时分类）
        
        用于首页分类栏显示
        """
        categories = CategoryRepository.get_all(db)
        return [cat for cat in categories if cat.name != CategoryService.TEMP_CATEGORY_NAME]
    
    @staticmethod
    def get_or_create_temp_category(db: Session) -> Category:
        """
        获取或创建临时分类
        
        如果临时分类不存在，则自动创建
        """
        temp_category = CategoryRepository.get_by_name(db, CategoryService.TEMP_CATEGORY_NAME)
        
        if not temp_category:
            # 创建临时分类
            temp_category = CategoryRepository.create(
                db=db,
                obj_data={
                    "name": CategoryService.TEMP_CATEGORY_NAME,
                    "description": "系统自动创建的临时分类，用于存放被删除分类下的视频"
                }
            )
        
        return temp_category
    
    @staticmethod
    def create_category(db: Session, category_data: CategoryCreate) -> Category:
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
        existing_category = CategoryRepository.get_by_name(db, category_data.name)
        
        if existing_category:
            raise ValidationException(
                message=f"分类名称 '{category_data.name}' 已存在"
            )
        
        # 2. 禁止创建临时分类名称
        if category_data.name == CategoryService.TEMP_CATEGORY_NAME:
            raise ValidationException(
                message=f"不能创建名为 '{CategoryService.TEMP_CATEGORY_NAME}' 的分类"
            )
        
        # 3. 使用 BaseRepository 的通用创建方法
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
        2. 检查是否为临时分类（不允许删除）
        3. 如果分类下有视频，将视频移动到临时分类
        4. 删除分类
        
        使用 BaseRepository 的通用方法进行基础操作，业务逻辑保留在 Service 层
        """
        # 1. 检查分类是否存在（使用 BaseRepository）
        category = CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ResourceNotFoundException(resource="分类", resource_id=category_id)
        
        # 2. 检查是否为临时分类（不允许删除）
        if category.name == CategoryService.TEMP_CATEGORY_NAME:
            raise ValidationException(
                message="临时分类不能被删除"
            )
        
        # 3. 检查分类下是否有视频
        video_count = db.query(func.count(Video.id)).filter(
            Video.category_id == category_id
        ).scalar()
        
        if video_count > 0:
            # 获取或创建临时分类
            temp_category = CategoryService.get_or_create_temp_category(db)
            
            # 将所有视频移动到临时分类
            db.query(Video).filter(
                Video.category_id == category_id
            ).update({"category_id": temp_category.id})
            
            # 提交视频移动操作
            db.commit()
        
        # 4. 使用 BaseRepository 的通用删除方法
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

