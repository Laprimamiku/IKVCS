"""
用户信息管理 API
需求：2.1, 2.2, 2.3
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.core.response import success_response
from app.core.video_constants import VideoStatus
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest, MessageResponse
from app.core.config import settings
from app.services.user.user_service import UserService
from app.utils.timezone_utils import isoformat_in_app_tz, to_app_tz, utc_now

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户信息
    
    需求：2.1 - 当用户请求个人信息时，系统应当返回当前用户的昵称、头像、简介等信息
    
    流程：
    1. 通过 JWT 令牌验证用户身份（get_current_user 依赖）
    2. 返回用户信息
    
    返回：
    - 用户完整信息（不包含密码哈希）
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user_info(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    
    需求：2.2 - 当用户更新个人信息时，系统应当验证数据格式并保存更改
    
    流程：
    1. 验证用户身份和状态
    2. 更新用户信息（只更新提供的字段）
    3. 保存到数据库
    4. 返回更新后的用户信息
    
    参数：
    - nickname: 昵称（可选）
    - intro: 个人简介（可选）
    
    返回：
    - 更新后的用户信息
    """
    # 调用 Service 层处理更新逻辑
    updated_user = UserService.update_user_info(db, current_user, user_update)
    return updated_user


@router.post("/me/avatar", response_model=dict)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    上传用户头像
    
    需求：2.2 - 实现头像上传功能
    
    流程：
    1. 验证文件类型（只允许图片）
    2. 验证文件大小（不超过 2MB）
    3. 生成唯一文件名
    4. 保存文件到服务器
    5. 更新用户头像 URL
    6. 返回头像 URL
    
    参数：
    - file: 图片文件
    
    返回：
    - avatar_url: 头像访问地址
    """
    # 调用 Service 层处理头像上传逻辑
    avatar_url = await UserService.upload_avatar(db, current_user, file)
    
    return success_response(
        data={"avatar_url": avatar_url},
        message="头像上传成功"
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定用户信息（他人主页）
    
    需求：2.3 - 当用户查看他人主页时，系统应当返回该用户的公开信息（不包含敏感数据）
    
    流程：
    1. 根据用户 ID 查询用户
    2. 返回用户公开信息
    
    参数：
    - user_id: 用户 ID
    
    返回：
    - 用户公开信息
    
    注意：
    - 不需要登录即可访问
    - 返回的信息不包含敏感数据（密码哈希等）
    """
    # 调用 Service 层获取用户信息
    return UserService.get_user_by_id(db, user_id)


