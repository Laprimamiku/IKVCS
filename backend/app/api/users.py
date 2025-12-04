"""
用户信息管理 API

这个文件的作用：
1. 获取当前用户信息（GET /me）
2. 更新用户信息（PUT /me）
3. 查看他人主页（GET /{user_id}）
4. 头像上传（POST /me/avatar）

类比 Java：
    相当于 Spring Boot 的 UserController
    
需求：2.1, 2.2, 2.3
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
import os
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest, MessageResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户信息
    
    类比 Java：
        @GetMapping("/me")
        public ResponseEntity<UserVO> getCurrentUser(@AuthenticationPrincipal User user) {
            return ResponseEntity.ok(userVO);
        }
    
    流程：
    1. 通过 JWT 令牌验证用户身份（get_current_active_user）
    2. 返回用户信息
    
    需求：2.1
    
    为什么这样写：
        - 使用依赖注入自动获取当前用户
        - 不需要额外的数据库查询（已在依赖注入中查询）
        - 返回 UserResponse 自动过滤敏感信息（如密码哈希）
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    
    类比 Java：
        @PutMapping("/me")
        public ResponseEntity<UserVO> updateCurrentUser(
            @RequestBody @Valid UserUpdateDTO updateDTO,
            @AuthenticationPrincipal User user
        ) {
            // 更新用户信息
            return ResponseEntity.ok(userVO);
        }
    
    流程：
    1. 验证用户身份
    2. 更新用户信息（只更新提供的字段）
    3. 保存到数据库
    4. 返回更新后的用户信息
    
    需求：2.2
    
    为什么这样写：
        - 使用 Pydantic 的 Optional 字段，只更新提供的字段
        - 用户只能更新自己的信息（通过 get_current_active_user 保证）
        - 更新 updated_at 时间戳（SQLAlchemy 自动处理）
    """
    # 更新用户信息（只更新非 None 的字段）
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    # 保存到数据库
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    查看他人主页
    
    类比 Java：
        @GetMapping("/{userId}")
        public ResponseEntity<UserVO> getUserById(@PathVariable Integer userId) {
            User user = userService.findById(userId);
            return ResponseEntity.ok(userVO);
        }
    
    流程：
    1. 根据 user_id 查询用户
    2. 检查用户是否存在
    3. 返回用户信息
    
    需求：2.3
    
    为什么这样写：
        - 不需要登录即可查看（公开信息）
        - 返回 UserResponse 自动过滤敏感信息
        - 如果用户不存在，返回 404 错误
    
    注意：
        这个接口不需要认证，任何人都可以查看用户主页
        但只返回公开信息（昵称、头像、简介等）
    """
    # 查询用户
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查用户状态（被封禁的用户不显示）
    if user.status == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user


@router.post("/me/avatar", response_model=MessageResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    上传头像
    
    类比 Java：
        @PostMapping("/me/avatar")
        public ResponseEntity<MessageDTO> uploadAvatar(
            @RequestParam("file") MultipartFile file,
            @AuthenticationPrincipal User user
        ) {
            // 保存文件
            // 更新用户头像 URL
            return ResponseEntity.ok(messageDTO);
        }
    
    流程：
    1. 验证用户身份
    2. 验证文件类型（只允许图片）
    3. 生成唯一文件名
    4. 保存文件到服务器
    5. 更新用户头像 URL
    6. 返回成功消息
    
    需求：2.2（头像上传是更新用户信息的一部分）
    
    为什么这样写：
        - 使用 UUID 生成唯一文件名，避免文件名冲突
        - 验证文件类型，防止上传恶意文件
        - 保存文件到 uploads 目录
        - 更新数据库中的头像 URL
    
    注意：
        生产环境建议使用对象存储（如 OSS、S3）
        这里为了简化，直接保存到本地
    """
    # 1. 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持上传图片文件（JPEG、PNG、GIF、WebP）"
        )
    
    # 2. 验证文件大小（最大 5MB）
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB
    max_size = 5 * 1024 * 1024  # 5MB
    
    # 读取文件内容
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件大小不能超过 5MB"
        )
    
    # 3. 生成唯一文件名
    file_ext = os.path.splitext(file.filename)[1]  # 获取文件扩展名
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # 4. 保存文件
    upload_dir = "uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # 5. 更新用户头像 URL
    # 注意：这里返回相对路径，前端需要拼接完整 URL
    avatar_url = f"/uploads/avatars/{unique_filename}"
    current_user.avatar = avatar_url
    
    db.commit()
    
    return MessageResponse(message="头像上传成功")
