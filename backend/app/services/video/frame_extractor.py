"""
视频帧提取服务

职责：
1. 使用 FFmpeg 从视频中提取关键帧
2. 支持多种提取策略（均匀采样、I帧、场景切换）
3. 保存帧文件到指定目录
"""

import os
import subprocess
import logging
from typing import List, Dict, Any
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class FrameExtractor:
    """视频帧提取器"""
    
    def __init__(self, storage_path: str = None):
        """
        初始化帧提取器
        
        参数:
            storage_path: 帧存储路径，默认使用配置中的路径
        """
        self.storage_path = storage_path or os.path.join(
            settings.STORAGE_ROOT, "frames"
        )
        # 确保存储目录存在
        os.makedirs(self.storage_path, exist_ok=True)
    
    def extract_frames(
        self,
        video_path: str,
        video_id: int,
        strategy: str = "hybrid",
        interval: int = None,
        max_frames: int = None
    ) -> List[Dict[str, Any]]:
        """
        从视频中提取帧（智能采样，平衡性能和准确率）
        
        参数:
            video_path: 视频文件路径（可以是原始mp4或m3u8主文件）
            video_id: 视频ID
            strategy: 提取策略
                - "uniform": 均匀采样（每隔N秒提取一帧）
                - "keyframe": I帧提取
                - "scene_change": 场景切换检测
                - "hybrid": 混合策略（均匀采样 + 关键帧，推荐）
            interval: 均匀采样间隔（秒），默认从配置读取
            max_frames: 最多提取的帧数量，默认从配置读取
        
        返回:
            List[Dict]: 帧信息列表（已限制数量），每个元素包含：
                - frame_time: 帧对应的时间（秒）
                - frame_path: 帧文件路径（相对于storage根目录）
                - frame_type: 帧类型
        """
        # 使用配置默认值
        if interval is None:
            interval = getattr(settings, 'FRAME_EXTRACT_INTERVAL', 5)
        if max_frames is None:
            # 优先使用 MAX_FRAMES_PER_VIDEO，如果没有则使用 FRAME_EXTRACT_MAX_COUNT
            max_frames = getattr(settings, 'MAX_FRAMES_PER_VIDEO', None) or getattr(settings, 'FRAME_EXTRACT_MAX_COUNT', 50)
        min_frames = getattr(settings, 'FRAME_EXTRACT_MIN_FRAMES', 10)
        
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return []
        
        # 获取视频时长，用于智能调整采样策略
        video_duration = self._get_video_duration(video_path)
        
        # 根据视频时长动态调整采样间隔和最大帧数
        if video_duration > 0:
            if video_duration < 120:  # 短视频（<2分钟）
                interval = 3  # 每3秒一帧
                max_frames = 20
            elif video_duration < 600:  # 中等视频（2-10分钟）
                interval = 10  # 每10秒一帧
                max_frames = 30
            else:  # 长视频（>10分钟）
                interval = 20  # 每20秒一帧
                max_frames = 40
            logger.info(f"视频时长 {video_duration}秒，使用采样间隔 {interval}秒，最多提取 {max_frames} 帧")
        
        # 创建视频专用的帧存储目录
        video_frame_dir = os.path.join(self.storage_path, str(video_id))
        os.makedirs(video_frame_dir, exist_ok=True)
        
        frames = []
        
        try:
            # 只使用均匀采样策略，简化逻辑
            if strategy == "hybrid" or strategy == "uniform":
                frames = self._extract_uniform_frames(
                    video_path, video_id, video_frame_dir, interval
                )
            elif strategy == "keyframe":
                frames = self._extract_keyframes(
                    video_path, video_id, video_frame_dir
                )
            elif strategy == "scene_change":
                frames = self._extract_scene_change_frames(
                    video_path, video_id, video_frame_dir
                )
            else:
                logger.warning(f"未知的提取策略: {strategy}，使用默认策略 uniform")
                frames = self._extract_uniform_frames(
                    video_path, video_id, video_frame_dir, interval
                )
            
            # 限制帧数量（如果超过限制，均匀采样选择）
            if len(frames) > max_frames:
                logger.info(f"提取了 {len(frames)} 帧，超过限制 {max_frames}，进行采样")
                # 均匀采样选择帧
                step = len(frames) / max_frames
                selected_frames = []
                for i in range(max_frames):
                    idx = int(i * step)
                    if idx < len(frames):
                        selected_frames.append(frames[idx])
                frames = selected_frames
                logger.info(f"采样后保留 {len(frames)} 帧")
            
            logger.info(f"成功提取 {len(frames)} 帧，video_id={video_id}, duration={video_duration}秒")
            return frames
            
        except Exception as e:
            logger.error(f"提取帧失败: {e}", exc_info=True)
            return []
    
    def _extract_uniform_frames(
        self,
        video_path: str,
        video_id: int,
        output_dir: str,
        interval: int
    ) -> List[Dict[str, Any]]:
        """
        均匀采样提取帧（每隔N秒提取一帧）
        
        使用 FFmpeg 命令：
        ffmpeg -i input.mp4 -vf "fps=1/10" -q:v 2 frames/frame_%04d.jpg
        """
        frames = []
        
        # 构建 FFmpeg 命令
        # 注意：FFmpeg 的 image2 输出格式需要使用整数格式（%04d），不支持浮点数格式
        output_pattern = os.path.join(output_dir, "frame_%04d.jpg")
        
        # 使用 fps 过滤器按时间间隔提取帧
        # fps=1/{interval} 表示每 interval 秒提取一帧
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'fps=1/{interval}',  # 每N秒一帧
            '-q:v', '2',  # 高质量JPEG
            '-y',  # 覆盖已存在文件
            output_pattern
        ]
        
        try:
            logger.info(f"开始提取帧: video_id={video_id}, interval={interval}秒, output_dir={output_dir}")
            # 执行 FFmpeg 命令
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode()
                logger.error(f"FFmpeg 提取帧失败: video_id={video_id}, error={error_msg}")
                return []
            
            # 扫描输出目录，获取所有提取的帧
            frame_files = sorted(Path(output_dir).glob("frame_*.jpg"))
            logger.info(f"扫描到 {len(frame_files)} 个帧文件: video_id={video_id}, output_dir={output_dir}")
            
            if not frame_files:
                logger.warning(f"未找到提取的帧文件: video_id={video_id}, output_dir={output_dir}")
                return []
            
            for idx, frame_file in enumerate(frame_files):
                # 从文件索引计算时间（frame_0001.jpg 对应第1帧，时间 = 索引 * interval）
                # 注意：由于使用了 select 过滤器，帧的顺序可能不完全按时间顺序
                # 这里简化处理，使用索引估算时间
                frame_time = idx * interval
                
                # 计算相对于 storage 根目录的路径
                relative_path = os.path.relpath(
                    str(frame_file),
                    settings.STORAGE_ROOT
                ).replace("\\", "/")  # Windows路径转Unix风格
                
                frames.append({
                    "frame_time": frame_time,
                    "frame_path": relative_path,
                    "frame_type": "uniform"
                })
            
            return frames
            
        except subprocess.TimeoutExpired:
            logger.error(f"提取帧超时: video_id={video_id}")
            return []
        except Exception as e:
            logger.error(f"提取帧异常: {e}", exc_info=True)
            return []
    
    def _extract_keyframes(
        self,
        video_path: str,
        video_id: int,
        output_dir: str
    ) -> List[Dict[str, Any]]:
        """
        提取 I 帧（关键帧）
        
        使用 FFmpeg 命令：
        ffmpeg -i input.mp4 -vf "select='eq(pict_type,I)'" -vsync vfr frames/frame_%04d.jpg
        """
        frames = []
        
        output_pattern = os.path.join(output_dir, "frame_%04d.jpg")
        
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vf', "select='eq(pict_type,I)'",  # 只选择I帧
            '-vsync', 'vfr',  # 可变帧率
            '-q:v', '2',
            '-y',
            output_pattern
        ]
        
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg 提取I帧失败: {result.stderr.decode()}")
                return []
            
            # 扫描输出目录
            frame_files = sorted(Path(output_dir).glob("frame_*.jpg"))
            
            # 对于I帧，需要从视频中获取每个帧的时间戳
            # 这里简化处理，使用文件索引估算时间
            for idx, frame_file in enumerate(frame_files):
                # 简化：使用索引估算时间（实际应该从视频元数据获取）
                frame_time = idx * 2.0  # 假设平均每2秒一个I帧
                
                relative_path = os.path.relpath(
                    str(frame_file),
                    settings.STORAGE_ROOT
                ).replace("\\", "/")
                
                frames.append({
                    "frame_time": frame_time,
                    "frame_path": relative_path,
                    "frame_type": "keyframe"
                })
            
            return frames
            
        except Exception as e:
            logger.error(f"提取I帧异常: {e}", exc_info=True)
            return []
    
    def _extract_scene_change_frames(
        self,
        video_path: str,
        video_id: int,
        output_dir: str
    ) -> List[Dict[str, Any]]:
        """
        场景切换检测提取帧
        
        使用 FFmpeg 命令：
        ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)'" -vsync vfr frames/frame_%04d.jpg
        """
        # 场景切换检测比较复杂，这里先使用均匀采样作为fallback
        logger.info(f"场景切换检测暂未实现，使用均匀采样替代: video_id={video_id}")
        return self._extract_uniform_frames(video_path, video_id, output_dir, 10)
    
    def _get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长（秒）
        
        参数:
            video_path: 视频文件路径
        
        返回:
            float: 视频时长（秒），如果获取失败返回0
        """
        try:
            command = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10
            )
            if result.returncode == 0:
                duration = float(result.stdout.decode().strip())
                return duration
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
        return 0.0


# 全局实例
frame_extractor = FrameExtractor()

