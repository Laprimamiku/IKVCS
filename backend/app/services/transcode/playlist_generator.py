"""
播放列表生成器

职责：生成 HLS 播放列表文件
相当于 Java 的 PlaylistGenerator
"""
from typing import List, Tuple


class PlaylistGenerator:
    """播放列表生成器"""
    
    @staticmethod
    def build_master_playlist(
        video_id: int,
        resolutions: List[Tuple[str, str, int]]
    ) -> str:
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
            playlist += f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}\n"
            playlist += f"{name}/index.m3u8\n\n"
        
        return playlist

