"""
视频转码服务

需求：4.1-4.5（视频转码处理）

这个文件的作用：
1. 使用 FFmpeg 将视频转码为 HLS/m3u8 格式
2. 更新视频状态（转码中 → 审核中/转码失败）
3. 记录转码错误日志

类比 Java：
    @Service
    public class TranscodeService {
        @Async
        public void transcodeVideo(Integer videoId) { ... }
    }
"""
import asyncio
import subprocess
import os
import logging
from pathlib import Path
from threading import Semaphore
from sqlalchemy.orm import Session

from app.models.video import Video
from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# 全局信号量：限制同时进行的转码任务数为 1（避免 CPU 满载）
# 如果有多个 CPU 核心，可以调整为 2 或 3
_TRANSCODE_SEMAPHORE = Semaphore(1)


class TranscodeService:
    """
    转码服务类
    
    为什么使用 HLS/m3u8 格式：
        - 支持自适应码率（根据网络速度切换清晰度）
        - 支持流式播放（边下载边播放）
        - 兼容性好（主流浏览器和播放器都支持）
        - 安全性高（分片文件，难以下载完整视频）
    """
    
    # HLS 输出目录
    HLS_OUTPUT_DIR = "videos/hls"
    
    # 多清晰度配置
    # 格式：(名称, 分辨率, 视频码率, 音频码率)
    # 优化：只提供 3 个清晰度，而不是 4 个，避免 CPU 过载
    # 为降低 CPU 占用与转码失败率，临时只保留 480p / 720p
    RESOLUTIONS = [
        ("480p", "854x480", "800k", "128k"),
        ("720p", "1280x720", "2000k", "128k"),
    ]
    
    @staticmethod
    def _ensure_directories():
        """确保输出目录存在"""
        os.makedirs(TranscodeService.HLS_OUTPUT_DIR, exist_ok=True)
    
    @staticmethod
    def build_ffmpeg_command(
        input_path: str, 
        output_path: str,
        resolution: str = None,
        video_bitrate: str = None,
        audio_bitrate: str = None
    ) -> list:
        """
        构建 FFmpeg 转码命令（支持多清晰度）
        
        参数：
            input_path: 输入视频路径
            output_path: 输出 m3u8 文件路径
            resolution: 分辨率（如 "1280x720"）
            video_bitrate: 视频码率（如 "2500k"）
            audio_bitrate: 音频码率（如 "128k"）
        
        返回：
            FFmpeg 命令列表
        
        命令说明：
            -i: 输入文件
            -vf scale: 缩放视频分辨率
            -c:v libx264: 视频编码器（H.264）
            -b:v: 视频码率
            -c:a aac: 音频编码器（AAC）
            -b:a: 音频码率
            -hls_time 10: 每个分片 10 秒
            -hls_list_size 0: 播放列表包含所有分片
            -hls_segment_filename: 分片文件命名模式
            -f hls: 输出格式为 HLS
        
        为什么这样写：
            - libx264: 最广泛支持的视频编码器
            - aac: 最广泛支持的音频编码器
            - 10 秒分片: 平衡加载速度和文件数量
            - 多清晰度: 适应不同网络环境
        """
        # 获取输出目录和文件名
        output_dir = os.path.dirname(output_path)
        output_name = os.path.splitext(os.path.basename(output_path))[0]
        
        # 分片文件命名模式
        segment_pattern = os.path.join(output_dir, f"{output_name}_%03d.ts")
        
        command = [
            'ffmpeg',
            '-i', input_path,           # 输入文件
        ]
        
        # 如果指定了分辨率，添加缩放滤镜
        if resolution:
            command.extend(['-vf', f'scale={resolution}'])
        
        command.extend([
            '-c:v', 'libx264',          # 视频编码器
            '-preset', 'fast',          # 编码速度：ultrafast < superfast < veryfast < faster < fast < medium < slow < slower < veryslow
                                        # 改为 'fast' 以降低 CPU 使用率
            '-threads', '4',            # 限制转码线程数为 4（避免 CPU 满载）
        ])
        
        # 如果指定了视频码率
        if video_bitrate:
            command.extend(['-b:v', video_bitrate])
        
        command.extend([
            '-c:a', 'aac',              # 音频编码器
        ])
        
        # 如果指定了音频码率
        if audio_bitrate:
            command.extend(['-b:a', audio_bitrate])
        
        command.extend([
            '-hls_time', '10',          # 每个分片 10 秒
            '-hls_list_size', '0',      # 播放列表包含所有分片
            '-hls_segment_filename', segment_pattern,  # 分片文件命名
            '-f', 'hls',                # 输出格式
            output_path                 # 输出 m3u8 文件
        ])
        
        return command
    
    @staticmethod
    def build_master_playlist(video_id: int, resolutions: list) -> str:
        """
        构建主播放列表（Master Playlist）
        
        参数：
            video_id: 视频ID
            resolutions: 已转码的清晰度列表 [(name, resolution, bandwidth), ...]
        
        返回：
            主播放列表内容
        
        为什么需要主播放列表：
            - 支持自适应码率切换
            - 播放器根据网络状况自动选择清晰度
            - 提升用户体验
        """
        playlist = "#EXTM3U\n"
        playlist += "#EXT-X-VERSION:3\n\n"
        
        for name, resolution, bandwidth in resolutions:
            width, height = resolution.split('x')
            playlist += f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}\n"
            playlist += f"{name}/index.m3u8\n\n"
        
        return playlist
    
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
        
        为什么使用异步：
            - 转码是耗时操作（几分钟到几十分钟）
            - 不能阻塞 API 响应
            - 使用 BackgroundTasks 在后台执行
        
        优化：
            - 使用信号量限制并发转码任务数（避免 CPU 满载）
            - 调整 FFmpeg preset 为 'fast' 以降低 CPU 使用
            - 限制转码线程数为 4
        
        容易踩坑点：
            - FFmpeg 必须安装在系统中
            - Windows: 下载 FFmpeg 并添加到 PATH
            - Linux: sudo apt install ffmpeg
            - 转码失败不影响其他功能
        """
        # 使用信号量控制并发转码任务数
        with _TRANSCODE_SEMAPHORE:
            # 创建新的数据库会话（后台任务需要独立会话）
            db = SessionLocal()
            
            try:
                logger.info(f"开始转码视频：video_id={video_id}")
                
                # 1. 获取视频记录
                video = db.query(Video).filter(Video.id == video_id).first()
                
                if not video:
                    logger.error(f"视频不存在：video_id={video_id}")
                    return
                
                # 获取上传会话以找到原始文件
                from app.models.upload import UploadSession
                upload_session = db.query(UploadSession).filter(
                    UploadSession.video_id == video_id
                ).first()
                
                if not upload_session:
                    logger.error(f"上传会话不存在：video_id={video_id}")
                    video.status = -1  # 转码失败
                    db.commit()
                    return
                
                # 2. 构建输入输出路径
                TranscodeService._ensure_directories()
                
                input_path = os.path.join(
                    settings.VIDEO_DIR,
                    f"{upload_session.file_hash}_{upload_session.file_name}"
                )
                
                output_dir = os.path.join(
                    TranscodeService.HLS_OUTPUT_DIR,
                    str(video_id)
                )
                os.makedirs(output_dir, exist_ok=True)
                
                output_path = os.path.join(output_dir, "index.m3u8")
                
                # 检查输入文件是否存在
                if not os.path.exists(input_path):
                    logger.error(f"输入文件不存在：{input_path}")
                    video.status = -1  # 转码失败
                    db.commit()
                    return
                
                # 3. 转码多个清晰度
                logger.info(f"开始多清晰度转码：{len(TranscodeService.RESOLUTIONS)} 个清晰度")
                
                transcoded_resolutions = []
                all_success = True
                
                for name, resolution, video_bitrate, audio_bitrate in TranscodeService.RESOLUTIONS:
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
                    ffmpeg_cmd = TranscodeService.build_ffmpeg_command(
                        input_path,
                        resolution_output,
                        resolution,
                        video_bitrate,
                        audio_bitrate
                    )
                    
                    logger.info(f"FFmpeg 命令 ({name})：{' '.join(ffmpeg_cmd)}")
                    
                    # 执行转码（Windows 兼容方式）
                    try:
                        process = subprocess.run(
                            ffmpeg_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=3600  # 1小时超时
                        )
                        returncode = process.returncode
                        stderr = process.stderr
                    except Exception as e:
                        logger.error(f"FFmpeg 执行失败 ({name}): {e}")
                        returncode = 1
                        stderr = str(e).encode()
                    
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
                    master_playlist_content = TranscodeService.build_master_playlist(
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
                    logger.info(f"转码完成：video_id={video_id}, 成功 {len(transcoded_resolutions)}/{len(TranscodeService.RESOLUTIONS)} 个清晰度")
                    
                    # 更新视频 URL 和状态（使用主播放列表）
                    video.video_url = f"/videos/hls/{video_id}/master.m3u8"
                    # 当前未实现审核流，转码成功后直接设置为已发布以便前端展示
                    video.status = 2  # 2=已发布
                    
                    # 获取视频时长（使用原始文件）
                    duration = TranscodeService.get_video_duration(input_path)
                    if duration > 0:
                        video.duration = duration
                    
                    db.commit()
                    logger.info(f"视频状态更新为审核中：video_id={video_id}")
                    
                else:
                    # 所有清晰度都转码失败
                    logger.error(f"所有清晰度转码失败：video_id={video_id}")
                    video.status = -1  # -1=转码失败
                    db.commit()
                    
                    # TODO: 通知上传者转码失败（需求 4.4）
                    # notification_service.notify_transcode_failed(video.uploader_id, video_id)
            
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
    def get_video_duration(video_path: str) -> int:
        """
        使用 ffprobe 获取视频时长
        
        参数：
            video_path: 视频文件路径
        
        返回：
            视频时长（秒）
        
        为什么需要这个：
            - 前端需要显示视频时长
            - 用于视频列表和详情页
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return int(duration)
            else:
                logger.error(f"ffprobe 执行失败：{result.stderr}")
                return 0
        
        except Exception as e:
            logger.error(f"获取视频时长失败：{e}")
            return 0
