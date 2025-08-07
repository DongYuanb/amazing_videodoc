"""
PDF渲染器

使用reportlab库将布局页面渲染为PDF文档，
支持图片、文字的精确排版和样式控制。
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import inch, cm, mm
    from reportlab.lib.colors import black, blue, gray, red
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF generation will not work.")

from .layout_engine import LayoutPage, LayoutElement, PageDimensions
from .notebook_content import ImageContent, TextContent, TimeStampedContent


class PDFStyle:
    """PDF样式配置"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            return
            
        # 获取默认样式
        self.styles = getSampleStyleSheet()
        
        # 自定义样式
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.darkblue,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            leftIndent=0,
            rightIndent=0
        ))
        
        self.styles.add(ParagraphStyle(
            name='ImageCaption',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=8,
            alignment=TA_CENTER,
            textColor=colors.gray
        ))
        
        self.styles.add(ParagraphStyle(
            name='Timestamp',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=4,
            alignment=TA_LEFT,
            textColor=colors.blue
        ))


class PDFRenderer:
    """PDF渲染器 - 将布局页面渲染为PDF"""
    
    def __init__(self, 
                 style: Optional[PDFStyle] = None,
                 page_size: Tuple[float, float] = A4):
        """
        初始化PDF渲染器
        
        Args:
            style: PDF样式配置
            page_size: 页面大小
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")
        
        self.style = style or PDFStyle()
        self.page_size = page_size
        self.render_config = {
            'show_timestamps': True,
            'show_page_numbers': True,
            'add_table_of_contents': False,
            'image_quality': 85,
            'compress_images': True,
        }
    
    def render_to_pdf(self, 
                     pages: List[LayoutPage], 
                     output_path: str,
                     title: str = "Generated Notebook",
                     author: str = "Video Frame Deduplicator",
                     **config) -> str:
        """
        渲染页面为PDF文件
        
        Args:
            pages: 布局页面列表
            output_path: 输出PDF路径
            title: 文档标题
            author: 文档作者
            **config: 渲染配置
            
        Returns:
            生成的PDF文件路径
        """
        # 更新配置
        self.render_config.update(config)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.page_size,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50,
            title=title,
            author=author,
            creator="Video Frame Deduplicator"
        )
        
        # 构建文档内容
        story = []
        
        # 添加标题页
        if title:
            story.append(Paragraph(title, self.style.styles['CustomTitle']))
            story.append(Spacer(1, 20))
            
            # 添加生成信息
            info_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
            info_text += f"Total pages: {len(pages)}<br/>"
            info_text += f"Author: {author}"
            story.append(Paragraph(info_text, self.style.styles['Normal']))
            story.append(PageBreak())
        
        # 渲染每一页
        for page in pages:
            page_content = self._render_page(page)
            story.extend(page_content)
            
            # 添加分页符（除了最后一页）
            if page != pages[-1]:
                story.append(PageBreak())
        
        # 构建PDF
        doc.build(story)
        
        print(f"PDF generated: {output_path}")
        return output_path
    
    def _render_page(self, page: LayoutPage) -> List[Any]:
        """渲染单个页面"""
        content = []
        
        # 按Y坐标排序元素（从上到下）
        sorted_elements = sorted(page.elements, key=lambda e: e.y)
        
        for element in sorted_elements:
            if element.element_type == "image":
                image_content = self._render_image_element(element)
                content.extend(image_content)
            elif element.element_type == "text":
                text_content = self._render_text_element(element)
                content.extend(text_content)
            
            # 添加元素间距
            content.append(Spacer(1, 10))
        
        return content
    
    def _render_image_element(self, element: LayoutElement) -> List[Any]:
        """渲染图片元素"""
        content = []
        image_content = element.content
        
        if not isinstance(image_content, ImageContent):
            return content
        
        # 添加时间戳
        if self.render_config['show_timestamps']:
            timestamp_text = f"[{image_content.timestamp:.1f}s]"
            content.append(Paragraph(timestamp_text, self.style.styles['Timestamp']))
        
        # 添加图片
        try:
            if os.path.exists(image_content.image_path):
                # 计算图片尺寸
                img_width = element.width
                img_height = element.height
                
                # 创建图片对象
                img = RLImage(
                    image_content.image_path,
                    width=img_width,
                    height=img_height
                )
                content.append(img)
                
                # 添加图片说明
                if image_content.caption:
                    caption_text = image_content.caption
                    if image_content.quality_score:
                        caption_text += f" (Quality: {image_content.quality_score:.2f})"
                    content.append(Paragraph(caption_text, self.style.styles['ImageCaption']))
            else:
                # 图片文件不存在时的占位符
                placeholder_text = f"[Image not found: {Path(image_content.image_path).name}]"
                content.append(Paragraph(placeholder_text, self.style.styles['Normal']))
                
        except Exception as e:
            error_text = f"[Error loading image: {e}]"
            content.append(Paragraph(error_text, self.style.styles['Normal']))
        
        return content
    
    def _render_text_element(self, element: LayoutElement) -> List[Any]:
        """渲染文字元素"""
        content = []
        text_content = element.content
        
        if not isinstance(text_content, TextContent):
            return content
        
        # 添加时间戳
        if self.render_config['show_timestamps']:
            timestamp_text = f"[{text_content.timestamp:.1f}s]"
            if text_content.speaker:
                timestamp_text += f" {text_content.speaker}:"
            content.append(Paragraph(timestamp_text, self.style.styles['Timestamp']))
        
        # 处理文字内容
        text = text_content.text
        
        # 转义HTML特殊字符
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 添加置信度信息（如果有）
        if text_content.confidence and text_content.confidence < 0.9:
            text += f" <i>(Confidence: {text_content.confidence:.2f})</i>"
        
        # 创建段落
        paragraph = Paragraph(text, self.style.styles['CustomBody'])
        content.append(paragraph)
        
        return content
    
    def update_config(self, config: Dict[str, Any]):
        """更新渲染配置"""
        self.render_config.update(config)
    
    def create_preview_pdf(self, 
                          pages: List[LayoutPage], 
                          output_path: str,
                          max_pages: int = 3) -> str:
        """
        创建预览PDF（只包含前几页）
        
        Args:
            pages: 布局页面列表
            output_path: 输出路径
            max_pages: 最大页数
            
        Returns:
            预览PDF路径
        """
        preview_pages = pages[:max_pages]
        return self.render_to_pdf(
            preview_pages, 
            output_path,
            title="Preview - Generated Notebook",
            show_timestamps=True,
            show_page_numbers=True
        )


def create_pdf_renderer(**config) -> PDFRenderer:
    """便捷函数：创建PDF渲染器"""
    return PDFRenderer(**config)


# 使用示例
if __name__ == "__main__":
    if REPORTLAB_AVAILABLE:
        from .layout_engine import create_layout_engine, LayoutType
        from .notebook_content import create_image_content, create_text_content, ContentGroup, TimeRange
        
        # 创建示例内容
        group = ContentGroup(TimeRange(10.0, 60.0))
        group.add_content(create_image_content("slide1.jpg", 10.0, caption="开场PPT"))
        group.add_content(create_text_content("欢迎大家参加今天的讲座", 12.0, confidence=0.95))
        group.add_content(create_image_content("slide2.jpg", 30.0, caption="主题介绍"))
        group.add_content(create_text_content("今天我们要讨论人工智能的发展", 32.0, confidence=0.88))
        
        # 创建布局
        layout_engine = create_layout_engine(LayoutType.BALANCED)
        pages = layout_engine.layout_group(group)
        
        # 创建PDF渲染器
        renderer = create_pdf_renderer()
        
        print(f"Generated {len(pages)} pages for PDF rendering")
        print("PDFRenderer ready")
    else:
        print("reportlab not available - install with: pip install reportlab")
