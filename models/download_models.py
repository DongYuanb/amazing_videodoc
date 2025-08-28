"""下载相关数据模型"""
from typing import Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum


class DownloadQuality(str, Enum):
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


class Platform(str, Enum):
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"


class DownloadUrlRequest(BaseModel):
    url: str
    quality: DownloadQuality = DownloadQuality.MEDIUM
    platform: Optional[Platform] = None  # 自动检测或手动指定


class VideoDownloadResult(BaseModel):
    file_path: str
    title: str
    duration: float  # 改为float以支持小数秒
    cover_url: Optional[str] = None
    platform: str
    video_id: str
    raw_info: Optional[Dict[str, Any]] = None


class DownloadStatus(BaseModel):
    task_id: str
    status: str  # downloading, processing, completed, failed
    platform: Optional[str] = None
    title: Optional[str] = None
    error_message: Optional[str] = None