@router.get("/me/stats", response_model=dict)
def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的统计数据
    
    返回：
    - following_count: 关注数（暂时为0，后续实现）
    - followers_count: 粉丝数（暂时为0，后续实现）
    - total_likes: 获赞数（用户所有视频的点赞总数+1）
    """
    from sqlalchemy import func
    from app.models.video import Video
    from app.models.comment import Comment
    from app.models.danmaku import Danmaku
    from app.services.cache.redis_service import redis_service

    # 只统计已发布的视频（创作者数据中心口径）
    rows = (
        db.query(Video.id, Video.view_count, Video.like_count, Video.collect_count)
        .filter(Video.uploader_id == current_user.id, Video.status == VideoStatus.PUBLISHED)
        .all()
    )
    video_ids = [r.id for r in rows]

    total_likes = sum((r.like_count or 0) for r in rows)
    total_collections = sum((r.collect_count or 0) for r in rows)

    # 播放量优先取 Redis 最新值（避免 DB 未同步导致“数据中心不同步”）
    total_views = 0
    if video_ids:
        try:
            keys = [f"video:view_count:{vid}" for vid in video_ids]
            values = redis_service.redis.mget(keys)
        except Exception:
            values = [None] * len(video_ids)

        for r, raw in zip(rows, values):
            if raw is not None and raw != "":
                try:
                    total_views += int(raw)
                    continue
                except Exception:
                    pass
            total_views += int(r.view_count or 0)

    total_comments = 0
    total_danmakus = 0
    if video_ids:
        total_comments = (
            db.query(func.count(Comment.id))
            .filter(Comment.video_id.in_(video_ids), Comment.is_deleted == False)
            .scalar()
            or 0
        )
        total_danmakus = (
            db.query(func.count(Danmaku.id))
            .filter(Danmaku.video_id.in_(video_ids), Danmaku.is_deleted == False)
            .scalar()
            or 0
        )
    
    return success_response(
        data={
            "following_count": 0,  # 暂时为0，后续实现关注功能
            "followers_count": 0,  # 暂时为0，后续实现粉丝功能
            "total_likes": int(total_likes),
            "total_views": int(total_views),
            "total_collections": int(total_collections),
            "total_comments": int(total_comments),
            "total_danmakus": int(total_danmakus),
        },
        message="获取统计数据成功"
    )


@router.get("/me/creator/stats", response_model=dict)
def get_creator_stats(
    days: int = Query(30, ge=7, le=365, description="统计周期（天）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创作中心：数据中心统计（用于前端图表/卡片）
    """
    from datetime import datetime, timedelta, time, timezone
    from sqlalchemy import func
    from app.models.video import Video
    from app.models.comment import Comment
    from app.models.danmaku import Danmaku
    from app.models.watch_history import WatchHistory
    from app.services.cache.redis_service import redis_service

    video_rows = (
        db.query(Video.id, Video.title, Video.view_count, Video.like_count, Video.collect_count)
        .filter(Video.uploader_id == current_user.id)
        .all()
    )
    video_ids = [r.id for r in video_rows]

    # merged view_count per video (Redis preferred)
    view_map: dict[int, int] = {}
    if video_ids:
        try:
            keys = [f"video:view_count:{vid}" for vid in video_ids]
            values = redis_service.redis.mget(keys)
        except Exception:
            values = [None] * len(video_ids)

        for r, raw in zip(video_rows, values):
            if raw is not None and raw != "":
                try:
                    view_map[int(r.id)] = int(raw)
                    continue
                except Exception:
                    pass
            view_map[int(r.id)] = int(r.view_count or 0)

    comment_count_map: dict[int, int] = {}
    danmaku_count_map: dict[int, int] = {}
    if video_ids:
        rows = (
            db.query(Comment.video_id, func.count(Comment.id))
            .filter(Comment.video_id.in_(video_ids), Comment.is_deleted == False)
            .group_by(Comment.video_id)
            .all()
        )
        comment_count_map = {int(vid): int(cnt) for vid, cnt in rows}

        rows = (
            db.query(Danmaku.video_id, func.count(Danmaku.id))
            .filter(Danmaku.video_id.in_(video_ids), Danmaku.is_deleted == False)
            .group_by(Danmaku.video_id)
            .all()
        )
        danmaku_count_map = {int(vid): int(cnt) for vid, cnt in rows}

    total_videos = len(video_rows)
    total_views = sum(view_map.get(int(r.id), int(r.view_count or 0)) for r in video_rows)
    total_likes = sum(int(r.like_count or 0) for r in video_rows)
    total_collections = sum(int(r.collect_count or 0) for r in video_rows)
    total_comments = sum(comment_count_map.values()) if video_ids else 0
    total_danmakus = sum(danmaku_count_map.values()) if video_ids else 0

    # daily series
    now_utc = utc_now()
    now_local = to_app_tz(now_utc)
    end_date = now_local.date()
    start_date = end_date - timedelta(days=days - 1)

    start_dt_local = datetime.combine(start_date, time.min).replace(tzinfo=now_local.tzinfo)
    start_dt = start_dt_local.astimezone(timezone.utc).replace(tzinfo=None)

    offset = now_local.utcoffset() or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    to_tz = f"{sign}{hours:02d}:{minutes:02d}"

    date_labels = [(start_date + timedelta(days=i)).isoformat() for i in range(days)]
    daily_views = {d: 0 for d in date_labels}
    daily_comments = {d: 0 for d in date_labels}
    daily_danmakus = {d: 0 for d in date_labels}

    if video_ids:
        watched_local_date = func.date(func.convert_tz(WatchHistory.watched_at, "+00:00", to_tz))
        rows = (
            db.query(watched_local_date, func.count(WatchHistory.id))
            .join(Video, Video.id == WatchHistory.video_id)
            .filter(Video.uploader_id == current_user.id, WatchHistory.watched_at >= start_dt)
            .group_by(watched_local_date)
            .all()
        )
        for d, cnt in rows:
            key = str(d)
            if key in daily_views:
                daily_views[key] = int(cnt)

        comment_local_date = func.date(func.convert_tz(Comment.created_at, "+00:00", to_tz))
        rows = (
            db.query(comment_local_date, func.count(Comment.id))
            .join(Video, Video.id == Comment.video_id)
            .filter(
                Video.uploader_id == current_user.id,
                Comment.created_at >= start_dt,
                Comment.is_deleted == False,
            )
            .group_by(comment_local_date)
            .all()
        )
        for d, cnt in rows:
            key = str(d)
            if key in daily_comments:
                daily_comments[key] = int(cnt)

        danmaku_local_date = func.date(func.convert_tz(Danmaku.created_at, "+00:00", to_tz))
        rows = (
            db.query(danmaku_local_date, func.count(Danmaku.id))
            .join(Video, Video.id == Danmaku.video_id)
            .filter(
                Video.uploader_id == current_user.id,
                Danmaku.created_at >= start_dt,
                Danmaku.is_deleted == False,
            )
            .group_by(danmaku_local_date)
            .all()
        )
        for d, cnt in rows:
            key = str(d)
            if key in daily_danmakus:
                daily_danmakus[key] = int(cnt)

    top_videos = [
        {
            "id": int(r.id),
            "title": r.title,
            "view_count": int(view_map.get(int(r.id), int(r.view_count or 0))),
            "like_count": int(r.like_count or 0),
            "collect_count": int(r.collect_count or 0),
            "comment_count": int(comment_count_map.get(int(r.id), 0)),
            "danmaku_count": int(danmaku_count_map.get(int(r.id), 0)),
        }
        for r in video_rows
    ]
    top_videos.sort(key=lambda x: x["view_count"], reverse=True)
    top_videos = top_videos[:5]

    return success_response(
        data={
            "totals": {
                "total_videos": int(total_videos),
                "total_views": int(total_views),
                "total_likes": int(total_likes),
                "total_comments": int(total_comments),
                "total_danmakus": int(total_danmakus),
                "total_collections": int(total_collections),
            },
            "daily": {
                "dates": date_labels,
                "views": [daily_views[d] for d in date_labels],
                "comments": [daily_comments[d] for d in date_labels],
                "danmakus": [daily_danmakus[d] for d in date_labels],
            },
            "top_videos": top_videos,
        },
        message="获取创作者数据中心统计成功",
    )


