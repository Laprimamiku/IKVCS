"""
视频管理 API

功能：
1. 获取视频列表（已发布）
2. 获取视频详情（并增加播放量）
3. 查询/触发转码（开发调试）
4. 上传封面、字幕（仅上传者）
5. 增加播放量（公开）
"""

import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, UploadFile, File, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc


from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, ForbiddenException, ValidationException
from app.core.response import success_response
from app.core.transaction import transaction
from app.core.config import settings
from app.models.user import User
from app.models.video import Video
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.schemas.video import (
    VideoListRequest,
    VideoListResponse,
    VideoDetailResponse,
    VideoUpdateRequest,
    SubtitleUploadResponse,
    CoverUploadResponse,
    VideoStatusResponse,
    TranscodeTestRequest,
    TranscodeTestResponse,
)
from app.services.video import (
    VideoQueryService,
    VideoStatsService,
    VideoManagementService,
    VideoResponseBuilder,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询视频状态（开发/调试专用接口）
    
    注意：此接口仅用于开发和调试，生产环境应通过视频详情接口获取状态
    """
    from app.services.video.video_status_service import VideoStatusService
    
    status_info = VideoStatusService.get_video_status(db, video_id)
    return VideoStatusResponse(**status_info)


@router.post("/{video_id}/transcode", response_model=TranscodeTestResponse)
async def test_transcode(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    触发转码（开发/调试专用接口）
    
    注意：此接口仅用于开发和调试，生产环境应通过上传流程自动触发转码
    """
    # 仅在开发环境允许使用此接口
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此接口仅在开发环境可用"
        )
    
    from app.services.video.video_status_service import VideoStatusService
    from app.services.transcode import TranscodeService
    
    # 调用 Service 层处理转码触发逻辑
    status_info = VideoStatusService.trigger_transcode(db, video_id)
    
    # 启动后台转码任务
    background_tasks.add_task(TranscodeService.transcode_video, video_id)
    
    return TranscodeTestResponse(**status_info)


