"""
FFmpeg 命令构建器

职责：构建 FFmpeg 转码命令
相当于 Java 的 FFmpegCommandBuilder
"""
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
        use_gpu = getattr(settings, 'TRANSCODE_USE_GPU', False)
        gpu_device = getattr(settings, 'TRANSCODE_GPU_DEVICE', 0)
        
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
                command.extend(['-vf', f'scale_cuda={resolution}'])
            else:
                # CPU转码：使用CPU缩放
                command.extend(['-vf', f'scale={resolution}'])
        
        if use_gpu:
            # GPU硬件加速编码（NVENC H.264）
            # 注意：输入视频可能是AV1编码，NVENC不支持AV1解码，需要CPU解码
            # 但可以使用GPU进行编码和缩放，提高效率
            command.extend([
                '-c:v', 'h264_nvenc',    # NVIDIA硬件编码器（RTX 3050支持）
                '-preset', 'p4',         # NVENC预设：p4平衡速度和质量（p1最快，p7最慢但质量最好）
                '-rc', 'vbr',            # 码率控制模式：VBR（可变码率）
                '-b:v', video_bitrate if video_bitrate else '2000k',  # 目标码率
                '-maxrate', str(int(video_bitrate.replace('k', '')) * 1.2) + 'k' if video_bitrate else '2400k',  # 最大码率（目标码率的1.2倍）
                '-bufsize', str(int(video_bitrate.replace('k', '')) * 2) + 'k' if video_bitrate else '4000k',  # 缓冲区大小（目标码率的2倍）
            ])
        else:
            # CPU软件编码（libx264）
            # 优化策略：降低CPU占用但保持转码效率
            # 1. 使用 medium preset（比 fast 稍慢但质量更好，比 slow 快很多）
            # 2. 使用 CRF 模式（恒定质量）而不是码率模式，更高效
            # 3. 限制线程数为4（i5-11260H为6核12线程，使用4线程避免过度占用，留出资源给系统）
            # 4. 使用 film tune（适合视频内容，比 zerolatency 更高效）
            command.extend([
                '-c:v', 'libx264',          # 视频编码器
                '-preset', 'medium',        # 编码速度：medium 平衡速度和质量（比 fast 稍慢但质量更好，比 slow 快很多）
                '-crf', '23',               # 质量因子：23 是较好的平衡点（18-28范围，越小质量越好）
                '-threads', '4',            # 转码线程数：4线程（i5-11260H为6核12线程，使用4线程避免过度占用）
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

