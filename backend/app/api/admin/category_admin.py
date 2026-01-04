"""
分类管理 API（管理员）
功能：创建、更新、删除分类
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.user import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CategoryResponse, summary="创建分类")
async def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """创建新分类"""
    # 查重
    if CategoryRepository.get_by_name(db, category_in.name):
        raise HTTPException(
            status_code=400,
            detail=f"分类名称 '{category_in.name}' 已存在"
        )
    
    return CategoryRepository.create(db, category_in)


@router.put("/{category_id}", response_model=CategoryResponse, summary="更新分类")
async def update_category(
    category_in: CategoryUpdate,
    category_id: int = Path(..., description="分类ID"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """更新分类信息"""
    category = CategoryRepository.get_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    # 如果要修改名称，需检查新名称是否与其他分类重复
    if category_in.name and category_in.name != category.name:
        if CategoryRepository.get_by_name(db, category_in.name):
            raise HTTPException(status_code=400, detail="新分类名称已存在")
            
    return CategoryRepository.update(db, category, category_in)


@router.delete("/{category_id}", response_model=MessageResponse, summary="删除分类")
async def delete_category(
    category_id: int = Path(..., description="分类ID"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    删除分类
    注意：如果分类下还有视频，禁止删除
    """
    # 1. 检查是否存在
    if not CategoryRepository.get_by_id(db, category_id):
        raise HTTPException(status_code=404, detail="分类不存在")
    
    # 2. 检查是否有视频关联
    # 数据库定义了 ON DELETE RESTRICT，直接删除会报错
    # 所以我们需要先手动检查并给前端友好的提示
    if CategoryRepository.has_videos(db, category_id):
        raise HTTPException(
            status_code=400, 
            detail="该分类下仍有视频，无法删除。请先移动或删除相关视频。"
        )
    
    # 3. 执行删除
    CategoryRepository.delete(db, category_id)
    
    return MessageResponse(message="分类已删除")

