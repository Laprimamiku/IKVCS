"""
用户信息管理 API
需求：2.1, 2.2, 2.3
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.core.response import success_response
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest, MessageResponse
from app.core.config import settings
from app.services.user.user_service import UserService

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
    from app.models.video import Video
    from sqlalchemy import func
    
    # 统计用户所有视频的点赞总数
    total_likes_result = db.query(func.sum(Video.like_count)).filter(
        Video.uploader_id == current_user.id,
        Video.status == 2  # 只统计已发布的视频
    ).scalar()
    
    # 将 Decimal 转换为 int（如果 total_likes_result 是 Decimal 类型）
    if total_likes_result is not None:
        total_likes = int(total_likes_result) + 1  # 获赞数 = 视频点赞总数 + 1
    else:
        total_likes = 1
    
    # 统计总播放量
    total_views_result = db.query(func.sum(Video.view_count)).filter(
        Video.uploader_id == current_user.id,
        Video.status == 2
    ).scalar()
    total_views = int(total_views_result) if total_views_result is not None else 0
    
    # 统计总收藏数
    from app.models.interaction import UserCollection
    total_collections = db.query(func.count(UserCollection.id)).filter(
        UserCollection.user_id == current_user.id
    ).scalar() or 0
    
    return success_response(
        data={
            "following_count": 0,  # 暂时为0，后续实现关注功能
            "followers_count": 0,  # 暂时为0，后续实现粉丝功能
            "total_likes": total_likes,
            "total_views": total_views,
            "total_collections": int(total_collections)
        },
        message="获取统计数据成功"
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
    for wh in watch_history_list:
        if wh.video:
            video_data = VideoResponseBuilder.build_list_item(wh.video, current_user.id if current_user else None)
            videos.append({
                "id": wh.id,
                "video_id": wh.video_id,
                "watched_at": wh.watched_at.isoformat(),
                "video": video_data
            })
    
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
    for collection in collections:
        if collection.video:
            video_data = VideoResponseBuilder.build_list_item(
                collection.video, 
                current_user.id
            )
            items.append(video_data)
    
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
    
    # 统计每个文件夹中的收藏数量
    folder_list = []
    for folder in folders:
        count = db.query(func.count(UserCollection.id)).filter(
            UserCollection.folder_id == folder.id
        ).scalar() or 0
        
        folder_list.append({
            "id": folder.id,
            "name": folder.name,
            "description": folder.description,
            "count": count,
            "created_at": folder.created_at.isoformat() if hasattr(folder.created_at, 'isoformat') else str(folder.created_at),
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
            "created_at": folder.created_at.isoformat() if hasattr(folder.created_at, 'isoformat') else str(folder.created_at),
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
            "created_at": folder.created_at.isoformat() if hasattr(folder.created_at, 'isoformat') else str(folder.created_at),
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