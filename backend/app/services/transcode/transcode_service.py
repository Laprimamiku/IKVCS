"""
视频转码服务

职责：协调转码流程（组合其他服务）
相当于 Java 的 TranscodeService

需求：4.1-4.5（视频转码处理）
"""
import asyncio
import os
import logging
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
    # 默认配置
    if not resolutions:
        resolutions = [
            ("480p", "854x480", "800k", "128k"),
            ("720p", "1280x720", "2000k", "128k"),
        ]
    return resolutions

RESOLUTIONS = _parse_resolutions()


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
                
                # 3. 转码多个清晰度
                logger.info(f"开始多清晰度转码：{len(RESOLUTIONS)} 个清晰度")
                
                transcoded_resolutions = []
                all_success = True
                
                for name, resolution, video_bitrate, audio_bitrate in RESOLUTIONS:
                    logger.info(f"转码 {name} ({resolution})...")
                    
                    # 创建清晰度目录
                    resolution_dir = os.path.join(output_dir, name)
                    os.makedirs(resolution_dir, exist_ok=True)
                    
                    resolution_output = os.path.join(resolution_dir, "index.m3u8")

                    # 如果该清晰度已经存在产物，直接复用，避免重复耗时
                    if os.path.exists(resolution_output):
                        bandwidth = int(video_bitrate.replace('k', '')) * 1000
                        transcoded_resolutions.append((name, resolution, bandwidth))
                        logger.info(f"检测到已有转码产物，复用 {name}: {resolution_output}")
                        continue
                    
                    # 构建 FFmpeg 命令
                    ffmpeg_cmd = FFmpegBuilder.build_ffmpeg_command(
                        input_path,
                        resolution_output,
                        resolution,
                        video_bitrate,
                        audio_bitrate
                    )
                    
                    logger.info(f"FFmpeg 命令 ({name})：{' '.join(ffmpeg_cmd)}")
                    
                    # 执行转码
                    returncode, stderr = TranscodeExecutor.execute_transcode(ffmpeg_cmd)
                    
                    if returncode == 0:
                        logger.info(f"转码成功：{name}")
                        # 计算带宽（码率转换为 bps）
                        bandwidth = int(video_bitrate.replace('k', '')) * 1000
                        transcoded_resolutions.append((name, resolution, bandwidth))
                    else:
                        logger.error(f"转码失败：{name}, returncode={returncode}")
                        if stderr:
                            error_msg = stderr.decode('utf-8', errors='ignore') if isinstance(stderr, bytes) else str(stderr)
                            logger.error(f"FFmpeg 错误输出 ({name})：{error_msg}")
                        all_success = False
                        # 若失败则提前结束后续耗时分辨率，使用已有清晰度兜底
                        break
                
                # 4. 生成主播放列表
                if transcoded_resolutions:
                    logger.info(f"生成主播放列表，包含 {len(transcoded_resolutions)} 个清晰度")
                    master_playlist_content = PlaylistGenerator.build_master_playlist(
                        video_id,
                        transcoded_resolutions
                    )
                    
                    master_playlist_path = os.path.join(output_dir, "master.m3u8")
                    with open(master_playlist_path, 'w', encoding='utf-8') as f:
                        f.write(master_playlist_content)
                    
                    logger.info(f"主播放列表已生成：{master_playlist_path}")
                
                # 5. 更新视频状态
                if transcoded_resolutions:
                    # 至少有一个清晰度转码成功
                    logger.info(f"转码完成：video_id={video_id}, 成功 {len(transcoded_resolutions)}/{len(RESOLUTIONS)} 个清晰度")
                    
                    # 更新视频 URL 和状态（使用主播放列表）
                    # 静态文件挂载：/videos -> ./storage/videos
                    # HLS文件路径：./storage/videos/hls/{video_id}/master.m3u8
                    # URL路径应该是：/videos/hls/{video_id}/master.m3u8
                    video.video_url = f"/videos/hls/{video_id}/master.m3u8"
                    # 当前未实现审核流，转码成功后直接设置为已发布以便前端展示
                    video.status = 2  # 2=已发布
                    
                    # 获取视频时长（使用原始文件）
                    duration = TranscodeExecutor.get_video_duration(input_path)
                    if duration > 0:
                        video.duration = duration
                    
                    db.commit()
                    logger.info(f"视频状态更新为已发布：video_id={video_id}")
                    
                else:
                    # 所有清晰度都转码失败
                    logger.error(f"所有清晰度转码失败：video_id={video_id}")
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

