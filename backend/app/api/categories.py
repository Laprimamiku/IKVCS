"""
分类管理 API

这个文件的作用：
1. 获取分类列表（GET /api/v1/categories）- 所有用户可访问
2. 创建分类（POST /api/v1/admin/categories）- 仅管理员可访问
3. 删除分类（DELETE /api/v1/admin/categories/{category_id}）- 仅管理员可访问

类比 Java：
    相当于 Spring Boot 的 CategoryController
    
需求：6.1, 6.2, 6.3
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryResponse,
    MessageResponse
)
from app.services.category.category_service import CategoryService

router = APIRouter()


@router.get("", response_model=List[CategoryResponse])
async def get_categories(
    db: Session = Depends(get_db)
):
    """
    获取所有分类
    
    类比 Java：
        @GetMapping("/categories")
        public ResponseEntity<List<CategoryVO>> getCategories() {
            List<Category> categories = categoryService.getAllCategories();
            return ResponseEntity.ok(categories);
        }
    
    需求：6.1
    
    为什么这样写：
        - 不需要认证（所有用户都可以查看分类）
        - 返回 List[CategoryResponse]（自动序列化）
        - 使用 Depends(get_db) 注入数据库会话
    
    容易踩坑点：
        - 路由路径是 ""，因为在 main.py 中已经配置了 prefix="/api/v1/categories"
        - 如果写成 "/categories"，实际路径会变成 /api/v1/categories/categories
    """
    categories = CategoryService.get_all_categories(db)
    return categories


@router.post("/admin", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    创建分类（仅管理员）
    
    类比 Java：
        @PostMapping("/admin/categories")
        @PreAuthorize("hasRole('ADMIN')")
        public ResponseEntity<CategoryVO> createCategory(
            @RequestBody @Valid CategoryCreateDTO dto,
            @AuthenticationPrincipal User user
        ) {
            Category category = categoryService.createCategory(dto);
            return ResponseEntity.status(HttpStatus.CREATED).body(category);
        }
    
    需求：6.2
    
    为什么这样写：
        - 使用 require_admin 依赖注入（验证管理员权限）
        - 返回 201 Created 状态码（RESTful 规范）
        - 自动验证请求体（Pydantic 自动验证）
    
    容易踩坑点：
        - 必须先通过 require_admin 验证，否则普通用户也能创建分类
        - 路由路径是 "/admin"，完整路径是 /api/v1/categories/admin
    """
    category = CategoryService.create_category(db, category_data)
    return category


@router.delete("/admin/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    删除分类（仅管理员）
    
    类比 Java：
        @DeleteMapping("/admin/categories/{categoryId}")
        @PreAuthorize("hasRole('ADMIN')")
        public ResponseEntity<MessageDTO> deleteCategory(
            @PathVariable Integer categoryId,
            @AuthenticationPrincipal User user
        ) {
            categoryService.deleteCategory(categoryId);
            return ResponseEntity.ok(new MessageDTO("删除成功"));
        }
    
    需求：6.3
    
    为什么这样写：
        - 使用路径参数 {category_id}（RESTful 风格）
        - 删除保护在 Service 层实现（业务逻辑）
        - 返回成功消息（前端需要提示）
    
    容易踩坑点：
        - 如果分类下有视频，Service 层会抛出 HTTPException
        - FastAPI 会自动捕获异常并返回对应的 HTTP 状态码
    """
    CategoryService.delete_category(db, category_id)
    return MessageResponse(message=f"分类 ID {category_id} 删除成功")
