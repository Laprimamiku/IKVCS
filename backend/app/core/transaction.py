"""
事务管理工具

提供事务装饰器和上下文管理器
类比 Java：相当于 Spring 的 @Transactional 注解

使用方式：
    方式1：使用装饰器
        @transactional
        def create_user(db: Session, user_data: dict):
            # 如果抛出异常，自动回滚
            user = User(**user_data)
            db.add(user)
            db.commit()
            return user
    
    方式2：使用上下文管理器
        with transaction(db):
            user = User(**user_data)
            db.add(user)
            # 如果出现异常，自动回滚
"""
from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class TransactionContext:
    """
    事务上下文管理器
    
    注意：FastAPI 的 get_db 依赖注入已经管理了 Session 的生命周期
    每个请求的 Session 已经在一个隐式事务中，所以我们不需要调用 db.begin()
    只需要在成功时 commit，失败时 rollback 即可
    
    类比 Java：
        @Transactional
        public void createUser(UserDTO dto) {
            // 如果抛出异常，自动回滚
        }
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def __enter__(self):
        """进入事务上下文"""
        # 不需要调用 db.begin()，因为 Session 已经在事务中
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出事务上下文"""
        if exc_type is not None:
            # 发生异常，回滚事务
            logger.error(f"事务回滚: {exc_type.__name__}: {exc_val}")
            self.db.rollback()
            return False  # 不抑制异常，继续抛出
        else:
            # 没有异常，提交事务
            try:
                self.db.commit()
                logger.debug("事务提交成功")
            except Exception as e:
                logger.error(f"事务提交失败: {e}")
                self.db.rollback()
                raise
        return True


def transaction(db: Session):
    """
    事务上下文管理器（函数形式）
    
    使用示例：
        with transaction(db):
            user = User(**user_data)
            db.add(user)
            # 自动提交或回滚
    """
    return TransactionContext(db)


def transactional(func: Callable) -> Callable:
    """
    事务装饰器
    
    自动管理函数执行过程中的事务
    如果函数抛出异常，自动回滚；否则自动提交
    
    使用示例：
        @transactional
        def create_user(db: Session, user_data: dict):
            user = User(**user_data)
            db.add(user)
            # 不需要手动 commit，装饰器会自动处理
            return user
    
    注意：
        - 函数必须接受 db: Session 作为参数
        - 函数内部不需要手动 commit/rollback
        - 如果函数返回前没有异常，会自动 commit
        - 如果函数抛出异常，会自动 rollback
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 查找 db 参数
        db = None
        for arg in args:
            if isinstance(arg, Session):
                db = arg
                break
        if 'db' in kwargs:
            db = kwargs['db']
        
        if db is None:
            raise ValueError("函数必须接受 db: Session 参数")
        
        # 使用事务上下文管理器
        with TransactionContext(db):
            return func(*args, **kwargs)
    
    return wrapper


def transactional_method(func: Callable) -> Callable:
    """
    事务装饰器（用于类方法）
    
    与 transactional 相同，但适用于类方法
    
    使用示例：
        class UserService:
            @transactional_method
            def create_user(self, db: Session, user_data: dict):
                user = User(**user_data)
                db.add(user)
                return user
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 查找 db 参数
        db = None
        for arg in args:
            if isinstance(arg, Session):
                db = arg
                break
        if 'db' in kwargs:
            db = kwargs['db']
        
        if db is None:
            raise ValueError("方法必须接受 db: Session 参数")
        
        # 使用事务上下文管理器
        with TransactionContext(db):
            return func(self, *args, **kwargs)
    
    return wrapper

