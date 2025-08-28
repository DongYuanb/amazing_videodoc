"""平台识别服务"""
import re
from typing import Optional
from models.download_models import Platform


class PlatformDetector:
    """视频平台识别器"""
    
    # 平台URL模式
    PLATFORM_PATTERNS = {
        Platform.YOUTUBE: [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/.*[?&]v=([a-zA-Z0-9_-]+)',
        ],
        Platform.BILIBILI: [
            r'bilibili\.com/video/([a-zA-Z0-9]+)',
            r'b23\.tv/([a-zA-Z0-9]+)',
        ],
    }
    
    @classmethod
    def detect_platform(cls, url: str) -> Optional[Platform]:
        """
        检测视频URL所属的平台
        """
        url = url.lower().strip()
        
        for platform, patterns in cls.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url):
                    return platform
        
        return None
    
    @classmethod
    def extract_video_id(cls, url: str, platform: Platform) -> Optional[str]:
        """
        提取视频ID
        """
        if platform not in cls.PLATFORM_PATTERNS:
            return None
        
        for pattern in cls.PLATFORM_PATTERNS[platform]:
            match = re.search(pattern, url.lower())
            if match:
                return match.group(1)
        
        return None
    
    @classmethod
    def is_supported_platform(cls, url: str) -> bool:
        """检查URL是否为支持的平台"""
        return cls.detect_platform(url) is not None
    
    @classmethod
    def get_supported_platforms(cls) -> list[str]:
        """获取支持的平台列表"""
        return [platform.value for platform in Platform]
