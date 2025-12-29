"""
用户信息管理 API
需求：2.1, 2.2, 2.3
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
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


@router.get("/me/watch-history", response_model=dict)
def get_watch_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的最近观看历史（最多3个）
    
    返回：
    - 最近观看的3个视频列表（按观看时间倒序）
    """
    from app.repositories.watch_history_repository import WatchHistoryRepository
    from app.schemas.video import VideoListItemResponse
    from app.services.video import VideoResponseBuilder
    
    # 获取最近3个观看历史
    watch_history_list = WatchHistoryRepository.get_recent_watches(db, current_user.id, limit=3)
    
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
        data={"items": videos, "total": len(videos)},
        message="获取观看历史成功"
    )