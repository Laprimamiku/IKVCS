"""
视频转码服务

职责：协调转码流程（组合其他服务）
相当于 Java 的 TranscodeService

需求：4.1-4.5（视频转码处理）
"""
import asyncio
import os
import logging
import threading
from threading import Semaphore
from sqlalchemy.orm import Session

from app.models.video import Video
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.transcode.ffmpeg_builder import FFmpegBuilder
from app.services.transcode.transcode_executor import TranscodeExecutor
from app.services.transcode.playlist_generator import PlaylistGenerator

logger = logging.getLogger(__name__)

# 全局信号量：限制同时进行的转码任务数（从配置读取）
_TRANSCODE_SEMAPHORE = Semaphore(settings.TRANSCODE_MAX_CONCURRENT)

# 解析转码清晰度配置
def _parse_resolutions() -> list:
    """从配置字符串解析转码清晰度配置"""
    resolutions = []
    if settings.TRANSCODE_RESOLUTIONS:
        for item in settings.TRANSCODE_RESOLUTIONS.split(','):
            parts = item.strip().split(':')
            if len(parts) == 4:
                resolutions.append((parts[0], parts[1], parts[2], parts[3]))
    # 默认配置（暂时只支持360p和480p，720p和1080p后期改善）
    if not resolutions:
        resolutions = [
            ("360p", "640x360", "500k", "96k"),
            ("480p", "854x480", "800k", "128k"),
            # ("720p", "1280x720", "2000k", "128k"),  # 暂时注释，后期改善
            # ("1080p", "1920x1080", "4000k", "192k"),  # 暂时注释，后期改善
        ]
    return resolutions

# 解析优先级清晰度（第一阶段转码）
def _parse_priority_resolutions() -> set:
    """解析需要优先转码的清晰度"""
    if settings.TRANSCODE_PRIORITY_RESOLUTIONS:
        return set(r.strip() for r in settings.TRANSCODE_PRIORITY_RESOLUTIONS.split(','))
    # 默认优先转码低清晰度
    return {"360p", "480p"}

RESOLUTIONS = _parse_resolutions()
PRIORITY_RESOLUTIONS = _parse_priority_resolutions()