@router.get("", response_model=VideoListResponse)
async def get_video_list(
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    获取视频列表（已发布）
    
    路由层只负责参数验证和调用 Service，所有业务逻辑在 Service 层
    """
    # 参数验证（也可以使用 Pydantic 的 Field 验证）
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    # 调用 Service 层获取响应（包含所有业务逻辑）
    return VideoResponseBuilder.get_video_list_response(
        db=db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        keyword=keyword,
    )


@router.get("/my", response_model=VideoListResponse)
async def get_my_videos(
    page: int = 1,
    page_size: int = 20,
    status: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户上传的视频列表
    
    路由层只负责参数验证和调用 Service，所有业务逻辑在 Service 层
    
    注意：此路由必须在 /{video_id} 之前定义，否则会被误匹配
    """
    # 参数验证
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    # 调用 Service 层获取响应
    return VideoResponseBuilder.get_user_video_list_response(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video_detail(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    获取视频详情并增加播放量
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    # 增加播放量
    VideoStatsService.increment_view_count(db, video_id)
    
    # 如果用户已登录，记录观看历史
    if current_user:
        from app.repositories.watch_history_repository import WatchHistoryRepository
        try:
            WatchHistoryRepository.record_watch(db, current_user.id, video_id)
        except Exception as e:
            logger.warning(f"记录观看历史失败: {e}")
    
    # 获取视频详情响应（包含所有数据组装逻辑）
    video_detail = VideoResponseBuilder.get_video_detail_response(db, video_id)
    if not video_detail:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return video_detail


@router.post("/{video_id}/view")
async def increase_view_count(
    video_id: int,
    db: Session = Depends(get_db),
):
    """增加视频播放量（公开接口）"""
    success = VideoStatsService.increment_view_count(db, video_id)
    if not success:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    view_count = VideoStatsService.get_merged_view_count(db, video_id)
    return success_response(
        data={"view_count": view_count},
        message="播放量已记录"
    )
@router.post("/{video_id}/cover", response_model=CoverUploadResponse)
async def upload_video_cover(
    video_id: int,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传封面图片（JPG/PNG/WEBP，<=5MB，仅上传者可操作）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以上传封面")

    ext = os.path.splitext(cover.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise ValidationException(message="封面格式不支持，仅支持 JPG/PNG/WEBP")

    content = await cover.read()
    if len(content) > 5 * 1024 * 1024:
        raise ValidationException(message="封面文件过大，最大 5MB")

    # 使用配置的封面目录，确保路径正确
    # 静态文件挂载：/uploads -> ./storage/uploads
    # 封面文件路径：./storage/uploads/covers/{filename}
    # URL路径应该是：/uploads/covers/{filename}
    cover_dir = settings.UPLOAD_COVER_DIR
    unique_filename = f"{video_id}_cover_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(cover_dir, unique_filename)
    os.makedirs(cover_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    # 生成URL路径：/uploads/covers/{filename}
    cover_url = f"/uploads/covers/{unique_filename}"

    # 使用事务管理，确保数据一致性
    try:
        with transaction(db):
            video.cover_url = cover_url
            # 事务上下文管理器会自动提交或回滚
    except Exception as e:
        # 如果数据库更新失败，删除已保存的文件
        file_path = os.path.join(cover_dir, unique_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"封面上传失败，已删除文件: {e}")
        raise

    logger.info(f"视频 {video_id} 封面上传成功：{cover_url}")
    return CoverUploadResponse(message="封面上传成功", cover_url=cover_url, video_id=video_id)


@router.post("/{video_id}/subtitle", response_model=SubtitleUploadResponse)
async def upload_video_subtitle(
    video_id: int,
    subtitle: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传字幕文件（SRT/VTT/JSON/ASS，仅上传者可操作）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以上传字幕")

    ext = os.path.splitext(subtitle.filename or "")[1].lower()
    if ext not in [".srt", ".vtt", ".json", ".ass"]:
        raise ValidationException(message="字幕格式不支持，仅支持 SRT/VTT/JSON/ASS")

    content = await subtitle.read()
    # 使用配置的字幕目录，确保路径正确
    # 静态文件挂载：/uploads -> ./storage/uploads
    # 字幕文件路径：./storage/uploads/subtitles/{filename}
    # URL路径应该是：/uploads/subtitles/{filename}
    subtitle_dir = settings.UPLOAD_SUBTITLE_DIR
    unique_filename = f"{video_id}_subtitle_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(subtitle_dir, unique_filename)
    os.makedirs(subtitle_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    # 生成URL路径：/uploads/subtitles/{filename}
    subtitle_url = f"/uploads/subtitles/{unique_filename}"

    # 使用事务管理，确保数据一致性
    try:
        with transaction(db):
            video.subtitle_url = subtitle_url
            # 事务上下文管理器会自动提交或回滚
    except Exception as e:
        # 如果数据库更新失败，删除已保存的文件
        file_path = os.path.join(subtitle_dir, unique_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"字幕上传失败，已删除文件: {e}")
        raise

    logger.info(f"视频 {video_id} 字幕上传成功：{subtitle_url}")
    return SubtitleUploadResponse(message="字幕上传成功", subtitle_url=subtitle_url, video_id=video_id)


# ==================== 用户视频管理 ====================

@router.put("/{video_id}", response_model=VideoDetailResponse)
async def update_video(
    video_id: int,
    video_update: VideoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新视频信息（仅上传者可操作）
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    # 调用 Service 层更新视频
    video = VideoManagementService.update_video(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        title=video_update.title,
        description=video_update.description,
        category_id=video_update.category_id,
    )
    
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 获取更新后的视频详情响应
    video_detail = VideoResponseBuilder.get_video_detail_response(db, video_id)
    if not video_detail:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return video_detail


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除视频（仅上传者可操作）
    
    直接硬删除，前端已有确认弹框
    
    路由层只负责调用 Service，所有业务逻辑在 Service 层
    """
    success = VideoManagementService.delete_video(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        hard_delete=True,  # 直接硬删除
    )
    
    if not success:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    return success_response(
        message="视频删除成功"
    )


# ==================== 视频互动（点赞、收藏）====================

@router.post("/{video_id}/like", response_model=dict)
async def like_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    点赞/取消点赞视频（RESTful 风格路由）
    
    如果已点赞则取消点赞，如果未点赞则点赞
    立即同步更新数据库的 like_count 字段
    """
    from app.services.cache.redis_service import redis_service
    
    # 检查视频是否存在
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 检查是否已点赞
    key = f"likes:video:{video_id}"
    is_liked = redis_service.redis.sismember(key, current_user.id)
    
    if is_liked:
        # 取消点赞
        await redis_service.remove_like(current_user.id, "video", video_id)
        count = await redis_service.get_like_count("video", video_id)
        
        # 立即同步更新数据库的 like_count
        video.like_count = count
        db.commit()
        
        return {"is_liked": False, "like_count": count}
    else:
        # 点赞
        await redis_service.add_like(current_user.id, "video", video_id)
        count = await redis_service.get_like_count("video", video_id)
        
        # 立即同步更新数据库的 like_count
        video.like_count = count
        db.commit()
        
        return {"is_liked": True, "like_count": count}


@router.post("/{video_id}/collect", response_model=dict)
async def collect_video(
    video_id: int,
    request_data: dict = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    收藏/取消收藏视频（RESTful 风格路由）
    
    如果已收藏则取消收藏，如果未收藏则收藏到指定文件夹（folder_id 为 None 表示未分类）
    
    参数：
    - video_id: 视频ID
    - request_data: 请求体，包含 folder_id（可选，None 表示未分类）
    """
    from app.models.interaction import UserCollection
    
    # 从请求体获取 folder_id
    folder_id = None
    if request_data:
        folder_id = request_data.get('folder_id')
    
    # 如果提供了 folder_id，验证文件夹是否存在且属于当前用户
    if folder_id is not None:
        from app.models.collection_folder import CollectionFolder
        folder = db.query(CollectionFolder).filter(
            CollectionFolder.id == folder_id,
            CollectionFolder.user_id == current_user.id
        ).first()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
    
    # 检查是否已收藏
    exists = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id,
        UserCollection.video_id == video_id
    ).first()
    
    if exists:
        # 取消收藏
        db.delete(exists)
        db.query(Video).filter(Video.id == video_id).update(
            {Video.collect_count: Video.collect_count - 1}
        )
        db.commit()
        # 获取最新收藏数
        video = db.query(Video).filter(Video.id == video_id).first()
        return {"is_collected": False, "collect_count": video.collect_count if video else 0}
    else:
        # 如果 folder_id 为 None，自动创建或获取"默认收藏夹"
        if folder_id is None:
            from app.models.collection_folder import CollectionFolder
            default_folder = db.query(CollectionFolder).filter(
                CollectionFolder.user_id == current_user.id,
                CollectionFolder.name == "默认收藏夹"
            ).first()
            
            if not default_folder:
                # 创建默认收藏夹
                default_folder = CollectionFolder(
                    user_id=current_user.id,
                    name="默认收藏夹",
                    description="系统自动创建的默认收藏夹"
                )
                db.add(default_folder)
                db.commit()
                db.refresh(default_folder)
            
            folder_id = default_folder.id
        
        # 收藏到指定文件夹
        new_collection = UserCollection(
            user_id=current_user.id, 
            video_id=video_id,
            folder_id=folder_id
        )
        db.add(new_collection)
        db.query(Video).filter(Video.id == video_id).update(
            {Video.collect_count: Video.collect_count + 1}
        )
        db.commit()
        # 获取最新收藏数
        video = db.query(Video).filter(Video.id == video_id).first()
        return {"is_collected": True, "collect_count": video.collect_count if video else 0}


@router.get("/{video_id}/outline", response_model=dict)
async def get_video_outline(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    获取视频内容大纲
    
    如果大纲不存在且视频有字幕，则自动生成
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 如果已有大纲，直接返回
    if video.outline:
        try:
            import json
            outline_data = json.loads(video.outline)
            return success_response(
                data={"outline": outline_data},
                message="获取大纲成功"
            )
        except:
            pass
    
    # 如果没有大纲但有字幕，尝试生成
    if video.subtitle_url:
        from app.services.video.outline_service import OutlineService
        outline = await OutlineService.extract_outline(video_id, video.subtitle_url)
        
        if outline:
            # 保存大纲到数据库
            import json
            video.outline = json.dumps(outline, ensure_ascii=False)
            db.commit()
            
            return success_response(
                data={"outline": outline},
                message="大纲生成成功"
            )
    
    return success_response(
        data={"outline": []},
        message="暂无大纲"
    )


@router.post("/{video_id}/outline/generate", response_model=dict)
async def generate_video_outline(
    video_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动触发生成视频大纲（需要登录，仅上传者可操作）
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以生成大纲")
    
    if not video.subtitle_url:
        raise ValidationException(message="视频没有字幕文件，无法生成大纲")
    
    # 异步生成大纲
    from app.services.video.outline_service import OutlineService
    
    async def generate_and_save():
        outline = await OutlineService.extract_outline(video_id, video.subtitle_url)
        if outline:
            # 使用新的数据库会话保存
            from app.core.database import SessionLocal
            db_session = SessionLocal()
            try:
                video_obj = db_session.query(Video).filter(Video.id == video_id).first()
                if video_obj:
                    import json
                    video_obj.outline = json.dumps(outline, ensure_ascii=False)
                    db_session.commit()
            finally:
                db_session.close()
    
    background_tasks.add_task(generate_and_save)
    
    return success_response(
        data={},
        message="大纲生成任务已启动，请稍后查询"
    )


@router.get("/{video_id}/ai-analysis", summary="获取视频AI分析报告")
async def get_video_ai_analysis(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. 鉴权：只有作者能看
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "视频不存在")
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "无权查看此报告")

    # 2. 检查数据量 (评论 + 弹幕)
    comment_count = db.query(Comment).filter(Comment.video_id == video_id).count()
    danmaku_count = db.query(Danmaku).filter(Danmaku.video_id == video_id).count()
    total_count = comment_count + danmaku_count

    if total_count == 0:
        return {
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
            "risks": [],
            "summary": "暂无数据：该视频尚未产生足够的互动（评论/弹幕），无法进行AI智能分析。",
            "expert_results": [],
            "conflict_resolved": False
        }

    # 3. 统计情感分布 (基于 ai_score)
    # score < 40: 负面/争议
    # 40 <= score <= 75: 中性/普通
    # score > 75: 正面/优质
    
    # 3.1 弹幕统计
    danmaku_stats = db.query(
        func.sum(case((Danmaku.ai_score < 40, 1), else_=0)).label("negative"),
        func.sum(case((Danmaku.ai_score.between(40, 75), 1), else_=0)).label("neutral"),
        func.sum(case((Danmaku.ai_score > 75, 1), else_=0)).label("positive")
    ).filter(Danmaku.video_id == video_id).first()

    # 3.2 评论统计
    comment_stats = db.query(
        func.sum(case((Comment.ai_score < 40, 1), else_=0)).label("negative"),
        func.sum(case((Comment.ai_score.between(40, 75), 1), else_=0)).label("neutral"),
        func.sum(case((Comment.ai_score > 75, 1), else_=0)).label("positive")
    ).filter(Comment.video_id == video_id).first()

    # 合并统计
    positive = (danmaku_stats.positive or 0) + (comment_stats.positive or 0)
    neutral = (danmaku_stats.neutral or 0) + (comment_stats.neutral or 0)
    negative = (danmaku_stats.negative or 0) + (comment_stats.negative or 0)

    # 4. 获取风险/高亮内容 (从两张表获取，合并排序)
    danmaku_risks = db.query(Danmaku).filter(
        Danmaku.video_id == video_id,
        Danmaku.ai_score < 30
    ).order_by(desc(Danmaku.created_at)).limit(5).all()

    comment_risks = db.query(Comment).filter(
        Comment.video_id == video_id,
        Comment.ai_score < 30
    ).order_by(desc(Comment.created_at)).limit(5).all()

    # 合并并按时间倒序
    combined_risks = []
    for d in danmaku_risks:
        combined_risks.append({
            "content": d.content,
            "reason": "弹幕低分预警",
            "score": d.ai_score,
            "time": d.created_at
        })
    for c in comment_risks:
        combined_risks.append({
            "content": c.content,
            "reason": "评论低分预警",
            "score": c.ai_score,
            "time": c.created_at
        })
    
    # 再次排序取前5
    combined_risks.sort(key=lambda x: x['time'], reverse=True)
    final_risks = combined_risks[:5]

    # 5. 动态生成陪审团数据 (模拟逻辑)
    # 基于情感分布动态调整专家评分
    
    # Meme Expert: 正面内容越多，评分越高
    meme_score = 60 + min(35, int((positive / total_count) * 40)) if total_count > 0 else 80
    
    # Emotion Expert: 负面内容越少，评分越高
    emotion_score = 100 - min(40, int((negative / total_count) * 100)) if total_count > 0 else 90
    
    # Legal Expert: 风险内容越多，评分越低
    risk_count = len(combined_risks)
    legal_score = max(50, 100 - risk_count * 10)

    expert_results = [
        {"agent": "Meme Expert", "score": meme_score, "opinion": "社区梗与互动氛围检测中...", "safe": True},
        {"agent": "Emotion Expert", "score": emotion_score, "opinion": "情感倾向与对立情绪分析中...", "safe": True},
        {"agent": "Legal Expert", "score": legal_score, "opinion": "合规性与潜在风险扫描中...", "safe": legal_score > 60}
    ]
    
    sentiment_desc = "积极" if positive > negative else "需关注"
    summary = f"基于 {total_count} 条互动（{comment_count}条评论，{danmaku_count}条弹幕）分析，整体氛围{sentiment_desc}。发现 {len(combined_risks)} 条潜在风险内容。"

    return {
        "sentiment": {
            "positive": positive,
            "neutral": neutral,
            "negative": negative
        },
        "risks": final_risks,
        "summary": summary,
        "expert_results": expert_results,
        "conflict_resolved": False
    }