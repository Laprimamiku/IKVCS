"""
上传业务逻辑服务

需求：3.1-3.6
"""
import os
import shutil
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from typing import List, Optional, Tuple
import logging

from app.models.upload import UploadSession
from app.models.video import Video
from app.core.redis import get_redis
from app.schemas.upload import UploadInitRequest

logger = logging.getLogger(__name__)


class UploadService:
    """
    上传服务类
    
    类比 Java：
        @Service
        public class UploadService {
            @Autowired
            private UploadSessionRepository uploadSessionRepository;
            
            @Autowired
            private RedisTemplate redisTemplate;
            
            public UploadInitResponse initUpload(UploadInitDTO dto) { ... }
            public void uploadChunk(String fileHash, int chunkIndex, MultipartFile file) { ... }
            public VideoDTO finishUpload(UploadFinishDTO dto) { ... }
        }
    """
    
    # 上传临时目录
    UPLOAD_TEMP_DIR = "uploads/temp"
    # 最终视频存储目录
    VIDEO_STORAGE_DIR = "videos"
    
    @staticmethod
    def _ensure_directories():
        """确保上传目录存在"""
        os.makedirs(UploadService.UPLOAD_TEMP_DIR, exist_ok=True)
        os.makedirs(UploadService.VIDEO_STORAGE_DIR, exist_ok=True)
    
    @staticmethod
    def init_upload(
        db: Session,
        user_id: int,
        upload_data: UploadInitRequest
    ) -> Tuple[UploadSession, List[int], bool]:
        """
        初始化上传
        
        需求：3.1, 3.2
        
        流程：
        1. 检查文件哈希是否已存在（秒传检测）
        2. 如果存在且已完成，返回已存在视频
        3. 如果存在但未完成，返回已上传分片列表（断点续传）
        4. 如果不存在，创建新的上传会话
        5. 在 Redis 中初始化 BitMap
        
        返回：
            (upload_session, uploaded_chunks, is_instant_upload)
        
        为什么这样写：
            - 秒传：避免重复上传相同文件
            - 断点续传：网络中断后可以继续
            - Redis BitMap：高效记录分片状态
        """
        try:
            logger.info(f"开始初始化上传：file_hash={upload_data.file_hash}, user_id={user_id}")
            UploadService._ensure_directories()
            
            # 1. 检查是否已存在上传会话
            logger.info(f"查询上传会话：{upload_data.file_hash}")
            existing_session = db.query(UploadSession).filter(
                UploadSession.file_hash == upload_data.file_hash
            ).first()
            
            if existing_session:
                # 2. 秒传检测：如果已完成上传
                if existing_session.is_completed and existing_session.video_id:
                    logger.info(f"秒传检测：文件 {upload_data.file_hash} 已存在")
                    uploaded_chunks = list(range(existing_session.total_chunks))
                    return existing_session, uploaded_chunks, True
                
                # 3. 断点续传：返回已上传分片列表
                logger.info(f"断点续传：文件 {upload_data.file_hash} 未完成上传")
                
                # 确保 Redis BitMap 存在（可能已过期或被删除）
                try:
                    redis_client = get_redis()
                    redis_key = f"upload:{upload_data.file_hash}"
                    # 检查 BitMap 是否存在
                    if not redis_client.exists(redis_key):
                        logger.info(f"断点续传：BitMap 不存在，重新初始化：{redis_key}")
                        # 初始化 BitMap：设置第一个 bit 为 0（未上传）
                        redis_client.setbit(redis_key, 0, 0)
                        # 设置过期时间：7 天
                        redis_client.expire(redis_key, 7 * 24 * 3600)
                        logger.info(f"断点续传：BitMap 重新初始化成功：{redis_key}")
                    else:
                        logger.info(f"断点续传：BitMap 已存在：{redis_key}")
                except Exception as e:
                    logger.error(f"断点续传：Redis BitMap 初始化失败：{e}", exc_info=True)
                    # Redis 失败不影响断点续传
                
                uploaded_chunks = UploadService._get_uploaded_chunks_from_redis(
                    upload_data.file_hash,
                    existing_session.total_chunks
                )
                return existing_session, uploaded_chunks, False
            
            # 4. 创建新的上传会话
            logger.info(f"创建新的上传会话：{upload_data.file_hash}")
            new_session = UploadSession(
                file_hash=upload_data.file_hash,
                user_id=user_id,
                file_name=upload_data.file_name,
                file_size=upload_data.file_size,
                total_chunks=upload_data.total_chunks,
                uploaded_chunks="",
                is_completed=False
            )
            
            db.add(new_session)
            logger.info("提交数据库事务...")
            db.commit()
            logger.info("刷新会话对象...")
            db.refresh(new_session)
            logger.info(f"上传会话创建成功：{new_session.file_hash}")
            
            # 5. 在 Redis 中初始化 BitMap
            try:
                redis_client = get_redis()
                redis_key = f"upload:{upload_data.file_hash}"
                # 初始化 BitMap：设置第一个 bit 为 0（未上传）
                # 这样会创建 BitMap key，否则只设置 expire 不会创建 key
                result = redis_client.setbit(redis_key, 0, 0)
                logger.debug(f"Redis SETBIT 结果：{result}, key: {redis_key}")
                # 设置过期时间：7 天
                expire_result = redis_client.expire(redis_key, 7 * 24 * 3600)
                logger.debug(f"Redis EXPIRE 结果：{expire_result}, key: {redis_key}")
                # 验证 key 是否存在
                exists = redis_client.exists(redis_key)
                logger.info(f"Redis BitMap 初始化成功：{redis_key}, exists={exists}")
                if not exists:
                    logger.warning(f"Redis BitMap 初始化后 key 不存在，可能 Redis 连接失败")
            except Exception as e:
                logger.error(f"Redis 初始化失败：{e}", exc_info=True)
                # Redis 失败不影响上传会话创建，但记录详细错误
            
            logger.info(f"初始化上传完成：{upload_data.file_hash}")
            return new_session, [], False
            
        except Exception as e:
            logger.error(f"初始化上传失败：{e}", exc_info=True)
            db.rollback()
            raise
    
    @staticmethod
    def upload_chunk(
        db: Session,
        file_hash: str,
        chunk_index: int,
        chunk_file: UploadFile
    ) -> int:
        """
        上传分片
        
        需求：3.3, 3.4
        
        流程：
        1. 验证上传会话是否存在
        2. 验证分片索引是否有效
        3. 保存分片文件到临时目录
        4. 在 Redis BitMap 中标记分片已上传
        5. 更新数据库中的 uploaded_chunks 字段
        
        返回：
            已上传分片总数
        
        为什么这样写：
            - 分片文件命名：{file_hash}/chunk_{index}
            - Redis BitMap：O(1) 时间复杂度标记分片
            - 数据库记录：持久化上传进度
        """
        # 1. 验证上传会话
        session = db.query(UploadSession).filter(
            UploadSession.file_hash == file_hash
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"上传会话 {file_hash} 不存在"
            )
        
        if session.is_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传已完成，无法继续上传分片"
            )
        
        # 2. 验证分片索引
        if chunk_index < 0 or chunk_index >= session.total_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分片索引 {chunk_index} 无效（总分片数：{session.total_chunks}）"
            )
        
        # 3. 保存分片文件
        chunk_dir = os.path.join(UploadService.UPLOAD_TEMP_DIR, file_hash)
        os.makedirs(chunk_dir, exist_ok=True)
        
        chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}")
        
        try:
            with open(chunk_path, "wb") as f:
                shutil.copyfileobj(chunk_file.file, f)
        except Exception as e:
            logger.error(f"保存分片失败：{e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"保存分片失败：{str(e)}"
            )
        
        # 4. 在 Redis 中标记分片已上传
        try:
            redis_client = get_redis()
            redis_key = f"upload:{file_hash}"
            redis_client.setbit(redis_key, chunk_index, 1)
        except Exception as e:
            logger.error(f"Redis 标记分片失败：{e}")
            # Redis 失败不影响分片上传
        
        # 5. 更新数据库（获取已上传分片列表）
        uploaded_chunks = UploadService._get_uploaded_chunks_from_redis(
            file_hash,
            session.total_chunks
        )
        session.uploaded_chunks = ",".join(map(str, uploaded_chunks))
        db.commit()
        
        logger.info(f"分片上传成功：{file_hash} - chunk {chunk_index}")
        return len(uploaded_chunks)
    
    @staticmethod
    def finish_upload(
        db: Session,
        user_id: int,
        file_hash: str,
        title: str,
        description: Optional[str],
        category_id: int,
        cover_url: Optional[str]
    ) -> Video:
        """
        完成上传
        
        需求：3.5, 3.6
        
        流程：
        1. 验证上传会话
        2. 验证所有分片已上传
        3. 合并分片文件
        4. 创建视频记录（status=0 转码中）
        5. 标记上传会话为已完成
        6. 清理 Redis 和临时文件
        
        返回：
            Video 对象
        
        为什么这样写：
            - 验证完整性：确保所有分片都已上传
            - 合并文件：按顺序拼接分片
            - 创建视频：状态为"转码中"，等待后台任务处理
        """
        # 1. 验证上传会话
        session = db.query(UploadSession).filter(
            UploadSession.file_hash == file_hash
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"上传会话 {file_hash} 不存在"
            )
        
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此上传会话"
            )
        
        if session.is_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传已完成"
            )
        
        # 2. 验证所有分片已上传
        uploaded_chunks = UploadService._get_uploaded_chunks_from_redis(
            file_hash,
            session.total_chunks
        )
        
        if len(uploaded_chunks) != session.total_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"上传未完成：已上传 {len(uploaded_chunks)}/{session.total_chunks} 个分片"
            )
        
        # 3. 合并分片文件
        final_file_path = UploadService._merge_chunks(file_hash, session.file_name)
        
        # 4. 创建视频记录
        video = Video(
            uploader_id=user_id,
            category_id=category_id,
            title=title,
            description=description,
            cover_url=cover_url,
            video_url=None,  # 转码后更新
            status=0,  # 0=转码中
            duration=0  # 转码后更新
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # 5. 标记上传会话为已完成
        session.is_completed = True
        session.video_id = video.id
        db.commit()
        
        # 6. 清理 Redis
        try:
            redis_client = get_redis()
            redis_client.delete(f"upload:{file_hash}")
        except Exception as e:
            logger.error(f"Redis 清理失败：{e}")
            # Redis 清理失败不影响上传完成
        
        logger.info(f"上传完成：{file_hash} -> video_id={video.id}")
        return video
    
    @staticmethod
    def _get_uploaded_chunks_from_redis(file_hash: str, total_chunks: int) -> List[int]:
        """
        从 Redis BitMap 获取已上传分片列表
        
        为什么使用 BitMap：
            - 内存高效：1 个分片只占 1 bit
            - 查询快速：O(N) 时间复杂度
            - 100 个分片只需要 13 字节
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
            # Redis 失败时返回空列表
            return []
    
    @staticmethod
    def _merge_chunks(file_hash: str, file_name: str) -> str:
        """
        合并分片文件
        
        流程：
        1. 按顺序读取所有分片
        2. 拼接到最终文件
        3. 删除临时分片文件
        
        返回：
            最终文件路径
        
        为什么这样写：
            - 顺序合并：确保文件完整性
            - 清理临时文件：释放磁盘空间
        """
        chunk_dir = os.path.join(UploadService.UPLOAD_TEMP_DIR, file_hash)
        final_file_path = os.path.join(UploadService.VIDEO_STORAGE_DIR, f"{file_hash}_{file_name}")
        
        try:
            with open(final_file_path, "wb") as final_file:
                chunk_index = 0
                while True:
                    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}")
                    if not os.path.exists(chunk_path):
                        break
                    
                    with open(chunk_path, "rb") as chunk_file:
                        shutil.copyfileobj(chunk_file, final_file)
                    
                    chunk_index += 1
            
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
    def get_upload_progress(db: Session, file_hash: str) -> Tuple[UploadSession, List[int]]:
        """
        查询上传进度
        
        需求：3.4
        
        返回：
            (upload_session, uploaded_chunks)
        """
        session = db.query(UploadSession).filter(
            UploadSession.file_hash == file_hash
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"上传会话 {file_hash} 不存在"
            )
        
        # 优先从 Redis 获取，如果 Redis 失败则从数据库解析
        uploaded_chunks = UploadService._get_uploaded_chunks_from_redis(
            file_hash,
            session.total_chunks
        )
        
        # 如果 Redis 返回空列表，尝试从数据库解析
        if not uploaded_chunks and session.uploaded_chunks:
            try:
                uploaded_chunks = [int(x) for x in session.uploaded_chunks.split(",") if x.strip()]
            except Exception as e:
                logger.error(f"解析 uploaded_chunks 失败：{e}")
                uploaded_chunks = []
        
        return session, uploaded_chunks
