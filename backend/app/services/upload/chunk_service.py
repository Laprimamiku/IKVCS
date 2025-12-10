"""
分片处理服务
职责：处理分片上传、验证、Redis BitMap操作
"""
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
import logging

from app.core.redis import get_redis
from app.repositories.upload_repository import UploadSessionRepository

logger = logging.getLogger(__name__)


class ChunkService:
    """分片处理服务"""
    
    @staticmethod
    def validate_chunk_index(
        session,
        chunk_index: int
    ):
        """
        验证分片索引是否有效
        
        Args:
            session: 上传会话
            chunk_index: 分片索引
            
        Raises:
            HTTPException: 索引无效时抛出
        """
        if chunk_index < 0 or chunk_index >= session.total_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分片索引 {chunk_index} 无效（总分片数：{session.total_chunks}）"
            )
    
    @staticmethod
    def mark_chunk_uploaded(
        file_hash: str,
        chunk_index: int
    ) -> bool:
        """
        在Redis BitMap中标记分片已上传
        
        Args:
            file_hash: 文件哈希
            chunk_index: 分片索引
            
        Returns:
            bool: 是否成功
        """
        try:
            redis_client = get_redis()
            redis_key = f"upload:{file_hash}"
            redis_client.setbit(redis_key, chunk_index, 1)
            logger.debug(f"分片标记成功：{file_hash} - chunk {chunk_index}")
            return True
        except Exception as e:
            logger.error(f"Redis 标记分片失败：{e}")
            return False
    
    @staticmethod
    def get_uploaded_chunks(
        file_hash: str,
        total_chunks: int
    ) -> List[int]:
        """
        从Redis BitMap获取已上传分片列表
        
        Args:
            file_hash: 文件哈希
            total_chunks: 总分片数
            
        Returns:
            List[int]: 已上传分片索引列表
        """
        try:
            redis_client = get_redis()
            redis_key = f"upload:{file_hash}"
            
            uploaded = []
            for i in range(total_chunks):
                if redis_client.getbit(redis_key, i):
                    uploaded.append(i)
            
            return uploaded
        except Exception as e:
            logger.error(f"Redis 读取失败：{e}")
            return []
    
    @staticmethod
    def update_session_chunks(
        db: Session,
        file_hash: str,
        uploaded_chunks: List[int]
    ):
        """
        更新会话中的已上传分片列表
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            uploaded_chunks: 已上传分片列表
        """
        session = UploadSessionRepository.get_by_file_hash(db, file_hash)
        if session:
            session.uploaded_chunks = ",".join(map(str, uploaded_chunks))
            db.commit()
    
    @staticmethod
    def validate_all_chunks_uploaded(
        uploaded_chunks: List[int],
        total_chunks: int
    ):
        """
        验证所有分片是否已上传
        
        Args:
            uploaded_chunks: 已上传分片列表
            total_chunks: 总分片数
            
        Raises:
            HTTPException: 分片不完整时抛出
        """
        if len(uploaded_chunks) != total_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"上传未完成：已上传 {len(uploaded_chunks)}/{total_chunks} 个分片"
            )
    
    @staticmethod
    def cleanup_redis(file_hash: str) -> bool:
        """
        清理Redis中的上传记录
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            bool: 是否成功
        """
        try:
            redis_client = get_redis()
            redis_client.delete(f"upload:{file_hash}")
            logger.info(f"Redis 清理成功：{file_hash}")
            return True
        except Exception as e:
            logger.error(f"Redis 清理失败：{e}")
            return False

