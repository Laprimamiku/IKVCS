"""
FFmpeg 命令构建器

职责：构建 FFmpeg 转码命令
相当于 Java 的 FFmpegCommandBuilder
"""
import os
from typing import Optional


class FFmpegBuilder:
    """FFmpeg 命令构建器"""
    
    @staticmethod
    def build_ffmpeg_command(
        input_path: str, 
        output_path: str,
        resolution: Optional[str] = None,
        video_bitrate: Optional[str] = None,
        audio_bitrate: Optional[str] = None
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
            '-preset', 'ultrafast',     # 编码速度：ultrafast 最快速度，最低 CPU 占用
            '-crf', '23',               # 质量因子：23 是较好的平衡点（18-28范围，越小质量越好）
            '-threads', '1',            # 限制转码线程数为 1（进一步降低 CPU 占用）
            '-tune', 'zerolatency',     # 低延迟调优，适合流式播放
            '-movflags', '+faststart',   # 优化网络播放（将元数据移到文件开头）
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

