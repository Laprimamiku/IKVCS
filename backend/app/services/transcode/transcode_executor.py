"""
转码执行器

职责：执行 FFmpeg 转码任务
相当于 Java 的 TranscodeExecutor
"""
import subprocess
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TranscodeExecutor:
    """转码执行器"""
    
    @staticmethod
    def execute_transcode(
        command: list,
        timeout: int = 3600
    ) -> Tuple[int, bytes]:
        """
        执行转码命令
        
        参数：
            command: FFmpeg 命令列表
            timeout: 超时时间（秒），默认 1 小时
        
        返回：
            Tuple[int, bytes]: (返回码, 错误输出)
        """
        try:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout
            )
            return process.returncode, process.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"转码超时：{timeout} 秒")
            return 1, "转码超时".encode("utf-8")
        except Exception as e:
            logger.error(f"FFmpeg 执行失败: {e}")
            return 1, str(e).encode()
    
    @staticmethod
    def get_video_duration(video_path: str) -> int:
        """
        使用 ffprobe 获取视频时长
        
        参数：
            video_path: 视频文件路径
        
        返回：
            视频时长（秒）
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

