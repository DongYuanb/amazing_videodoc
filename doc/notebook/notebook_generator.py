"""
图文混排笔记生成器

主控制器类，整合内容管理、布局引擎和PDF渲染功能，
提供完整的图文混排笔记生成解决方案。
"""

import os
import json
from typing import List, Dict, Any, Optional, Union, Callable
from pathlib import Path
from datetime import datetime

from .notebook_content import (
    TimeStampedContent, ImageContent, TextContent, ContentGroup, TimeRange
)
from .content_manager import ContentManager
from .layout_engine import (
    LayoutEngine, LayoutType, PageDimensions, create_layout_engine
)
from .pdf_renderer import PDFRenderer, PDFStyle, create_pdf_renderer


class NotebookConfig:
    """笔记生成配置"""
    
    def __init__(self):
        # 内容配置
        self.time_window = 30.0  # 内容分组时间窗口（秒）
        self.filter_time_range: Optional[TimeRange] = None  # 时间范围过滤
        
        # 布局配置
        self.layout_type = LayoutType.BALANCED  # 默认平衡布局
        self.page_dimensions = PageDimensions()  # 默认A4页面
        self.layout_config = {}  # 布局引擎特定配置
        
        # PDF配置
        self.pdf_title = "Generated Notebook"
        self.pdf_author = "Video Frame Deduplicator"
        self.show_timestamps = True
        self.show_page_numbers = True
        self.image_quality = 85
        
        # 输出配置
        self.output_dir = "output/notebooks"
        self.filename_template = "notebook_{timestamp}.pdf"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'time_window': self.time_window,
            'layout_type': self.layout_type.value,
            'pdf_title': self.pdf_title,
            'pdf_author': self.pdf_author,
            'show_timestamps': self.show_timestamps,
            'show_page_numbers': self.show_page_numbers,
            'image_quality': self.image_quality,
            'output_dir': self.output_dir,
            'filename_template': self.filename_template
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotebookConfig':
        """从字典创建配置"""
        config = cls()
        config.time_window = data.get('time_window', config.time_window)
        config.layout_type = LayoutType(data.get('layout_type', config.layout_type.value))
        config.pdf_title = data.get('pdf_title', config.pdf_title)
        config.pdf_author = data.get('pdf_author', config.pdf_author)
        config.show_timestamps = data.get('show_timestamps', config.show_timestamps)
        config.show_page_numbers = data.get('show_page_numbers', config.show_page_numbers)
        config.image_quality = data.get('image_quality', config.image_quality)
        config.output_dir = data.get('output_dir', config.output_dir)
        config.filename_template = data.get('filename_template', config.filename_template)
        return config