@router.get("/me/watch-history", response_model=dict)
def get_watch_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20
):
    """
    获取当前用户的观看历史（支持分页）
    
    返回：
    - 观看历史视频列表（按观看时间倒序，支持分页）
    """
    from app.repositories.watch_history_repository import WatchHistoryRepository
    from app.services.video import VideoResponseBuilder
    from sqlalchemy.orm import joinedload
    from app.models.watch_history import WatchHistory
    from app.models.video import Video
    
    # 计算分页
    skip = (page - 1) * page_size
    
    # 查询观看历史（关联视频、上传者、分类）
    watch_history_list = db.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id
    ).options(
        joinedload(WatchHistory.video).joinedload(Video.uploader),
        joinedload(WatchHistory.video).joinedload(Video.category)
    ).order_by(
        WatchHistory.watched_at.desc()
    ).offset(skip).limit(page_size).all()
    
    # 查询总数
    total = db.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id
    ).count()
    
    # 转换为响应格式
    videos = []
    videos = []
    wh_with_video = [wh for wh in watch_history_list if wh.video]
    video_items = VideoResponseBuilder.build_list_items(
        [wh.video for wh in wh_with_video],
        current_user.id if current_user else None,
    )
    for wh, video_data in zip(wh_with_video, video_items):
        videos.append(
            {
                "id": wh.id,
                "video_id": wh.video_id,
                "watched_at": isoformat_in_app_tz(wh.watched_at),
                "video": video_data,
            }
        )
    
    return success_response(
        data={
            "items": videos,
            "total": total,
            "page": page,
            "page_size": page_size
        },
        message="获取观看历史成功"
    )


