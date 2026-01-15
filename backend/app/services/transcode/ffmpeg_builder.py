"""
FFmpeg 命令构建器

职责：构建 FFmpeg 转码命令
相当于 Java 的 FFmpegCommandBuilder
"""
import math
import os
from typing import Optional

from app.core.config import settings


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
        
        # 检查是否使用GPU硬件加速
        use_gpu = getattr(settings, 'TRANSCODE_USE_GPU', True)
        gpu_device = getattr(settings, 'TRANSCODE_GPU_DEVICE', 0)
        cpu_count = os.cpu_count() or 8
        cpu_threads = max(4, min(8, int(math.ceil(cpu_count * 0.4))))

        def _parse_resolution(value: str):
            if not value:
                return None
            parts = value.lower().split('x')
            if len(parts) != 2:
                return None
            try:
                width = int(parts[0])
                height = int(parts[1])
            except ValueError:
                return None
            if width <= 0 or height <= 0:
                return None
            return width, height

        def _normalize_bitrate_k(value: Optional[str]):
            if not value:
                return None
            raw = value.strip().lower()
            try:
                if raw.endswith('k'):
                    return int(float(raw[:-1]))
                if raw.endswith('m'):
                    return int(float(raw[:-1]) * 1000)
                number = float(raw)
            except ValueError:
                return None
            if number <= 0:
                return None
            if number > 10000:
                return int(number / 1000)
            return int(number)
        
        # 构建FFmpeg命令
        command = ['ffmpeg']
        
        # 输入选项（必须在 -i 之前）
        # 注意：如果输入视频是AV1编码，NVENC不支持AV1硬件解码，需要CPU解码
        # 但可以使用GPU进行编码和缩放，所以这里不添加硬件解码选项
        # 如果输入是H.264/H.265，可以添加硬件解码以提高效率
        
        # 输入文件
        command.extend(['-i', input_path])
        
        # 输出选项（必须在 -i 之后）
        # 如果指定了分辨率，添加缩放滤镜
        if resolution:
            if use_gpu:
                # GPU硬件加速：使用GPU缩放
                resolution_dims = _parse_resolution(resolution)
                if resolution_dims:
                    width, height = resolution_dims
                    command.extend([
                        '-vf',
                        f'hwupload_cuda,scale_cuda=w={width}:h={height}:format=nv12',
                    ])
                else:
                    command.extend(['-vf', f'hwupload_cuda,scale_cuda={resolution}'])
            else:
                # CPU转码：使用CPU缩放
                command.extend(['-vf', f'scale={resolution}'])
        
        if use_gpu:
            # GPU硬件加速编码（NVENC H.264）
            # 注意：输入视频可能是AV1编码，NVENC不支持AV1解码，需要CPU解码
            # 但可以使用GPU进行编码和缩放，提高效率
            bitrate_k = _normalize_bitrate_k(video_bitrate)
            maxrate = f"{int(bitrate_k * 1.2)}k" if bitrate_k else '2400k'
            bufsize = f"{int(bitrate_k * 2)}k" if bitrate_k else '4000k'
            command.extend([
                '-c:v', 'h264_nvenc',    # NVIDIA硬件编码器（RTX 3050支持）
                '-preset', 'p3',         # NVENC preset: p3 favors speed (p1 fastest, p7 slowest/best quality)
                '-rc', 'vbr',            # 码率控制模式：VBR（可变码率）
                '-rc-lookahead', '8',
                '-bf', '2',
                '-gpu', str(gpu_device),
                '-b:v', video_bitrate if video_bitrate else '2000k',  # 目标码率
                '-maxrate', maxrate,     # 最大码率（目标码率的1.2倍）
                '-bufsize', bufsize,     # 缓冲区大小（目标码率的2倍）
            ])
        else:
            # CPU软件编码（libx264）
            # 优化策略：降低CPU占用但保持转码效率
            # 1. 使用 fast preset（更快的编码速度）
            # 2. 使用 CRF 模式（恒定质量）而不是码率模式，更高效
            # 3. 线程数约为CPU的40%（提升速度同时避免过度占用）
            # 4. 使用 film tune（适合视频内容，比 zerolatency 更高效）
            command.extend([
                '-c:v', 'libx264',          # 视频编码器
                '-preset', 'fast',          # 编码速度：fast 提升转码速度
                '-crf', '23',               # 质量因子：23 是较好的平衡点（18-28范围，越小质量越好）
                '-threads', str(cpu_threads),  # 转码线程数：约占CPU 40%
                '-tune', 'film',            # 视频内容调优（适合视频内容，比 zerolatency 更高效）
                '-movflags', '+faststart',   # 优化网络播放（将元数据移到文件开头）
            ])
            # 如果指定了视频码率，使用码率模式（覆盖CRF）
            if video_bitrate:
                # 移除 CRF，使用码率模式
                command = [cmd for cmd in command if cmd != '-crf' and cmd != '23']
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
