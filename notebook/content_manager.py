"""
内容管理器

负责管理带时间戳的图片和文字内容，提供内容的添加、过滤、
分组和查询功能，是图文混排笔记系统的核心组件。
"""

import os
import json
from typing import List, Dict, Optional, Union, Tuple, Callable
from pathlib import Path
from .notebook_content import (
    TimeStampedContent, ImageContent, TextContent, ContentGroup,
    TimeRange, create_image_content, create_text_content,
    group_content_by_time
)


class ContentManager:
    """内容管理器 - 管理所有带时间戳的内容"""
    
    def __init__(self):
        self.contents: List[TimeStampedContent] = []
        self._content_groups: Optional[List[ContentGroup]] = None
        self._group_time_window: float = 30.0  # 默认时间窗口
    
    def clear(self):
        """清空所有内容"""
        self.contents.clear()
        self._content_groups = None
    
    def add_content(self, content: TimeStampedContent):
        """添加单个内容"""
        if not content.is_valid():
            raise ValueError(f"Invalid content: {content}")
        
        self.contents.append(content)
        self._content_groups = None  # 清除缓存的分组
    
    def add_image(self, 
                  image_path: str, 
                  timestamp: float, 
                  **kwargs) -> ImageContent:
        """添加图片内容"""
        image_content = create_image_content(image_path, timestamp, **kwargs)
        self.add_content(image_content)
        return image_content
    
    def add_text(self, 
                 text: str, 
                 timestamp: float, 
                 **kwargs) -> TextContent:
        """添加文字内容"""
        text_content = create_text_content(text, timestamp, **kwargs)
        self.add_content(text_content)
        return text_content
    
    def add_images_from_directory(self, 
                                 directory: str, 
                                 timestamp_extractor: Optional[Callable[[str], float]] = None,
                                 **kwargs) -> List[ImageContent]:
        """
        从目录批量添加图片
        
        Args:
            directory: 图片目录
            timestamp_extractor: 从文件名提取时间戳的函数
            **kwargs: 传递给ImageContent的额外参数
            
        Returns:
            添加的图片内容列表
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}
        image_files = []
        
        for file_path in Path(directory).iterdir():
            if file_path.suffix.lower() in image_extensions:
                image_files.append(file_path)
        
        # 按文件名排序
        image_files.sort()
        
        added_images = []
        for i, image_path in enumerate(image_files):
            # 提取时间戳
            if timestamp_extractor:
                timestamp = timestamp_extractor(str(image_path))
            else:
                # 默认：按顺序分配时间戳，每张图片间隔1秒
                timestamp = float(i)
            
            try:
                image_content = self.add_image(str(image_path), timestamp, **kwargs)
                added_images.append(image_content)
            except Exception as e:
                print(f"Warning: Failed to add image {image_path}: {e}")
        
        print(f"Added {len(added_images)} images from {directory}")
        return added_images
    
    def load_from_json(self, json_path: str):
        """从JSON文件加载内容"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data.get('contents', []):
            content_type = item.get('content_type')
            timestamp = item.get('timestamp')
            
            if content_type == 'image':
                self.add_image(
                    image_path=item.get('image_path'),
                    timestamp=timestamp,
                    caption=item.get('caption'),
                    quality_score=item.get('quality_score'),
                    source=item.get('source'),
                    metadata=item.get('metadata', {})
                )
            elif content_type == 'text':
                self.add_text(
                    text=item.get('text'),
                    timestamp=timestamp,
                    confidence=item.get('confidence'),
                    speaker=item.get('speaker'),
                    language=item.get('language'),
                    source=item.get('source'),
                    duration=item.get('duration'),
                    metadata=item.get('metadata', {})
                )
    
    def save_to_json(self, json_path: str):
        """保存内容到JSON文件"""
        data = {
            'contents': [],
            'metadata': {
                'total_count': len(self.contents),
                'image_count': len(self.get_images()),
                'text_count': len(self.get_texts()),
                'time_range': self.get_time_range_info()
            }
        }
        
        for content in self.contents:
            item = {
                'content_type': content.content_type,
                'timestamp': content.timestamp,
                'duration': content.duration,
                'metadata': content.metadata
            }
            
            if isinstance(content, ImageContent):
                item.update({
                    'image_path': content.image_path,
                    'caption': content.caption,
                    'width': content.width,
                    'height': content.height,
                    'quality_score': content.quality_score,
                    'source': content.source
                })
            elif isinstance(content, TextContent):
                item.update({
                    'text': content.text,
                    'confidence': content.confidence,
                    'speaker': content.speaker,
                    'language': content.language,
                    'source': content.source
                })
            
            data['contents'].append(item)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(self.contents)} contents to {json_path}")
    
    def filter_by_time_range(self, 
                           start_time: float, 
                           end_time: float) -> List[TimeStampedContent]:
        """按时间范围过滤内容"""
        time_range = TimeRange(start_time, end_time)
        return [content for content in self.contents 
                if time_range.contains(content.timestamp)]
    
    def filter_by_content_type(self, content_type: str) -> List[TimeStampedContent]:
        """按内容类型过滤"""
        return [content for content in self.contents 
                if content.content_type == content_type]
    
    def get_images(self) -> List[ImageContent]:
        """获取所有图片内容"""
        return [content for content in self.contents 
                if isinstance(content, ImageContent)]
    
    def get_texts(self) -> List[TextContent]:
        """获取所有文字内容"""
        return [content for content in self.contents 
                if isinstance(content, TextContent)]
    
    def get_sorted_contents(self) -> List[TimeStampedContent]:
        """获取按时间戳排序的内容"""
        return sorted(self.contents, key=lambda x: x.timestamp)
    
    def get_content_groups(self, 
                          time_window: Optional[float] = None,
                          force_refresh: bool = False) -> List[ContentGroup]:
        """
        获取内容分组
        
        Args:
            time_window: 时间窗口大小（秒），None使用默认值
            force_refresh: 是否强制刷新缓存
            
        Returns:
            内容组列表
        """
        if time_window is None:
            time_window = self._group_time_window
        
        # 检查是否需要重新分组
        if (self._content_groups is None or 
            force_refresh or 
            time_window != self._group_time_window):
            
            self._content_groups = group_content_by_time(self.contents, time_window)
            self._group_time_window = time_window
        
        return self._content_groups
    
    def get_time_range_info(self) -> Optional[Dict[str, float]]:
        """获取时间范围信息"""
        if not self.contents:
            return None
        
        timestamps = [content.timestamp for content in self.contents]
        return {
            'start_time': min(timestamps),
            'end_time': max(timestamps),
            'duration': max(timestamps) - min(timestamps)
        }
    
    def get_statistics(self) -> Dict[str, Union[int, float, Dict]]:
        """获取内容统计信息"""
        images = self.get_images()
        texts = self.get_texts()
        time_info = self.get_time_range_info()
        
        stats = {
            'total_contents': len(self.contents),
            'image_count': len(images),
            'text_count': len(texts),
            'time_range': time_info,
            'content_distribution': {}
        }
        
        # 按来源统计
        sources = {}
        for content in self.contents:
            source = getattr(content, 'source', 'unknown') or 'unknown'
            sources[source] = sources.get(source, 0) + 1
        stats['content_distribution']['by_source'] = sources
        
        # 图片质量统计
        if images:
            quality_scores = [img.quality_score for img in images 
                            if img.quality_score is not None]
            if quality_scores:
                stats['image_quality'] = {
                    'avg_quality': sum(quality_scores) / len(quality_scores),
                    'min_quality': min(quality_scores),
                    'max_quality': max(quality_scores)
                }
        
        # 文字置信度统计
        if texts:
            confidences = [text.confidence for text in texts 
                          if text.confidence is not None]
            if confidences:
                stats['text_confidence'] = {
                    'avg_confidence': sum(confidences) / len(confidences),
                    'min_confidence': min(confidences),
                    'max_confidence': max(confidences)
                }
        
        return stats
    
    def validate_contents(self) -> Tuple[List[TimeStampedContent], List[str]]:
        """
        验证所有内容的有效性
        
        Returns:
            (有效内容列表, 错误信息列表)
        """
        valid_contents = []
        errors = []
        
        for i, content in enumerate(self.contents):
            try:
                if content.is_valid():
                    valid_contents.append(content)
                else:
                    errors.append(f"Content {i}: Invalid content - {content}")
            except Exception as e:
                errors.append(f"Content {i}: Validation error - {e}")
        
        return valid_contents, errors
    
    def __len__(self) -> int:
        """返回内容数量"""
        return len(self.contents)
    
    def __str__(self) -> str:
        """返回管理器摘要"""
        stats = self.get_statistics()
        return (f"ContentManager({stats['total_contents']} contents: "
                f"{stats['image_count']} images, {stats['text_count']} texts)")


# 使用示例
if __name__ == "__main__":
    # 创建内容管理器
    manager = ContentManager()
    
    # 添加示例内容
    manager.add_image("frame_001.jpg", 10.0, caption="开场PPT", quality_score=0.95)
    manager.add_text("欢迎大家参加今天的讲座", 12.0, confidence=0.92, speaker="讲师")
    manager.add_image("frame_002.jpg", 45.0, caption="主题介绍", quality_score=0.88)
    manager.add_text("今天我们要讨论人工智能的发展", 47.0, confidence=0.89, speaker="讲师")
    
    # 显示统计信息
    print("Content Manager Statistics:")
    print(manager)
    
    stats = manager.get_statistics()
    print(f"Time range: {stats['time_range']}")
    
    # 获取内容分组
    groups = manager.get_content_groups(time_window=30.0)
    print(f"\nContent groups ({len(groups)}):")
    for i, group in enumerate(groups):
        print(f"  Group {i+1}: {group}")
    
    print("\nContentManager ready")
