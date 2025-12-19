"""
上传相关的 Pydantic Schema（DTO）

需求：3.1-3.6
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class UploadInitRequest(BaseModel):
    """
    上传初始化请求
    
    类比 Java：
        public class UploadInitDTO {
            @NotBlank
            @Size(min=64, max=64)
            private String fileHash;
            
            @NotBlank
            private String fileName;
            
            @Min(1)
            private Integer totalChunks;
            
            @Min(1)
            private Long fileSize;
        }
    
    为什么这样写：
        - file_hash 必须是 64 位（SHA-256 十六进制）
        - total_chunks 和 file_size 必须大于 0
        - 前端需要先计算文件哈希再调用此接口
    """
    file_hash: str = Field(..., min_length=64, max_length=64, description="文件哈希（SHA-256）")
    file_name: str = Field(..., min_length=1, max_length=255, description="文件名")
    total_chunks: int = Field(..., gt=0, description="总分片数")
    file_size: int = Field(..., gt=0, description="文件大小（字节）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_hash": "a" * 64,
                "file_name": "my_video.mp4",
                "total_chunks": 100,
                "file_size": 524288000
            }
        }


class UploadInitResponse(BaseModel):
    """
    上传初始化响应
    
    为什么返回 uploaded_chunks：
        - 支持断点续传
        - 前端可以跳过已上传的分片
        - 减少重复上传
    """
    file_hash: str = Field(..., description="文件哈希")
    uploaded_chunks: List[int] = Field(default=[], description="已上传分片索引列表")
    total_chunks: int = Field(..., description="总分片数")
    is_completed: bool = Field(..., description="是否已完成上传")
    video_id: Optional[int] = Field(None, description="视频ID（秒传时返回）")
    message: str = Field(..., description="提示信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_hash": "a" * 64,
                "uploaded_chunks": [0, 1, 2, 5],
                "is_completed": False,
                "video_id": None,
                "message": "上传会话已创建，可以开始上传分片"
            }
        }


class UploadChunkRequest(BaseModel):
    """
    分片上传请求
    
    注意：实际的分片数据通过 multipart/form-data 上传
    这个 Schema 用于验证表单字段
    """
    file_hash: str = Field(..., min_length=64, max_length=64, description="文件哈希")
    chunk_index: int = Field(..., ge=0, description="分片索引（从0开始）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_hash": "a" * 64,
                "chunk_index": 5
            }
        }


class UploadChunkResponse(BaseModel):
    """分片上传响应"""
    message: str = Field(..., description="提示信息")
    chunk_index: int = Field(..., description="已上传分片索引")
    uploaded_chunks_count: int = Field(..., description="已上传分片总数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "分片 5 上传成功",
                "chunk_index": 5,
                "uploaded_chunks_count": 6
            }
        }


class UploadFinishRequest(BaseModel):
    """
    上传完成请求
    
    为什么需要这个接口：
        - 通知服务器所有分片已上传
        - 触发分片合并和转码任务
        - 创建视频记录
    """
    file_hash: str = Field(..., min_length=64, max_length=64, description="文件哈希")
    title: str = Field(..., min_length=1, max_length=100, description="视频标题")
    description: Optional[str] = Field(None, max_length=1000, description="视频描述")
    category_id: int = Field(..., gt=0, description="分类ID")
    cover_url: Optional[str] = Field(None, max_length=255, description="封面图URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_hash": "a" * 64,
                "title": "我的科普视频",
                "description": "这是一个关于量子力学的科普视频",
                "category_id": 1,
                "cover_url": "/uploads/covers/cover.jpg"
            }
        }


class UploadFinishResponse(BaseModel):
    """上传完成响应"""
    video_id: int = Field(..., description="视频ID")
    message: str = Field(..., description="提示信息")
    status: str = Field(..., description="视频状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": 123,
                "message": "视频上传成功，正在转码中",
                "status": "transcoding"
            }
        }


class UploadProgressResponse(BaseModel):
    """上传进度查询响应"""
    file_hash: str = Field(..., description="文件哈希")
    total_chunks: int = Field(..., description="总分片数")
    uploaded_chunks: List[int] = Field(..., description="已上传分片索引列表")
    uploaded_chunks_count: int = Field(..., description="已上传分片数量")
    progress_percentage: float = Field(..., description="上传进度百分比")
    is_completed: bool = Field(..., description="是否完成上传")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_hash": "a" * 64,
                "total_chunks": 100,
                "uploaded_chunks": [0, 1, 2, 3, 4, 5],
                "uploaded_chunks_count": 6,
                "progress_percentage": 6.0,
                "is_completed": False
            }
        }