class NotebookGenerator:
    """图文混排笔记生成器 - 主控制器"""
    
    def __init__(self, config: Optional[NotebookConfig] = None):
        """
        初始化笔记生成器
        
        Args:
            config: 生成配置
        """
        self.config = config or NotebookConfig()
        self.content_manager = ContentManager()
        self.layout_engine: Optional[LayoutEngine] = None
        self.pdf_renderer: Optional[PDFRenderer] = None
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化组件"""
        # 创建布局引擎
        self.layout_engine = create_layout_engine(
            self.config.layout_type,
            self.config.page_dimensions,
            **self.config.layout_config
        )
        
        # 创建PDF渲染器
        self.pdf_renderer = create_pdf_renderer()
        self.pdf_renderer.update_config({
            'show_timestamps': self.config.show_timestamps,
            'show_page_numbers': self.config.show_page_numbers,
            'image_quality': self.config.image_quality
        })
    
    def add_image(self, image_path: str, timestamp: float, **kwargs) -> ImageContent:
        """添加图片内容"""
        return self.content_manager.add_image(image_path, timestamp, **kwargs)
    
    def add_text(self, text: str, timestamp: float, **kwargs) -> TextContent:
        """添加文字内容"""
        return self.content_manager.add_text(text, timestamp, **kwargs)
    
    def add_images_from_directory(self, 
                                 directory: str,
                                 timestamp_extractor: Optional[Callable[[str], float]] = None,
                                 **kwargs) -> List[ImageContent]:
        """从目录批量添加图片"""
        return self.content_manager.add_images_from_directory(
            directory, timestamp_extractor, **kwargs
        )
    
    def load_content_from_json(self, json_path: str):
        """从JSON文件加载内容"""
        self.content_manager.load_from_json(json_path)
    
    def save_content_to_json(self, json_path: str):
        """保存内容到JSON文件"""
        self.content_manager.save_to_json(json_path)
    
    def set_time_filter(self, start_time: float, end_time: float):
        """设置时间范围过滤"""
        self.config.filter_time_range = TimeRange(start_time, end_time)
    
    def clear_time_filter(self):
        """清除时间范围过滤"""
        self.config.filter_time_range = None
    
    def get_filtered_contents(self) -> List[TimeStampedContent]:
        """获取过滤后的内容"""
        if self.config.filter_time_range:
            return self.content_manager.filter_by_time_range(
                self.config.filter_time_range.start_time,
                self.config.filter_time_range.end_time
            )
        return self.content_manager.get_sorted_contents()
    
    def generate_notebook(self, 
                         output_path: Optional[str] = None,
                         preview_only: bool = False,
                         max_preview_pages: int = 3) -> str:
        """
        生成图文混排笔记
        
        Args:
            output_path: 输出PDF路径，None则自动生成
            preview_only: 是否只生成预览
            max_preview_pages: 预览最大页数
            
        Returns:
            生成的PDF文件路径
        """
        # 检查内容
        if len(self.content_manager) == 0:
            raise ValueError("No content to generate notebook")
        
        # 生成输出路径
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.config.filename_template.format(timestamp=timestamp)
            output_path = os.path.join(self.config.output_dir, filename)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"🚀 Starting notebook generation...")
        print(f"Output: {output_path}")
        
        # 1. 获取过滤后的内容
        contents = self.get_filtered_contents()
        print(f"📄 Processing {len(contents)} contents")
        
        # 2. 按时间分组
        groups = self.content_manager.get_content_groups(self.config.time_window)
        print(f"📚 Created {len(groups)} content groups")
        
        # 3. 生成布局
        pages = self.layout_engine.layout_groups(groups)
        print(f"📐 Generated {len(pages)} layout pages")
        
        # 4. 渲染PDF
        if preview_only:
            output_path = self.pdf_renderer.create_preview_pdf(
                pages, output_path, max_preview_pages
            )
        else:
            output_path = self.pdf_renderer.render_to_pdf(
                pages, output_path,
                title=self.config.pdf_title,
                author=self.config.pdf_author
            )
        
        print(f"✅ Notebook generated: {output_path}")
        return output_path
    
    def generate_preview(self, output_path: Optional[str] = None) -> str:
        """生成预览PDF"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.config.output_dir, f"preview_{timestamp}.pdf")
        
        return self.generate_notebook(output_path, preview_only=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取内容统计信息"""
        stats = self.content_manager.get_statistics()
        stats['config'] = self.config.to_dict()
        return stats
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # 重新初始化组件（如果需要）
        if any(key in ['layout_type', 'page_dimensions', 'layout_config'] for key in kwargs):
            self._initialize_components()
    
    def save_config(self, config_path: str):
        """保存配置到文件"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"Config saved to: {config_path}")
    
    def load_config(self, config_path: str):
        """从文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.config = NotebookConfig.from_dict(data)
        self._initialize_components()
        print(f"Config loaded from: {config_path}")
    
    def clear_all_content(self):
        """清空所有内容"""
        self.content_manager.clear()
    
    def validate_content(self) -> Dict[str, Any]:
        """验证内容有效性"""
        valid_contents, errors = self.content_manager.validate_contents()
        
        return {
            'total_contents': len(self.content_manager.contents),
            'valid_contents': len(valid_contents),
            'invalid_contents': len(errors),
            'errors': errors
        }
    
    def __str__(self) -> str:
        """返回生成器摘要"""
        stats = self.content_manager.get_statistics()
        return (f"NotebookGenerator({stats['total_contents']} contents, "
                f"layout: {self.config.layout_type.value})")


def create_notebook_generator(config_path: Optional[str] = None, **kwargs) -> NotebookGenerator:
    """
    便捷函数：创建笔记生成器
    
    Args:
        config_path: 配置文件路径
        **kwargs: 配置参数
        
    Returns:
        笔记生成器实例
    """
    if config_path and os.path.exists(config_path):
        generator = NotebookGenerator()
        generator.load_config(config_path)
    else:
        config = NotebookConfig()
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        generator = NotebookGenerator(config)
    
    return generator


# 使用示例
if __name__ == "__main__":
    # 创建笔记生成器
    generator = create_notebook_generator(
        pdf_title="AI讲座笔记",
        layout_type=LayoutType.BALANCED,
        time_window=30.0
    )
    
    # 添加示例内容
    generator.add_image("slide1.jpg", 10.0, caption="开场PPT", quality_score=0.95)
    generator.add_text("欢迎大家参加今天的AI讲座", 12.0, confidence=0.92, speaker="讲师")
    generator.add_image("slide2.jpg", 45.0, caption="AI发展历程", quality_score=0.88)
    generator.add_text("人工智能经历了多个发展阶段", 47.0, confidence=0.89, speaker="讲师")
    
    # 显示统计信息
    print("Notebook Generator Statistics:")
    print(generator)
    
    stats = generator.get_statistics()
    print(f"Time range: {stats['time_range']}")
    print(f"Layout type: {generator.config.layout_type.value}")
    
    print("\nNotebookGenerator ready")
