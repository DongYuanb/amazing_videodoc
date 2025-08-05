"""
图文混排笔记生成系统

一个完整的图文混排PDF笔记生成解决方案，支持：
- 带时间戳的图片和文字内容管理
- 多种布局模式（图片主导、文字主导、平衡布局）
- 高质量PDF生成
- 与视频处理系统的无缝集成

主要组件：
- NotebookGenerator: 主控制器
- ContentManager: 内容管理器
- LayoutEngine: 布局引擎
- PDFRenderer: PDF渲染器
"""

# 导入主要类和函数，方便外部使用
from .notebook_generator import NotebookGenerator, NotebookConfig, create_notebook_generator
from .content_manager import ContentManager
from .layout_engine import LayoutType, LayoutEngine, create_layout_engine
from .pdf_renderer import PDFRenderer, create_pdf_renderer
from .notebook_content import (
    TimeStampedContent, ImageContent, TextContent, ContentGroup, TimeRange,
    create_image_content, create_text_content, group_content_by_time
)

# 版本信息
__version__ = "1.0.0"
__author__ = "Video Frame Deduplicator Team"

# 导出的公共接口
__all__ = [
    # 主要类
    'NotebookGenerator',
    'NotebookConfig', 
    'ContentManager',
    'LayoutEngine',
    'PDFRenderer',
    
    # 内容类
    'TimeStampedContent',
    'ImageContent', 
    'TextContent',
    'ContentGroup',
    'TimeRange',
    
    # 枚举
    'LayoutType',
    
    # 工厂函数
    'create_notebook_generator',
    'create_layout_engine',
    'create_pdf_renderer',
    'create_image_content',
    'create_text_content',
    'group_content_by_time',
]