class TranscodeService:
    """
    转码服务类
    
    为什么使用 HLS/m3u8 格式：
        - 支持自适应码率（根据网络速度切换清晰度）
        - 支持流式播放（边下载边播放）
        - 兼容性好（主流浏览器和播放器都支持）
        - 安全性高（分片文件，难以下载完整视频）
    """
    
    @staticmethod
    def _ensure_directories():
        """确保转码输出目录存在"""
        os.makedirs(settings.VIDEO_HLS_DIR, exist_ok=True)
    
    @staticmethod
    async def transcode_video(video_id: int):
        """
        转码视频（异步后台任务）
        
        需求：4.1, 4.2, 4.3, 4.4
        
        流程：
        1. 获取视频记录
        2. 构建 FFmpeg 命令
        3. 执行转码
        4. 更新视频状态和 URL
        5. 记录错误日志（如果失败）
        """
        # 使用信号量控制并发转码任务数
        with _TRANSCODE_SEMAPHORE:
            # 创建新的数据库会话（后台任务需要独立会话）
            db = SessionLocal()
            
            try:
                logger.info(f"开始转码视频：video_id={video_id}")
                
                # 1. 获取视频记录
                from app.repositories.video_repository import VideoRepository
                video = VideoRepository.get_by_id(db, video_id)
                
                if not video:
                    logger.error(f"视频不存在：video_id={video_id}")
                    return
                
                # 获取上传会话以找到原始文件
                from app.repositories.upload_repository import UploadSessionRepository
                upload_session = UploadSessionRepository.get_by_video_id(db, video_id)
                
                if not upload_session:
                    logger.error(f"上传会话不存在：video_id={video_id}")
                    video.status = -1  # 转码失败
                    db.commit()
                    return
                
                # 2. 构建输入输出路径
                TranscodeService._ensure_directories()
                
                input_path = os.path.join(
                    settings.VIDEO_ORIGINAL_DIR,
                    f"{upload_session.file_hash}_{upload_session.file_name}"
                )
                
                output_dir = os.path.join(
                    settings.VIDEO_HLS_DIR,
                    str(video_id)
                )
                os.makedirs(output_dir, exist_ok=True)
                
                # 检查输入文件是否存在
                if not os.path.exists(input_path):
                    logger.error(f"输入文件不存在：{input_path}")
                    video.status = -1  # 转码失败
                    db.commit()
                    return
                
                # 3. 转码多个清晰度（渐进式策略）
                strategy = getattr(settings, 'TRANSCODE_STRATEGY', 'progressive')
                logger.info(f"开始多清晰度转码：{len(RESOLUTIONS)} 个清晰度，策略={strategy}")
                
                # 分离优先级清晰度和其他清晰度
                priority_list = []
                other_list = []
                for res in RESOLUTIONS:
                    name = res[0]
                    if name in PRIORITY_RESOLUTIONS:
                        priority_list.append(res)
                    else:
                        other_list.append(res)
                
                transcoded_resolutions = []
                
                # 第一阶段：转码优先级清晰度（快速完成，让用户能立即观看）
                logger.info(f"第一阶段：转码优先级清晰度 {[r[0] for r in priority_list]}")
                for name, resolution, video_bitrate, audio_bitrate in priority_list:
                    result = TranscodeService._transcode_single_resolution(
                        name, resolution, video_bitrate, audio_bitrate,
                        input_path, output_dir
                    )
                    if result:
                        transcoded_resolutions.append(result)
                
                # 如果至少有一个清晰度转码成功，立即生成播放列表并更新状态
                # 特别地，如果 360p 转码成功，立即更新状态让用户可观看
                if transcoded_resolutions:
                    logger.info(f"第一阶段完成：成功转码 {len(transcoded_resolutions)} 个清晰度，立即更新播放列表")
                    # 检查是否有 360p（最低清晰度，用户可立即观看）
                    has_360p = any(r[0] == '360p' for r in transcoded_resolutions)
                    if has_360p:
                        logger.info(f"360p 转码成功，立即更新视频状态为可观看：video_id={video_id}")
                    TranscodeService._update_playlist_and_status(
                        db, video, video_id, output_dir, transcoded_resolutions, input_path
                    )
                
                # 第二阶段：后台转码其他清晰度（渐进增强，不阻塞用户观看）
                if strategy == 'progressive' and other_list:
                    logger.info(f"第二阶段：后台转码其他清晰度 {[r[0] for r in other_list]}")
                    # 使用线程转码其他清晰度，不阻塞当前流程
                    thread = threading.Thread(
                        target=TranscodeService._transcode_other_resolutions_sync,
                        args=(video_id, other_list, input_path, output_dir),
                        daemon=True
                    )
                    thread.start()
                    logger.info(f"后台转码线程已启动：video_id={video_id}")
                elif strategy == 'all':
                    # 一次性转码所有清晰度（传统方式）
                    logger.info("策略为 all，继续转码所有清晰度")
                    for name, resolution, video_bitrate, audio_bitrate in other_list:
                        result = TranscodeService._transcode_single_resolution(
                            name, resolution, video_bitrate, audio_bitrate,
                            input_path, output_dir
                        )
                        if result:
                            transcoded_resolutions.append(result)
                    
                    # 更新播放列表（包含所有清晰度）
                    if transcoded_resolutions:
                        TranscodeService._update_playlist_and_status(
                            db, video, video_id, output_dir, transcoded_resolutions, input_path
                        )
                
                # 如果第一阶段没有成功转码任何清晰度，标记为失败
                if not transcoded_resolutions:
                    logger.error(f"所有优先级清晰度转码失败：video_id={video_id}")
                    video.status = -1  # -1=转码失败
                    db.commit()
            
            except Exception as e:
                logger.error(f"转码过程异常：video_id={video_id}, error={e}", exc_info=True)
                
                # 更新视频状态为转码失败
                try:
                    video = db.query(Video).filter(Video.id == video_id).first()
                    if video:
                        video.status = -1
                        db.commit()
                except Exception as db_error:
                    logger.error(f"更新视频状态失败：{db_error}")
            
            finally:
                db.close()
    
    @staticmethod
    def _transcode_single_resolution(
        name: str,
        resolution: str,
        video_bitrate: str,
        audio_bitrate: str,
        input_path: str,
        output_dir: str
    ) -> tuple:
        """
        转码单个清晰度
        
        Returns:
            tuple: (name, resolution, bandwidth) 如果成功，否则 None
        """
        # 创建清晰度目录
        resolution_dir = os.path.join(output_dir, name)
        os.makedirs(resolution_dir, exist_ok=True)
        
        resolution_output = os.path.join(resolution_dir, "index.m3u8")

        # 如果该清晰度已经存在产物，直接复用，避免重复耗时
        if os.path.exists(resolution_output):
            bandwidth = int(video_bitrate.replace('k', '')) * 1000
            logger.info(f"检测到已有转码产物，复用 {name}: {resolution_output}")
            return (name, resolution, bandwidth)
        
        # 构建 FFmpeg 命令
        ffmpeg_cmd = FFmpegBuilder.build_ffmpeg_command(
            input_path,
            resolution_output,
            resolution,
            video_bitrate,
            audio_bitrate
        )
        
        logger.info(f"FFmpeg 命令 ({name})：{' '.join(ffmpeg_cmd)}")
        
        # 执行转码（最多重试3次）
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            returncode, stderr = TranscodeExecutor.execute_transcode(ffmpeg_cmd)
            
            if returncode == 0:
                logger.info(f"转码成功：{name}" + (f"（重试 {retry_count} 次后成功）" if retry_count > 0 else ""))
                # 计算带宽（码率转换为 bps）
                bandwidth = int(video_bitrate.replace('k', '')) * 1000
                return (name, resolution, bandwidth)
            else:
                retry_count += 1
                error_msg = ""
                if stderr:
                    error_msg = stderr.decode('utf-8', errors='ignore') if isinstance(stderr, bytes) else str(stderr)
                    last_error = error_msg
                
                if retry_count < max_retries:
                    logger.warning(f"转码失败 ({name})，第 {retry_count} 次重试：returncode={returncode}")
                    if error_msg:
                        logger.warning(f"FFmpeg 错误输出 ({name})：{error_msg[:500]}")  # 只记录前500字符
                    # 等待1秒后重试
                    import time
                    time.sleep(1)
                else:
                    logger.error(f"转码失败 ({name})，已重试 {max_retries} 次，放弃：returncode={returncode}")
                    if last_error:
                        # 记录完整错误信息
                        logger.error(f"FFmpeg 完整错误输出 ({name})：{last_error}")
                    return None
        
        return None
    
    @staticmethod
    def _update_playlist_and_status(
        db: Session,
        video: Video,
        video_id: int,
        output_dir: str,
        transcoded_resolutions: list,
        input_path: str
    ):
        """更新播放列表和视频状态"""
        # 生成主播放列表
        logger.info(f"生成主播放列表，包含 {len(transcoded_resolutions)} 个清晰度")
        master_playlist_content = PlaylistGenerator.build_master_playlist(
            video_id,
            transcoded_resolutions
        )
        
        master_playlist_path = os.path.join(output_dir, "master.m3u8")
        with open(master_playlist_path, 'w', encoding='utf-8') as f:
            f.write(master_playlist_content)
        
        logger.info(f"主播放列表已生成：{master_playlist_path}")
        
        # 更新视频 URL 和状态
        video.video_url = f"/videos/hls/{video_id}/master.m3u8"
        video.status = 1  # 1=审核中（转码完成后先进入审核流程）
        
        # 获取视频时长（使用原始文件）
        duration = TranscodeExecutor.get_video_duration(input_path)
        if duration > 0:
            video.duration = duration
        
        db.commit()
        logger.info(f"视频转码完成，进入审核流程：video_id={video_id}")
        
        # 异步触发审核（使用后台线程，不阻塞转码流程）
        def trigger_review_async():
            """在后台线程中触发审核"""
            try:
                import asyncio
                from app.services.ai.video_review_service import video_review_service
                
                # 获取字幕路径
                subtitle_path = video.subtitle_url if video.subtitle_url else None
                if subtitle_path and not os.path.isabs(subtitle_path):
                    # 处理相对路径
                    from app.core.config import settings
                    subtitle_path = os.path.join(settings.STORAGE_ROOT, subtitle_path.lstrip("/"))
                
                # 创建新的事件循环（在后台线程中）
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        video_review_service.review_video(
                            video_id=video_id,
                            video_path=input_path,
                            subtitle_path=subtitle_path
                        )
                    )
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"触发视频审核失败: {e}", exc_info=True)
                # 审核失败，保持审核中状态，等待人工处理
        
        # 启动后台线程执行审核
        review_thread = threading.Thread(target=trigger_review_async, daemon=True)
        review_thread.start()
        logger.info(f"视频审核任务已启动（后台线程）: video_id={video_id}")
    
    @staticmethod
    def _transcode_other_resolutions_sync(
        video_id: int,
        other_resolutions: list,
        input_path: str,
        output_dir: str
    ):
        """
        后台转码其他清晰度（渐进增强）- 同步版本
        不阻塞用户观看，在后台逐步完成高清晰度转码
        使用线程执行，避免阻塞主流程
        """
        db = SessionLocal()
        try:
            from app.repositories.video_repository import VideoRepository
            video = VideoRepository.get_by_id(db, video_id)
            
            if not video:
                logger.error(f"视频不存在，取消后台转码：video_id={video_id}")
                return
            
            logger.info(f"开始后台转码其他清晰度：video_id={video_id}")
            
            new_resolutions = []
            for name, resolution, video_bitrate, audio_bitrate in other_resolutions:
                result = TranscodeService._transcode_single_resolution(
                    name, resolution, video_bitrate, audio_bitrate,
                    input_path, output_dir
                )
                if result:
                    new_resolutions.append(result)
                    logger.info(f"后台转码成功：{name}")
            
            # 如果转码成功，更新播放列表（包含所有清晰度）
            if new_resolutions:
                # 读取现有的转码清晰度
                existing_playlist_path = os.path.join(output_dir, "master.m3u8")
                existing_resolutions = []
                
                # 从现有播放列表解析已转码的清晰度
                if os.path.exists(existing_playlist_path):
                    with open(existing_playlist_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 简单解析：查找所有已存在的清晰度目录
                        for res in RESOLUTIONS:
                            name = res[0]
                            resolution_dir = os.path.join(output_dir, name)
                            resolution_output = os.path.join(resolution_dir, "index.m3u8")
                            if os.path.exists(resolution_output):
                                bandwidth = int(res[2].replace('k', '')) * 1000
                                existing_resolutions.append((name, res[1], bandwidth))
                
                # 合并所有清晰度（去重）
                all_resolutions = existing_resolutions + new_resolutions
                # 去重：按名称去重，保留最新的
                unique_resolutions = {}
                for res in all_resolutions:
                    unique_resolutions[res[0]] = res
                all_resolutions = list(unique_resolutions.values())
                # 按清晰度排序（从低到高）
                resolution_order = {"360p": 1, "480p": 2}  # 暂时只支持360p和480p
                # resolution_order = {"360p": 1, "480p": 2, "720p": 3, "1080p": 4}  # 后期改善时恢复
                all_resolutions.sort(key=lambda x: resolution_order.get(x[0], 99))
                
                # 更新播放列表
                master_playlist_content = PlaylistGenerator.build_master_playlist(
                    video_id,
                    all_resolutions
                )
                
                master_playlist_path = os.path.join(output_dir, "master.m3u8")
                with open(master_playlist_path, 'w', encoding='utf-8') as f:
                    f.write(master_playlist_content)
                
                logger.info(f"播放列表已更新：包含 {len(all_resolutions)} 个清晰度（video_id={video_id}）")
        except Exception as e:
            logger.error(f"后台转码失败：video_id={video_id}, error={e}", exc_info=True)
        finally:
            db.close()

