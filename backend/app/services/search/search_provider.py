"""
搜索提供者抽象接口

为未来 ES 可插拔设计，当前实现 MySQL 版本
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class SearchProvider(ABC):
    """搜索提供者抽象基类"""
    
    @abstractmethod
    def search_videos(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        搜索视频
        
        Args:
            query: 搜索关键词
            filters: 筛选条件
                - category_id: 分类ID
                - status: 状态（2=已发布）
                - created_from: 创建时间起始
                - created_to: 创建时间结束
                - duration_min: 时长最小值（秒）
                - duration_max: 时长最大值（秒）
                - uploader_id: 上传者ID
            sort: 排序方式
                - field: 排序字段（created/view/like）
                - order: 排序方向（asc/desc）
            page: 页码
            page_size: 每页数量
            
        Returns:
            {
                "items": List[Video],  # 视频列表
                "total": int,  # 总数
                "page": int,
                "page_size": int,
                "suggestions": Optional[List[str]],  # 搜索建议（可选）
                "highlights": Optional[Dict[int, str]]  # 高亮文本（可选，ES 使用）
            }
        """
        pass

