"""视频下载服务 - 重构版本"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import yt_dlp

from models.download_models import Platform, DownloadQuality, VideoDownloadResult


class BaseDownloader(ABC):
    """下载器基类"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    @abstractmethod
    def download_video(self, url: str, output_dir: str, quality: DownloadQuality = DownloadQuality.MEDIUM) -> VideoDownloadResult:
        """下载视频"""
        pass
    
    @abstractmethod
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """获取视频信息"""
        pass


class YouTubeDownloader(BaseDownloader):
    """YouTube下载器"""
    
    def download_video(self, url: str, output_dir: str, quality: DownloadQuality = DownloadQuality.MEDIUM) -> VideoDownloadResult:
        """下载YouTube视频"""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "%(id)s.%(ext)s")
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_path,
            'noplaylist': True,
            'quiet': True,
            'merge_output_format': 'mp4',
            'socket_timeout': 15,
            'retries': 2,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info.get("id")
                title = info.get("title", "Unknown")
                duration = float(info.get("duration", 0))  # 确保转换为float
                cover_url = info.get("thumbnail")
                
                video_path = os.path.join(output_dir, f"{video_id}.mp4")
                
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"视频文件未找到: {video_path}")
                
                return VideoDownloadResult(
                    file_path=video_path,
                    title=title,
                    duration=duration,
                    cover_url=cover_url,
                    platform="youtube",
                    video_id=video_id,
                    raw_info={"tags": info.get('tags', [])}
                )
        except Exception as e:
            self.logger.error(f"YouTube下载失败: {e}")
            raise RuntimeError(f"YouTube下载失败: {e}")
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """获取YouTube视频信息"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 10,
            'retries': 2,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": float(info.get("duration", 0)),  # 确保转换为float
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "view_count": info.get("view_count"),
                }
        except Exception as e:
            self.logger.error(f"获取YouTube视频信息失败: {e}")
            raise RuntimeError(f"获取视频信息失败: {e}")


class BilibiliDownloader(BaseDownloader):
    """Bilibili下载器"""
    
    def download_video(self, url: str, output_dir: str, quality: DownloadQuality = DownloadQuality.MEDIUM) -> VideoDownloadResult:
        """下载Bilibili视频"""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "%(id)s.%(ext)s")
        
        ydl_opts = {
            'format': 'bv*+ba/best',
            'outtmpl': output_path,
            'noplaylist': True,
            'quiet': True,
            'merge_output_format': 'mp4',
            'socket_timeout': 15,
            'retries': 2,
        }
                
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info.get("id")
                title = info.get("title", "Unknown")
                duration = float(info.get("duration", 0))  # 确保转换为float
                cover_url = info.get("thumbnail")
                
                video_path = os.path.join(output_dir, f"{video_id}.mp4")
                
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"视频文件未找到: {video_path}")
                
                return VideoDownloadResult(
                    file_path=video_path,
                    title=title,
                    duration=duration,
                    cover_url=cover_url,
                    platform="bilibili",
                    video_id=video_id,
                    raw_info={"uploader": info.get("uploader")}
                )
        except Exception as e:
            self.logger.error(f"Bilibili下载失败: {e}")
            raise RuntimeError(f"Bilibili下载失败: {e}")
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """获取Bilibili视频信息"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 10,
            'retries': 2,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": float(info.get("duration", 0)),  # 确保转换为float
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "view_count": info.get("view_count"),
                }
        except Exception as e:
            self.logger.error(f"获取Bilibili视频信息失败: {e}")
            raise RuntimeError(f"获取视频信息失败: {e}")


class VideoDownloaderService:
    """视频下载服务"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.downloaders = {
            Platform.YOUTUBE: YouTubeDownloader(logger),
            Platform.BILIBILI: BilibiliDownloader(logger),
            # 其他平台下载器可以后续添加
        }
    
    def get_downloader(self, platform: Platform) -> BaseDownloader:
        """获取指定平台的下载器"""
        if platform not in self.downloaders:
            raise ValueError(f"不支持的平台: {platform}")
        return self.downloaders[platform]
    
    def download_video(self, url: str, platform: Platform, output_dir: str, 
                      quality: DownloadQuality = DownloadQuality.FAST) -> VideoDownloadResult:
        """下载视频"""
        downloader = self.get_downloader(platform)
        return downloader.download_video(url, output_dir, quality)
    
    def get_video_info(self, url: str, platform: Platform) -> Dict[str, Any]:
        """获取视频信息"""
        downloader = self.get_downloader(platform)
        return downloader.get_video_info(url)
    
    def is_platform_supported(self, platform: Platform) -> bool:
        """检查平台是否支持"""
        return platform in self.downloaders
