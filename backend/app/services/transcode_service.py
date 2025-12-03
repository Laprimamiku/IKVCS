"""
视频转码服务
需求：4.1-4.5
"""
import asyncio
import subprocess
from pathlib import Path

# TODO: 从 config 导入配置
# from app.core.config import settings

async def transcode_video(video_id: int, input_path: str, output_path: str):
    """
    使用 FFmpeg 转码视频为 HLS/m3u8 格式
    
    参数：
        video_id: 视频 ID
        input_path: 输入视频路径
        output_path: 输出 m3u8 文件路径
    """
    # TODO: 实现视频转码
    # 1. 构建 FFmpeg 命令
    # 2. 执行转码
    # 3. 更新视频状态
    pass

def build_ffmpeg_command(input_path: str, output_path: str) -> list:
    """
    构建 FFmpeg 转码命令
    
    返回示例：
    [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-hls_time', '10',
        '-hls_list_size', '0',
        '-f', 'hls',
        output_path
    ]
    """
    # TODO: 实现命令构建
    pass
