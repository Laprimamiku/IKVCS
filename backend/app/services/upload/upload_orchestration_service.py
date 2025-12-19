"""
上传编排服务
职责：协调各个服务，实现完整的上传流程
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
import logging

from app.models.upload import UploadSession
from app.models.video import Video
from app.schemas.upload import UploadInitRequest
from app.services.upload.file_storage_service import FileStorageService
from app.services.upload.session_service import SessionService
from app.services.upload.chunk_service import ChunkService
from app.repositories.video_repository import VideoRepository
from app.repositories.upload_repository import UploadSessionRepository

logger = logging.getLogger(__name__)


class UploadOrchestrationService:
    """上传编排服务"""
    
    @staticmethod
    def init_upload(
        db: Session,
        user_id: int,
        upload_data: UploadInitRequest
    ) -> Tuple[UploadSession, List[int], bool]:
        """
        初始化上传（编排：会话管理 + 秒传检测 + Redis初始化）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            upload_data: 上传初始化数据
            
        Returns:
            Tuple[UploadSession, List[int], bool]: (会话, 已上传分片列表, 是否秒传)
        """
        try:
            FileStorageService.ensure_directories()
            
            # 1. 检查秒传
            instant_result = SessionService.check_instant_upload(db, upload_data.file_hash)
            if instant_result:
                session, video = instant_result
                uploaded_chunks = list(range(session.total_chunks))
                logger.info(f"秒传检测：文件 {upload_data.file_hash} 已存在")
                return session, uploaded_chunks, True
            
            # 2. 检查断点续传
            existing_session = SessionService.get_session_by_hash(db, upload_data.file_hash)
            if existing_session:
                # 检查会话是否属于当前用户
                if existing_session.user_id != user_id:
                    # 会话不属于当前用户
                    # 如果文件已完成上传（有 video_id），应该走秒传逻辑
                    if existing_session.is_completed and existing_session.video_id:
                        logger.info(
                            f"文件 {upload_data.file_hash} 已由用户 {existing_session.user_id} 完成上传，"
                            f"当前用户 {user_id} 触发秒传"
                        )
                        # 检查视频是否存在
                        from app.repositories.video_repository import VideoRepository
                        video = VideoRepository.get_by_id(db, existing_session.video_id)
                        if video:
                            uploaded_chunks = list(range(existing_session.total_chunks))
                            return existing_session, uploaded_chunks, True
                        else:
                            logger.warning(f"视频 {existing_session.video_id} 不存在，但会话标记为已完成")
                            # 视频不存在，重置会话状态
                            existing_session.is_completed = False
                            existing_session.video_id = None
                            db.commit()
                    
                    # 文件未完成且属于其他用户，返回错误
                    logger.warning(
                        f"文件 {upload_data.file_hash} 的上传会话属于用户 {existing_session.user_id}，"
                        f"当前用户 {user_id} 无法创建新会话（主键冲突）"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"该文件正在被其他用户上传中，请稍后重试。如果文件已上传完成，系统会自动触发秒传。"
                    )
                
                logger.info(f"断点续传：文件 {upload_data.file_hash} 未完成上传")
                
                # 检查并更新 total_chunks（如果前端传入的值与数据库不一致）
                # 这可能是由于之前上传时计算错误，或者文件大小发生了变化
                if existing_session.total_chunks != upload_data.total_chunks:
                    logger.warning(
                        f"总分片数不一致：数据库={existing_session.total_chunks}，前端={upload_data.total_chunks}，"
                        f"使用前端传入的值（更准确）"
                    )
                    existing_session.total_chunks = upload_data.total_chunks
                    db.commit()
                    db.refresh(existing_session)
                
                # 确保 Redis BitMap 存在
                SessionService.init_redis_bitmap(upload_data.file_hash)
                # 获取已上传分片
                uploaded_chunks = ChunkService.get_uploaded_chunks(
                    upload_data.file_hash,
                    existing_session.total_chunks
                )
                return existing_session, uploaded_chunks, False
            
            # 3. 创建新会话
            new_session = SessionService.create_session(db, user_id, upload_data)
            
            # 4. 初始化 Redis BitMap
            SessionService.init_redis_bitmap(upload_data.file_hash)
            
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
        chunk_file: UploadFile,
        user_id: Optional[int] = None
    ) -> int:
        """
        上传分片（编排：会话验证 + 文件存储 + Redis标记 + 数据库更新）
        
        Args:
            db: 数据库会话
            file_hash: 文件哈希
            chunk_index: 分片索引
            chunk_file: 分片文件
            user_id: 用户ID（可选，用于权限验证）
            
        Returns:
            int: 已上传分片总数
        """
        # 1. 验证上传会话
        session = SessionService.get_session_by_hash(db, file_hash)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"上传会话 {file_hash} 不存在"
            )
        
        # 验证用户权限（如果提供了 user_id）
        if user_id is not None and session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此上传会话"
            )
        
        if session.is_completed:
            # 如果分片目录已不存在（例如之前失败被清理），重置会话允许重新上传
            if not FileStorageService.check_chunk_dir_exists(file_hash):
                ChunkService.cleanup_redis(file_hash)
                SessionService.reset_session_for_reupload(db, file_hash)
                # 重新初始化 Redis BitMap
                SessionService.init_redis_bitmap(file_hash)
            else:
                # 已完成且目录存在，直接返回已上传数量
                uploaded_chunks = ChunkService.get_uploaded_chunks(
                    file_hash,
                    session.total_chunks
                )
                return len(uploaded_chunks)
        
        # 2. 验证分片索引
        logger.info(f"验证分片索引：chunk_index={chunk_index} (type: {type(chunk_index)}), session.total_chunks={session.total_chunks} (type: {type(session.total_chunks)})")
        ChunkService.validate_chunk_index(session, chunk_index)
        
        # 3. 保存分片文件
        FileStorageService.save_chunk(file_hash, chunk_index, chunk_file)
        
        # 4. 在 Redis 中标记分片已上传
        ChunkService.mark_chunk_uploaded(file_hash, chunk_index)
        
        # 5. 更新数据库
        uploaded_chunks = ChunkService.get_uploaded_chunks(
            file_hash,
            session.total_chunks
        )
        ChunkService.update_session_chunks(db, session.file_hash, uploaded_chunks)
        
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
        完成上传（编排：会话验证 + 分片验证 + 文件合并 + 视频创建 + 清理）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            file_hash: 文件哈希
            title: 视频标题
            description: 视频描述
            category_id: 分类ID
            cover_url: 封面URL
            
        Returns:
            Video: 创建的视频对象
        """
        # 1. 验证上传会话
        session = SessionService.get_session_by_hash(db, file_hash)
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
        
        # 2. 验证所有分片已上传
        uploaded_chunks = ChunkService.get_uploaded_chunks(
            file_hash,
            session.total_chunks
        )
        
        # 如果 Redis 读取不到，尝试使用数据库中的 uploaded_chunks 兜底
        if not uploaded_chunks and session.uploaded_chunks:
            try:
                uploaded_chunks = [
                    int(x) for x in session.uploaded_chunks.split(",") if x.strip()
                ]
            except Exception as e:
                logger.error(f"解析数据库分片列表失败：{e}")
                uploaded_chunks = []
        
        # 如果会话已标记完成且有 video_id，处理幂等
        if session.is_completed and session.video_id:
            existing_video = VideoRepository.get_by_id(db, session.video_id)
            if existing_video:
                # 检查元信息是否变化
                meta_changed = (
                    title != existing_video.title
                    or (description or "") != (existing_video.description or "")
                    or category_id != existing_video.category_id
                    or cover_url
                )
                if not meta_changed:
                    logger.info(f"上传会话已完成，返回已有视频：video_id={session.video_id}")
                    return existing_video
        
        # 3. 验证分片完整性
        ChunkService.validate_all_chunks_uploaded(uploaded_chunks, session.total_chunks)
        
        # 4. 验证分片目录存在
        if not FileStorageService.check_chunk_dir_exists(file_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="分片临时目录不存在，请重新上传"
            )
        
        # 5. 合并分片文件
        final_file_path = FileStorageService.merge_chunks(
            file_hash,
            session.file_name,
            session.total_chunks
        )
        
        # 6. 创建视频记录
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
        
        # 7. 标记上传会话为已完成
        SessionService.mark_session_completed(db, session.file_hash, video.id)
        
        # 8. 清理 Redis
        ChunkService.cleanup_redis(file_hash)
        
        logger.info(f"上传完成：{file_hash} -> video_id={video.id}")
        return video
    
    @staticmethod
    def get_upload_progress(
        db: Session,
        file_hash: str
    ) -> Tuple[UploadSession, List[int]]:
        """
        查询上传进度（编排：会话查询 + Redis查询）
        
        Args:
            db: 数据库会话
            file_hash: 文件哈希
            
        Returns:
            Tuple[UploadSession, List[int]]: (上传会话, 已上传分片列表)
        """
        session = SessionService.get_session_by_hash(db, file_hash)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"上传会话 {file_hash} 不存在"
            )
        
        # 优先从 Redis 获取，如果 Redis 失败则从数据库解析
        uploaded_chunks = ChunkService.get_uploaded_chunks(
            file_hash,
            session.total_chunks
        )
        
        # 如果 Redis 返回空列表，尝试从数据库解析
        if not uploaded_chunks and session.uploaded_chunks:
            try:
                uploaded_chunks = [
                    int(x) for x in session.uploaded_chunks.split(",") if x.strip()
                ]
            except Exception as e:
                logger.error(f"解析 uploaded_chunks 失败：{e}")
                uploaded_chunks = []
        
        return session, uploaded_chunks

