"""
文件存储服务
职责：处理文件存储相关的操作（保存分片、合并文件、目录管理）
"""
import os
import shutil
from typing import Optional
from fastapi import UploadFile, HTTPException, status
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileStorageService:
    """文件存储服务"""
    
    @staticmethod
    def ensure_directories():
        """确保上传目录存在"""
        # 创建所有必要的目录
        os.makedirs(settings.UPLOAD_TEMP_DIR, exist_ok=True)
        os.makedirs(settings.UPLOAD_AVATAR_DIR, exist_ok=True)
        os.makedirs(settings.UPLOAD_COVER_DIR, exist_ok=True)
        os.makedirs(settings.UPLOAD_SUBTITLE_DIR, exist_ok=True)
        os.makedirs(settings.VIDEO_ORIGINAL_DIR, exist_ok=True)
        os.makedirs(settings.VIDEO_HLS_DIR, exist_ok=True)
        logger.debug(f"确保存储目录存在：{settings.STORAGE_ROOT}")

    
    @staticmethod
    def save_chunk(
        file_hash: str,
        chunk_index: int,
        chunk_file: UploadFile
    ) -> str:
        """
        保存分片文件到临时目录
        
        Args:
            file_hash: 文件哈希
            chunk_index: 分片索引
            chunk_file: 分片文件
            
        Returns:
            str: 分片文件路径
            
        Raises:
            HTTPException: 保存失败时抛出
        """
        FileStorageService.ensure_directories()
        
        chunk_dir = os.path.join(settings.UPLOAD_TEMP_DIR, file_hash)
        os.makedirs(chunk_dir, exist_ok=True)
        
        chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}")
        
        try:
            with open(chunk_path, "wb") as f:
                shutil.copyfileobj(chunk_file.file, f)
            logger.info(f"分片保存成功：{chunk_path}")
            return chunk_path
        except Exception as e:
            logger.error(f"保存分片失败：{e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"保存分片失败：{str(e)}"
            )
    
    @staticmethod
    def merge_chunks(
        file_hash: str,
        file_name: str,
        total_chunks: int
    ) -> str:
        """
        合并分片文件
        
        Args:
            file_hash: 文件哈希
            file_name: 原始文件名
            total_chunks: 总分片数
            
        Returns:
            str: 最终文件路径
            
        Raises:
            HTTPException: 合并失败时抛出
        """
        chunk_dir = os.path.join(settings.UPLOAD_TEMP_DIR, file_hash)
        final_file_path = os.path.join(settings.VIDEO_ORIGINAL_DIR, f"{file_hash}_{file_name}")

        
        try:
            if not os.path.exists(chunk_dir):
                raise FileNotFoundError(f"分片目录不存在：{chunk_dir}")
            
            with open(final_file_path, "wb") as final_file:
                for chunk_index in range(total_chunks):
                    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}")
                    if not os.path.exists(chunk_path):
                        raise FileNotFoundError(f"分片文件不存在：{chunk_path}")
                    
                    with open(chunk_path, "rb") as chunk_file:
                        shutil.copyfileobj(chunk_file, final_file)
            
            # 删除临时分片目录
            shutil.rmtree(chunk_dir)
            
            logger.info(f"分片合并成功：{final_file_path}")
            return final_file_path
            
        except Exception as e:
            logger.error(f"分片合并失败：{e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"分片合并失败：{str(e)}"
            )
    
    @staticmethod
    def check_chunk_exists(
        file_hash: str,
        chunk_index: int
    ) -> bool:
        """
        检查分片文件是否存在
        
        Args:
            file_hash: 文件哈希
            chunk_index: 分片索引
            
        Returns:
            bool: 是否存在
        """
        chunk_path = os.path.join(
            settings.UPLOAD_TEMP_DIR, file_hash, f"chunk_{chunk_index}"
        )
        return os.path.exists(chunk_path)
    
    @staticmethod
    def check_chunk_dir_exists(file_hash: str) -> bool:
        """
        检查分片目录是否存在
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            bool: 是否存在
        """
        chunk_dir = os.path.join(settings.UPLOAD_TEMP_DIR, file_hash)
        return os.path.exists(chunk_dir)

