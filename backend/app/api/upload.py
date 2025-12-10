"""
上传管理 API

这个文件的作用：
1. 初始化上传（POST /api/v1/upload/init）
2. 上传分片（POST /api/v1/upload/chunk）
3. 完成上传（POST /api/v1/upload/finish）
4. 查询上传进度（GET /api/v1/upload/progress/{file_hash}）

类比 Java：
    相当于 Spring Boot 的 UploadController
    
需求：3.1-3.6
"""
from fastapi import APIRouter, Depends, File, UploadFile, Form, BackgroundTasks, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.upload import (
    UploadInitRequest,
    UploadInitResponse,
    UploadChunkResponse,
    UploadFinishRequest,
    UploadFinishResponse,
    UploadProgressResponse
)
from app.services.upload.upload_orchestration_service import UploadOrchestrationService

router = APIRouter()


@router.post("/init", response_model=UploadInitResponse)
async def init_upload(
    upload_data: UploadInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    初始化上传
    
    类比 Java：
        @PostMapping("/upload/init")
        public ResponseEntity<UploadInitVO> initUpload(
            @RequestBody @Valid UploadInitDTO dto,
            @AuthenticationPrincipal User user
        ) {
            UploadSession session = uploadService.initUpload(dto, user.getId());
            return ResponseEntity.ok(session);
        }
    
    需求：3.1, 3.2
    
    流程：
    1. 检查文件哈希是否已存在（秒传检测）
    2. 如果存在且已完成，返回已存在视频（秒传）
    3. 如果存在但未完成，返回已上传分片列表（断点续传）
    4. 如果不存在，创建新的上传会话
    
    为什么这样写：
        - 秒传：避免重复上传相同文件，节省带宽和时间
        - 断点续传：网络中断后可以继续，提升用户体验
        - 前端需要先计算文件哈希（SHA-256）再调用此接口
    
    容易踩坑点：
        - 文件哈希必须是 SHA-256（64 位十六进制）
        - 前端计算哈希可以使用 Web Crypto API
        - 分片大小建议 5MB（平衡上传速度和失败重试成本）
    """
    session, uploaded_chunks, is_instant = UploadOrchestrationService.init_upload(
        db,
        current_user.id,
        upload_data
    )
    
    # 秒传：文件已存在
    if is_instant:
        return UploadInitResponse(
            file_hash=session.file_hash,
            uploaded_chunks=uploaded_chunks,
            is_completed=True,
            video_id=session.video_id,
            message="文件已存在，秒传成功"
        )
    
    # 断点续传或新上传
    return UploadInitResponse(
        file_hash=session.file_hash,
        uploaded_chunks=uploaded_chunks,
        is_completed=False,
        video_id=None,
        message=f"上传会话已创建，已上传 {len(uploaded_chunks)}/{session.total_chunks} 个分片"
    )


@router.post("/chunk", response_model=UploadChunkResponse)
async def upload_chunk(
    file_hash: str = Form(..., min_length=64, max_length=64),
    chunk_index: int = Form(..., ge=0),
    chunk: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传分片
    
    类比 Java：
        @PostMapping("/upload/chunk")
        public ResponseEntity<UploadChunkVO> uploadChunk(
            @RequestParam String fileHash,
            @RequestParam Integer chunkIndex,
            @RequestParam MultipartFile chunk,
            @AuthenticationPrincipal User user
        ) {
            uploadService.uploadChunk(fileHash, chunkIndex, chunk);
            return ResponseEntity.ok(new UploadChunkVO("上传成功"));
        }
    
    需求：3.3, 3.4
    
    流程：
    1. 验证上传会话是否存在
    2. 验证分片索引是否有效
    3. 保存分片文件到临时目录
    4. 在 Redis BitMap 中标记分片已上传
    5. 更新数据库中的 uploaded_chunks 字段
    
    为什么这样写：
        - 使用 Form 和 File：支持 multipart/form-data 上传
        - Redis BitMap：高效记录分片状态（1 个分片只占 1 bit）
        - 临时目录：分片文件保存在 uploads/temp/{file_hash}/chunk_{index}
    
    容易踩坑点：
        - 前端需要使用 FormData 上传
        - chunk_index 从 0 开始
        - 分片文件大小建议 5MB
    """
    uploaded_count = UploadOrchestrationService.upload_chunk(
        db,
        file_hash,
        chunk_index,
        chunk
    )
    
    return UploadChunkResponse(
        message=f"分片 {chunk_index} 上传成功",
        chunk_index=chunk_index,
        uploaded_chunks_count=uploaded_count
    )


@router.post("/finish", response_model=UploadFinishResponse, status_code=status.HTTP_201_CREATED)
async def finish_upload(
    finish_data: UploadFinishRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    完成上传
    
    ... (保留原有的文档)
    """
    try:
        video = UploadOrchestrationService.finish_upload(
            db,
            current_user.id,
            finish_data.file_hash,
            finish_data.title,
            finish_data.description,
            finish_data.category_id,
            finish_data.cover_url
        )
        
        # 触发后台转码任务（需求 3.6, 4.2）
        # 已有视频且已转码完成时不重复触发
        if video.status == 0 or not video.video_url:
            from app.services.transcode import TranscodeService
            background_tasks.add_task(TranscodeService.transcode_video, video.id)
        
        return UploadFinishResponse(
            video_id=video.id,
            message="视频上传成功，正在转码中",
            status="transcoding"
        )
    except HTTPException:
        # HTTPException 直接抛出，由 FastAPI 处理
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"完成上传失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"完成上传失败：{str(e)}"
        )


@router.get("/progress/{file_hash}", response_model=UploadProgressResponse)
async def get_upload_progress(
    file_hash: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询上传进度
    
    类比 Java：
        @GetMapping("/upload/progress/{fileHash}")
        public ResponseEntity<UploadProgressVO> getUploadProgress(
            @PathVariable String fileHash,
            @AuthenticationPrincipal User user
        ) {
            UploadProgress progress = uploadService.getUploadProgress(fileHash);
            return ResponseEntity.ok(progress);
        }
    
    需求：3.4
    
    为什么需要这个接口：
        - 前端可以显示上传进度条
        - 断点续传时可以知道哪些分片已上传
        - 用户刷新页面后可以恢复上传状态
    
    容易踩坑点：
        - 前端需要定期轮询此接口（建议 1-2 秒间隔）
        - 或者使用 WebSocket 实时推送进度（更高级）
    """
    session, uploaded_chunks = UploadOrchestrationService.get_upload_progress(db, file_hash)
    
    progress_percentage = (len(uploaded_chunks) / session.total_chunks) * 100 if session.total_chunks > 0 else 0
    
    return UploadProgressResponse(
        file_hash=session.file_hash,
        total_chunks=session.total_chunks,
        uploaded_chunks=uploaded_chunks,
        uploaded_chunks_count=len(uploaded_chunks),
        progress_percentage=round(progress_percentage, 2),
        is_completed=session.is_completed
    )
