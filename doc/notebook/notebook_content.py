"""
图文混排笔记内容数据结构

定义带时间戳的内容类型，用于表示图片和文字内容，
支持基于时间的内容匹配和组织。
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class TimeRange:
    """时间范围类"""
    start_time: float  # 开始时间（秒）
    end_time: float    # 结束时间（秒）
    
    def __post_init__(self):
        """验证时间范围"""
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be less than end_time")
    
    @property
    def duration(self) -> float:
        """获取持续时间"""
        return self.end_time - self.start_time
    
    @property
    def center_time(self) -> float:
        """获取中心时间点"""
        return (self.start_time + self.end_time) / 2
    
    def contains(self, timestamp: float) -> bool:
        """检查时间戳是否在范围内"""
        return self.start_time <= timestamp <= self.end_time
    
    def overlaps(self, other: 'TimeRange') -> bool:
        """检查是否与另一个时间范围重叠"""
        return not (self.end_time <= other.start_time or other.end_time <= self.start_time)
    
    def intersection(self, other: 'TimeRange') -> Optional['TimeRange']:
        """计算与另一个时间范围的交集"""
        if not self.overlaps(other):
            return None
        
        start = max(self.start_time, other.start_time)
        end = min(self.end_time, other.end_time)
        return TimeRange(start, end)
    
    def __str__(self) -> str:
        return f"TimeRange({self.start_time:.1f}s - {self.end_time:.1f}s)"


class TimeStampedContent(ABC):
    """带时间戳的内容基类"""

    def __init__(self, timestamp: float, duration: Optional[float] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.timestamp = timestamp
        self.duration = duration
        self.content_type = ""  # 子类中设置
        self.metadata = metadata or {}
    
    @property
    def time_range(self) -> TimeRange:
        """获取时间范围"""
        end_time = self.timestamp + (self.duration or 0)
        return TimeRange(self.timestamp, end_time)
    
    @abstractmethod
    def is_valid(self) -> bool:
        """检查内容是否有效"""
        pass
    
    @abstractmethod
    def get_summary(self) -> str:
        """获取内容摘要"""
        pass
    
    def __lt__(self, other: 'TimeStampedContent') -> bool:
        """支持按时间戳排序"""
        return self.timestamp < other.timestamp


class ImageContent(TimeStampedContent):
    """图片内容类"""

    def __init__(self, timestamp: float, image_path: str,
                 caption: Optional[str] = None,
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 quality_score: Optional[float] = None,
                 source: Optional[str] = None,
                 duration: Optional[float] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        super().__init__(timestamp, duration, metadata)
        self.content_type = "image"
        self.image_path = image_path
        self.caption = caption
        self.width = width
        self.height = height
        self.quality_score = quality_score
        self.source = source

        # 自动获取图片尺寸
        if self.width is None or self.height is None:
            self._load_image_info()
    
    def _load_image_info(self):
        """加载图片信息"""
        try:
            from PIL import Image
            with Image.open(self.image_path) as img:
                self.width, self.height = img.size
        except Exception as e:
            print(f"Warning: Failed to load image info for {self.image_path}: {e}")
            self.width = self.width or 800
            self.height = self.height or 600
    
    def is_valid(self) -> bool:
        """检查图片是否有效"""
        return (os.path.exists(self.image_path) and 
                self.width is not None and 
                self.height is not None and
                self.width > 0 and 
                self.height > 0)
    
    def get_summary(self) -> str:
        """获取图片摘要"""
        filename = Path(self.image_path).name
        size_info = f"{self.width}x{self.height}" if self.width and self.height else "unknown"
        quality_info = f" (quality: {self.quality_score:.2f})" if self.quality_score else ""
        return f"Image: {filename} [{size_info}]{quality_info}"
    
    @property
    def aspect_ratio(self) -> float:
        """获取宽高比"""
        if self.width and self.height and self.height > 0:
            return self.width / self.height
        return 1.0
    
    def __str__(self) -> str:
        return f"ImageContent({self.timestamp:.1f}s, {Path(self.image_path).name})"


class TextContent(TimeStampedContent):
    """文字内容类"""

    def __init__(self, timestamp: float, text: str,
                 confidence: Optional[float] = None,
                 speaker: Optional[str] = None,
                 language: Optional[str] = None,
                 source: Optional[str] = None,
                 duration: Optional[float] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        super().__init__(timestamp, duration, metadata)
        self.content_type = "text"
        self.text = text
        self.confidence = confidence
        self.speaker = speaker
        self.language = language
        self.source = source
    
    def is_valid(self) -> bool:
        """检查文字是否有效"""
        return bool(self.text and self.text.strip())
    
    def get_summary(self) -> str:
        """获取文字摘要"""
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        confidence_info = f" (conf: {self.confidence:.2f})" if self.confidence else ""
        speaker_info = f" [{self.speaker}]" if self.speaker else ""
        return f"Text: {preview}{speaker_info}{confidence_info}"
    
    @property
    def word_count(self) -> int:
        """获取字数"""
        return len(self.text.split())
    
    @property
    def char_count(self) -> int:
        """获取字符数"""
        return len(self.text)
    
    def __str__(self) -> str:
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"TextContent({self.timestamp:.1f}s, '{preview}')"


@dataclass
class ContentGroup:
    """内容组 - 表示同一时间段内的相关内容"""
    time_range: TimeRange
    images: List[ImageContent] = field(default_factory=list)
    texts: List[TextContent] = field(default_factory=list)
    title: Optional[str] = None  # 组标题
    
    @property
    def total_content_count(self) -> int:
        """获取总内容数量"""
        return len(self.images) + len(self.texts)
    
    @property
    def has_images(self) -> bool:
        """是否包含图片"""
        return len(self.images) > 0
    
    @property
    def has_texts(self) -> bool:
        """是否包含文字"""
        return len(self.texts) > 0
    
    @property
    def is_mixed_content(self) -> bool:
        """是否为图文混合内容"""
        return self.has_images and self.has_texts
    
    def add_content(self, content: TimeStampedContent):
        """添加内容到组中"""
        if isinstance(content, ImageContent):
            self.images.append(content)
        elif isinstance(content, TextContent):
            self.texts.append(content)
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")
    
    def get_all_content(self) -> List[TimeStampedContent]:
        """获取所有内容，按时间戳排序"""
        all_content = self.images + self.texts
        return sorted(all_content, key=lambda x: x.timestamp)
    
    def get_summary(self) -> str:
        """获取组摘要"""
        img_count = len(self.images)
        text_count = len(self.texts)
        return f"ContentGroup({self.time_range}, {img_count} images, {text_count} texts)"
    
    def __str__(self) -> str:
        return self.get_summary()


def create_image_content(image_path: str, 
                        timestamp: float, 
                        **kwargs) -> ImageContent:
    """便捷函数：创建图片内容"""
    return ImageContent(
        timestamp=timestamp,
        image_path=image_path,
        **kwargs
    )


def create_text_content(text: str, 
                       timestamp: float, 
                       **kwargs) -> TextContent:
    """便捷函数：创建文字内容"""
    return TextContent(
        timestamp=timestamp,
        text=text,
        **kwargs
    )


def group_content_by_time(contents: List[TimeStampedContent], 
                         time_window: float = 30.0) -> List[ContentGroup]:
    """
    按时间窗口将内容分组
    
    Args:
        contents: 内容列表
        time_window: 时间窗口大小（秒）
        
    Returns:
        内容组列表
    """
    if not contents:
        return []
    
    # 按时间戳排序
    sorted_contents = sorted(contents, key=lambda x: x.timestamp)
    
    groups = []
    current_group_start = sorted_contents[0].timestamp
    current_group_contents = []
    
    for content in sorted_contents:
        # 如果内容超出当前时间窗口，创建新组
        if content.timestamp - current_group_start > time_window:
            if current_group_contents:
                # 创建当前组
                time_range = TimeRange(
                    current_group_start,
                    current_group_start + time_window
                )
                group = ContentGroup(time_range)
                for c in current_group_contents:
                    group.add_content(c)
                groups.append(group)
            
            # 开始新组
            current_group_start = content.timestamp
            current_group_contents = [content]
        else:
            current_group_contents.append(content)
    
    # 处理最后一组
    if current_group_contents:
        time_range = TimeRange(
            current_group_start,
            current_group_contents[-1].timestamp + (current_group_contents[-1].duration or 0)
        )
        group = ContentGroup(time_range)
        for c in current_group_contents:
            group.add_content(c)
        groups.append(group)
    
    return groups


# 使用示例
if __name__ == "__main__":
    # 创建示例内容
    img1 = create_image_content("frame_001.jpg", 10.0, caption="PPT第一页")
    text1 = create_text_content("欢迎大家来到今天的讲座", 12.0, confidence=0.95)
    img2 = create_image_content("frame_002.jpg", 45.0, caption="PPT第二页")
    text2 = create_text_content("今天我们要讨论的主题是...", 47.0, confidence=0.88)
    
    # 按时间分组
    contents = [img1, text1, img2, text2]
    groups = group_content_by_time(contents, time_window=30.0)
    
    print("Content groups:")
    for i, group in enumerate(groups):
        print(f"  Group {i+1}: {group}")
        for content in group.get_all_content():
            print(f"    - {content}")
    
    print("\nNotebook content structures ready")
