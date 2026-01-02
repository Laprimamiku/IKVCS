# backend/app/api/categories.py

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.category_repository import CategoryRepository
from app.services.category.category_service import CategoryService
from app.schemas.category import CategoryResponse

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse], summary="获取所有分类")
def get_categories(db: Session = Depends(get_db)):
    """
    获取全部分类列表
    用于管理后台或视频编辑时的下拉选择
    """
    return CategoryRepository.get_all(db)

@router.get("/public", response_model=List[CategoryResponse], summary="获取公开分类")
def get_public_categories(db: Session = Depends(get_db)):
    """
    获取公开分类列表（排除临时分类）
    用于首页分类导航栏显示
    """
    return CategoryService.get_public_categories(db)