@router.delete("/me/watch-history/{watch_history_id}", response_model=dict)
def delete_watch_history(
    watch_history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除观看历史记录（硬删除）
    
    参数：
    - watch_history_id: 观看历史记录ID
    
    返回：
    - 删除成功消息
    """
    from app.models.watch_history import WatchHistory
    
    # 查询观看历史记录
    watch_history = db.query(WatchHistory).filter(
        WatchHistory.id == watch_history_id,
        WatchHistory.user_id == current_user.id
    ).first()
    
    if not watch_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="观看历史记录不存在"
        )
    
    # 硬删除
    db.delete(watch_history)
    db.commit()
    
    return success_response(
        message="删除观看历史成功"
    )


@router.get("/me/favorites", response_model=dict)
def get_my_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    folder_id: int = None
):
    """
    获取当前用户的收藏列表
    
    参数：
    - page: 页码
    - page_size: 每页数量
    - folder_id: 文件夹ID（可选，用于筛选特定文件夹的收藏）
    
    返回：
    - 收藏的视频列表（分页）
    """
    from app.models.interaction import UserCollection
    from app.services.video import VideoResponseBuilder
    from sqlalchemy.orm import joinedload
    
    # 计算分页
    skip = (page - 1) * page_size
    
    # 构建查询条件
    query = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id
    )
    
    # 如果指定了文件夹ID，则筛选该文件夹的收藏
    if folder_id is not None:
        query = query.filter(UserCollection.folder_id == folder_id)
    
    # 查询收藏记录（关联视频、上传者、分类）
    from app.models.video import Video
    collections = query.options(
        joinedload(UserCollection.video).joinedload(Video.uploader),
        joinedload(UserCollection.video).joinedload(Video.category)
    ).order_by(
        UserCollection.created_at.desc()
    ).offset(skip).limit(page_size).all()
    
    # 查询总数
    count_query = db.query(UserCollection).filter(
        UserCollection.user_id == current_user.id
    )
    if folder_id is not None:
        count_query = count_query.filter(UserCollection.folder_id == folder_id)
    total = count_query.count()
    
    # 转换为响应格式
    items = []
    videos = [c.video for c in collections if c.video]
    items = VideoResponseBuilder.build_list_items(videos, current_user.id)
    
    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        },
        message="获取收藏列表成功"
    )


@router.get("/me/favorites/folders", response_model=dict)
def get_collection_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的所有收藏文件夹
    
    返回：
    - 文件夹列表
    """
    from app.models.collection_folder import CollectionFolder
    from app.models.interaction import UserCollection
    from sqlalchemy import func
    
    # 查询所有文件夹
    folders = db.query(CollectionFolder).filter(
        CollectionFolder.user_id == current_user.id
    ).order_by(CollectionFolder.created_at.desc()).all()

    # 批量统计每个文件夹的收藏数量，避免逐条 count 查询导致 N+1
    folder_ids = [f.id for f in folders]
    count_map: dict[int, int] = {}
    if folder_ids:
        rows = (
            db.query(UserCollection.folder_id, func.count(UserCollection.id))
            .filter(
                UserCollection.user_id == current_user.id,
                UserCollection.folder_id.in_(folder_ids),
            )
            .group_by(UserCollection.folder_id)
            .all()
        )
        count_map = {int(folder_id): int(cnt) for folder_id, cnt in rows if folder_id is not None}
    
    # 统计每个文件夹中的收藏数量
    folder_list = []
    for folder in folders:
        count = count_map.get(folder.id, 0)
        
        folder_list.append({
            "id": folder.id,
            "name": folder.name,
            "description": folder.description,
            "count": count,
            "created_at": isoformat_in_app_tz(folder.created_at),
        })
    
    # 统计未分类的收藏数量
    uncategorized_count = db.query(func.count(UserCollection.id)).filter(
        UserCollection.user_id == current_user.id,
        UserCollection.folder_id.is_(None)
    ).scalar() or 0
    
    return success_response(
        data={
            "folders": folder_list,
            "uncategorized_count": uncategorized_count
        },
        message="获取文件夹列表成功"
    )


@router.post("/me/favorites/folders", response_model=dict)
def create_collection_folder(
    folder_create: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建收藏文件夹
    
    参数：
    - folder_create: 请求体，包含 name（必填）和 description（可选）
    
    返回：
    - 创建的文件夹信息
    """
    from app.models.collection_folder import CollectionFolder
    
    name = folder_create.get('name')
    description = folder_create.get('description')
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件夹名称不能为空"
        )
    
    # 检查文件夹名称是否已存在
    existing = db.query(CollectionFolder).filter(
        CollectionFolder.user_id == current_user.id,
        CollectionFolder.name == name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件夹名称已存在"
        )
    
    # 创建文件夹
    folder = CollectionFolder(
        user_id=current_user.id,
        name=name,
        description=description
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    
    return success_response(
        data={
            "id": folder.id,
            "name": folder.name,
            "description": folder.description,
            "count": 0,  # 新创建的文件夹初始数量为 0
            "created_at": isoformat_in_app_tz(folder.created_at),
        },
        message="创建文件夹成功"
    )


@router.put("/me/favorites/folders/{folder_id}", response_model=dict)
def update_collection_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    name: str = None,
    description: str = None
):
    """
    更新收藏文件夹
    
    参数：
    - folder_id: 文件夹ID
    - name: 文件夹名称（可选）
    - description: 文件夹描述（可选）
    
    返回：
    - 更新后的文件夹信息
    """
    from app.models.collection_folder import CollectionFolder
    
    # 查询文件夹
    folder = db.query(CollectionFolder).filter(
        CollectionFolder.id == folder_id,
        CollectionFolder.user_id == current_user.id
    ).first()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 更新文件夹信息
    if name is not None:
        # 检查新名称是否与其他文件夹冲突
        existing = db.query(CollectionFolder).filter(
            CollectionFolder.user_id == current_user.id,
            CollectionFolder.name == name,
            CollectionFolder.id != folder_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件夹名称已存在"
            )
        folder.name = name
    
    if description is not None:
        folder.description = description
    
    db.commit()
    db.refresh(folder)
    
    return success_response(
        data={
            "id": folder.id,
            "name": folder.name,
            "description": folder.description,
            "created_at": isoformat_in_app_tz(folder.created_at),
        },
        message="更新文件夹成功"
    )


@router.delete("/me/favorites/folders/{folder_id}", response_model=dict)
def delete_collection_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除收藏文件夹（文件夹中的收藏将变为未分类）
    
    参数：
    - folder_id: 文件夹ID
    
    返回：
    - 删除成功消息
    """
    from app.models.collection_folder import CollectionFolder
    
    # 查询文件夹
    folder = db.query(CollectionFolder).filter(
        CollectionFolder.id == folder_id,
        CollectionFolder.user_id == current_user.id
    ).first()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 删除文件夹（由于设置了 ondelete='SET NULL'，收藏的 folder_id 会自动设为 NULL）
    db.delete(folder)
    db.commit()
    
    return success_response(
        message="删除文件夹成功"
    )
