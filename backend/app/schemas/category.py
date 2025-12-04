"""
分类相关的 Pydantic Schema（DTO）

这个文件定义了分类相关的请求和响应数据结构
相当于 Java 的 DTO（Data Transfer Object）

需求：6.1, 6.2, 6.3
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CategoryCreateRequest(BaseModel):
    """
    创建分类请求
    
    类比 Java：
        public class CategoryCreateDTO {
            @NotBlank
            private String name;
            private String description;
        }
    
    为什么这样写：
        - name 必填，长度限制 1-50 字符
        - description 可选，长度限制 0-255 字符
        - 使用 Field() 添加验证规则和示例
    """
    name: str = Field(..., min_length=1, max_length=50, description="分类名称", example="科技")
    description: Optional[str] = Field(None, max_length=255, description="分类描述", example="科技类视频")
    
    class Config:
        # 允许从 ORM 模型创建（方便测试）
        from_attributes = True


class CategoryResponse(BaseModel):
    """
    分类响应
    
    类比 Java：
        public class CategoryVO {
            private Integer id;
            private String name;
            private String description;
            private LocalDateTime createdAt;
        }
    
    为什么这样写：
        - 返回所有字段（包括 ID 和创建时间）
        - 前端需要 ID 来关联视频
        - 前端需要创建时间来排序
    """
    id: int = Field(..., description="分类ID")
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        # 允许从 ORM 模型创建
        from_attributes = True


class MessageResponse(BaseModel):
    """
    通用消息响应
    
    用于返回操作成功/失败的消息
    """
    message: str = Field(..., description="消息内容")
