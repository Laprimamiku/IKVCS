"""
通用 Repository 基类

提供通用的 CRUD 操作方法
类比 Java：相当于 MyBatis-Plus 的 BaseMapper 或 Spring Data JPA 的 Repository

使用方式：
    from app.core.repository import BaseRepository
    from app.models.video import Video
    
    class VideoRepository(BaseRepository):
        model = Video
    
    # 使用
    video = VideoRepository.get_by_id(db, 1)
    videos = VideoRepository.get_all(db, skip=0, limit=20)
"""
from typing import Type, TypeVar, Optional, List, Union, Dict, Any, Sequence
from sqlalchemy.orm import Session, joinedload, RelationshipProperty
from sqlalchemy import and_, or_

from app.core.database import Base
from app.core.types import FilterDict

# 类型变量，用于泛型
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository:
    """
    通用 Repository 基类
    
    提供通用的 CRUD 操作方法
    类比 Java：
        public interface BaseMapper<T> {
            T selectById(Long id);
            List<T> selectList(Wrapper<T> wrapper);
            int insert(T entity);
            int updateById(T entity);
            int deleteById(Long id);
        }
    """
    
    model: Type[ModelType] = None  # 子类需要指定模型类
    
    @classmethod
    def get_by_id(cls, db: Session, id: int) -> Optional[ModelType]:
        """
        根据 ID 查询
        
        Args:
            db: 数据库会话
            id: 主键ID
            
        Returns:
            Optional[ModelType]: 模型对象，不存在返回 None
            
        使用示例：
            user = UserRepository.get_by_id(db, 1)
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        return db.query(cls.model).filter(cls.model.id == id).first()
    
    @classmethod
    def get_all(
        cls,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[FilterDict] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        查询所有记录（支持分页、筛选、排序）
        
        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            filters: 筛选条件字典，如 {"status": 1, "name": "test"}
            order_by: 排序字段，如 "created_at.desc()"
            
        Returns:
            List[ModelType]: 模型对象列表
            
        使用示例：
            users = UserRepository.get_all(db, skip=0, limit=20, filters={"status": 1})
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        
        query = db.query(cls.model)
        
        # 应用筛选条件
        if filters:
            for key, value in filters.items():
                if hasattr(cls.model, key):
                    query = query.filter(getattr(cls.model, key) == value)
        
        # 应用排序
        if order_by:
            if "." in order_by:
                field, direction = order_by.split(".")
                if hasattr(cls.model, field):
                    attr = getattr(cls.model, field)
                    if direction == "desc":
                        query = query.order_by(attr.desc())
                    else:
                        query = query.order_by(attr.asc())
        
        return query.offset(skip).limit(limit).all()
    
    @classmethod
    def count(cls, db: Session, filters: Optional[FilterDict] = None) -> int:
        """
        统计记录数量
        
        Args:
            db: 数据库会话
            filters: 筛选条件字典
            
        Returns:
            int: 记录数量
            
        使用示例：
            total = UserRepository.count(db, filters={"status": 1})
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        
        query = db.query(cls.model)
        
        # 应用筛选条件
        if filters:
            for key, value in filters.items():
                if hasattr(cls.model, key):
                    query = query.filter(getattr(cls.model, key) == value)
        
        return query.count()
    
    @classmethod
    def create(cls, db: Session, obj_data: FilterDict) -> ModelType:
        """
        创建新记录
        
        Args:
            db: 数据库会话
            obj_data: 对象数据字典
            
        Returns:
            ModelType: 创建的模型对象
            
        使用示例：
            user = UserRepository.create(db, {"username": "example", "password_hash": "hashed_password"})
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        
        obj = cls.model(**obj_data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    
    @classmethod
    def update(
        cls,
        db: Session,
        id: int,
        update_data: Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        更新记录
        
        Args:
            db: 数据库会话
            id: 主键ID
            update_data: 更新数据字典
            
        Returns:
            Optional[ModelType]: 更新后的模型对象，不存在返回 None
            
        使用示例：
            user = UserRepository.update(db, 1, {"nickname": "新昵称"})
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        
        obj = cls.get_by_id(db, id)
        if not obj:
            return None
        
        for key, value in update_data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        db.commit()
        db.refresh(obj)
        return obj
    
    @classmethod
    def delete(cls, db: Session, id: int) -> bool:
        """
        删除记录
        
        Args:
            db: 数据库会话
            id: 主键ID
            
        Returns:
            bool: 是否删除成功
            
        使用示例：
            success = UserRepository.delete(db, 1)
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        
        obj = cls.get_by_id(db, id)
        if not obj:
            return False
        
        db.delete(obj)
        db.commit()
        return True
    
    @classmethod
    def exists(cls, db: Session, id: int) -> bool:
        """
        检查记录是否存在
        
        Args:
            db: 数据库会话
            id: 主键ID
            
        Returns:
            bool: 是否存在
            
        使用示例：
            if UserRepository.exists(db, 1):
                print("用户存在")
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        
        return db.query(cls.model).filter(cls.model.id == id).first() is not None
    
    @classmethod
    def get_by_id_with_relations(
        cls,
        db: Session,
        id: int,
        relations: Optional[List[str]] = None
    ) -> Optional[ModelType]:
        """
        根据ID查询（包含关联数据）
        
        Args:
            db: 数据库会话
            id: 主键ID
            relations: 关联字段列表，如 ["uploader", "category"]
            
        Returns:
            Optional[ModelType]: 模型对象，不存在返回 None
            
        使用示例：
            video = VideoRepository.get_by_id_with_relations(db, 1, ["uploader", "category"])
        """
        if cls.model is None:
            raise ValueError("子类必须设置 model 属性")
        
        query = db.query(cls.model).filter(cls.model.id == id)
        
        # 如果指定了关联字段，使用 joinedload 预加载
        if relations:
            for rel in relations:
                if hasattr(cls.model, rel):
                    query = query.options(joinedload(getattr(cls.model, rel)))
        
        return query.first()

