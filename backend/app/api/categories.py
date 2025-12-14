# backend/app/api/categories.py

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryResponse

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse], summary="获取所有分类")
def get_categories(db: Session = Depends(get_db)):
    """
    获取全部分类列表
    用于视频上传时的下拉选择，或首页的分类导航
    """
    return CategoryRepository.get_all(db)