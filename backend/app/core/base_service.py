"""
通用 Service 基类

提供通用的业务逻辑方法，减少重复代码
类比 Java：相当于 Spring 的 BaseService
"""
from typing import TypeVar, Generic, Optional, Type
from sqlalchemy.orm import Session

from app.core.repository import BaseRepository
from app.core.exceptions import ResourceNotFoundException
from app.core.error_codes import ErrorCode

# 类型变量
ModelType = TypeVar("ModelType")
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


class BaseService(Generic[ModelType, RepositoryType]):
    """
    通用 Service 基类
    
    提供通用的业务逻辑方法
    """
    
    repository: Type[RepositoryType] = None  # 子类需要指定 Repository 类
    
    @classmethod
    def get_by_id_or_raise(
        cls,
        db: Session,
        id: int,
        resource_name: str = "资源",
        error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND
    ) -> ModelType:
        """
        根据ID获取资源，不存在则抛出异常
        
        Args:
            db: 数据库会话
            id: 资源ID
            resource_name: 资源名称（用于错误消息）
            error_code: 错误码
            
        Returns:
            ModelType: 资源对象
            
        Raises:
            ResourceNotFoundException: 资源不存在
        """
        if cls.repository is None:
            raise ValueError("子类必须设置 repository 属性")
        
        obj = cls.repository.get_by_id(db, id)
        if not obj:
            raise ResourceNotFoundException(resource=resource_name, resource_id=id)
        return obj
    
    @classmethod
    def get_by_id(
        cls,
        db: Session,
        id: int
    ) -> Optional[ModelType]:
        """
        根据ID获取资源（不抛出异常）
        
        Args:
            db: 数据库会话
            id: 资源ID
            
        Returns:
            Optional[ModelType]: 资源对象，不存在返回 None
        """
        if cls.repository is None:
            raise ValueError("子类必须设置 repository 属性")
        
        return cls.repository.get_by_id(db, id)
    
    @classmethod
    def exists(
        cls,
        db: Session,
        id: int
    ) -> bool:
        """
        检查资源是否存在
        
        Args:
            db: 数据库会话
            id: 资源ID
            
        Returns:
            bool: 是否存在
        """
        if cls.repository is None:
            raise ValueError("子类必须设置 repository 属性")
        
        return cls.repository.exists(db, id)

