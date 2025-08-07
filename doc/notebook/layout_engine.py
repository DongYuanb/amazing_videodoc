"""
布局引擎

提供多种图文混排的布局策略，支持不同的排版需求：
- 图片主导布局：适合PPT截图等场景
- 文字主导布局：适合讲座笔记等场景  
- 平衡布局：图文并重
- 时间线布局：按时间顺序展示
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
from .notebook_content import ContentGroup, ImageContent, TextContent, TimeStampedContent


class LayoutType(Enum):
    """布局类型枚举"""
    IMAGE_DOMINANT = "image_dominant"      # 图片主导
    TEXT_DOMINANT = "text_dominant"        # 文字主导
    BALANCED = "balanced"                  # 平衡布局
    TIMELINE = "timeline"                  # 时间线布局
    GRID = "grid"                         # 网格布局


@dataclass
class PageDimensions:
    """页面尺寸配置"""
    width: float = 595.0    # A4宽度（点）
    height: float = 842.0   # A4高度（点）
    margin_top: float = 50.0
    margin_bottom: float = 50.0
    margin_left: float = 50.0
    margin_right: float = 50.0
    
    @property
    def content_width(self) -> float:
        """内容区域宽度"""
        return self.width - self.margin_left - self.margin_right
    
    @property
    def content_height(self) -> float:
        """内容区域高度"""
        return self.height - self.margin_top - self.margin_bottom


@dataclass
class LayoutElement:
    """布局元素 - 表示页面上的一个元素"""
    content: TimeStampedContent
    x: float  # X坐标
    y: float  # Y坐标
    width: float  # 宽度
    height: float  # 高度
    element_type: str  # 元素类型（image/text）
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """获取边界 (x, y, x+width, y+height)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class LayoutPage:
    """布局页面 - 表示PDF中的一页"""
    page_number: int
    elements: List[LayoutElement]
    dimensions: PageDimensions
    title: Optional[str] = None
    
    @property
    def has_content(self) -> bool:
        """是否有内容"""
        return len(self.elements) > 0
    
    def add_element(self, element: LayoutElement):
        """添加元素"""
        self.elements.append(element)
    
    def get_used_height(self) -> float:
        """获取已使用的高度"""
        if not self.elements:
            return 0.0
        return max(elem.y + elem.height for elem in self.elements)


class LayoutEngine(ABC):
    """布局引擎基类"""
    
    def __init__(self, page_dimensions: Optional[PageDimensions] = None):
        self.page_dimensions = page_dimensions or PageDimensions()
        self.layout_config = self._get_default_config()
    
    @abstractmethod
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        pass
    
    @abstractmethod
    def layout_group(self, group: ContentGroup, page_number: int = 1) -> List[LayoutPage]:
        """
        为内容组生成布局
        
        Args:
            group: 内容组
            page_number: 起始页码
            
        Returns:
            布局页面列表
        """
        pass
    
    def layout_groups(self, groups: List[ContentGroup]) -> List[LayoutPage]:
        """为多个内容组生成布局"""
        all_pages = []
        current_page_number = 1
        
        for group in groups:
            pages = self.layout_group(group, current_page_number)
            all_pages.extend(pages)
            current_page_number += len(pages)
        
        return all_pages
    
    def update_config(self, config: Dict[str, Any]):
        """更新布局配置"""
        self.layout_config.update(config)


class ImageDominantLayout(LayoutEngine):
    """图片主导布局 - 图片占据主要空间，文字作为说明"""
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'image_width_ratio': 0.8,      # 图片宽度占比
            'image_height_max': 400,       # 图片最大高度
            'text_font_size': 12,          # 文字字体大小
            'spacing': 20,                 # 元素间距
            'caption_height': 30,          # 图片说明高度
        }
    
    def layout_group(self, group: ContentGroup, page_number: int = 1) -> List[LayoutPage]:
        """图片主导布局"""
        pages = []
        current_page = LayoutPage(page_number, [], self.page_dimensions)
        current_y = self.page_dimensions.margin_top
        
        # 按时间戳排序内容
        all_content = group.get_all_content()
        
        for content in all_content:
            if isinstance(content, ImageContent):
                element_height = self._calculate_image_height(content)
                
                # 检查是否需要新页面
                if (current_y + element_height > 
                    self.page_dimensions.height - self.page_dimensions.margin_bottom):
                    pages.append(current_page)
                    page_number += 1
                    current_page = LayoutPage(page_number, [], self.page_dimensions)
                    current_y = self.page_dimensions.margin_top
                
                # 添加图片元素
                image_element = self._create_image_element(content, current_y)
                current_page.add_element(image_element)
                current_y += element_height + self.layout_config['spacing']
                
            elif isinstance(content, TextContent):
                # 文字作为注释，紧跟在图片后面或独立显示
                text_height = self._calculate_text_height(content)
                
                if (current_y + text_height > 
                    self.page_dimensions.height - self.page_dimensions.margin_bottom):
                    pages.append(current_page)
                    page_number += 1
                    current_page = LayoutPage(page_number, [], self.page_dimensions)
                    current_y = self.page_dimensions.margin_top
                
                text_element = self._create_text_element(content, current_y)
                current_page.add_element(text_element)
                current_y += text_height + self.layout_config['spacing']
        
        if current_page.has_content:
            pages.append(current_page)
        
        return pages
    
    def _calculate_image_height(self, image: ImageContent) -> float:
        """计算图片在页面上的高度"""
        if not image.width or not image.height:
            return self.layout_config['image_height_max']
        
        # 根据宽度比例计算高度
        target_width = self.page_dimensions.content_width * self.layout_config['image_width_ratio']
        scale_factor = target_width / image.width
        scaled_height = image.height * scale_factor
        
        # 限制最大高度
        return min(scaled_height, self.layout_config['image_height_max'])
    
    def _calculate_text_height(self, text: TextContent) -> float:
        """计算文字在页面上的高度"""
        # 简单估算：每行约20像素，每行约80字符
        chars_per_line = 80
        line_height = 20
        lines = max(1, len(text.text) // chars_per_line + 1)
        return lines * line_height
    
    def _create_image_element(self, image: ImageContent, y: float) -> LayoutElement:
        """创建图片元素"""
        width = self.page_dimensions.content_width * self.layout_config['image_width_ratio']
        height = self._calculate_image_height(image)
        x = self.page_dimensions.margin_left + (self.page_dimensions.content_width - width) / 2
        
        return LayoutElement(
            content=image,
            x=x, y=y,
            width=width, height=height,
            element_type="image"
        )
    
    def _create_text_element(self, text: TextContent, y: float) -> LayoutElement:
        """创建文字元素"""
        width = self.page_dimensions.content_width
        height = self._calculate_text_height(text)
        x = self.page_dimensions.margin_left
        
        return LayoutElement(
            content=text,
            x=x, y=y,
            width=width, height=height,
            element_type="text"
        )


class TextDominantLayout(LayoutEngine):
    """文字主导布局 - 文字为主体，图片作为插图"""
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'text_font_size': 12,
            'text_line_height': 18,
            'image_width_ratio': 0.6,
            'image_height_max': 300,
            'spacing': 15,
            'paragraph_spacing': 25,
        }
    
    def layout_group(self, group: ContentGroup, page_number: int = 1) -> List[LayoutPage]:
        """文字主导布局"""
        pages = []
        current_page = LayoutPage(page_number, [], self.page_dimensions)
        current_y = self.page_dimensions.margin_top
        
        all_content = group.get_all_content()
        
        for content in all_content:
            if isinstance(content, TextContent):
                text_height = self._calculate_text_height(content)
                
                if (current_y + text_height > 
                    self.page_dimensions.height - self.page_dimensions.margin_bottom):
                    pages.append(current_page)
                    page_number += 1
                    current_page = LayoutPage(page_number, [], self.page_dimensions)
                    current_y = self.page_dimensions.margin_top
                
                text_element = self._create_text_element(content, current_y)
                current_page.add_element(text_element)
                current_y += text_height + self.layout_config['paragraph_spacing']
                
            elif isinstance(content, ImageContent):
                image_height = self._calculate_image_height(content)
                
                if (current_y + image_height > 
                    self.page_dimensions.height - self.page_dimensions.margin_bottom):
                    pages.append(current_page)
                    page_number += 1
                    current_page = LayoutPage(page_number, [], self.page_dimensions)
                    current_y = self.page_dimensions.margin_top
                
                image_element = self._create_image_element(content, current_y)
                current_page.add_element(image_element)
                current_y += image_height + self.layout_config['spacing']
        
        if current_page.has_content:
            pages.append(current_page)
        
        return pages
    
    def _calculate_text_height(self, text: TextContent) -> float:
        """计算文字高度"""
        chars_per_line = 90  # 文字主导时每行字符更多
        lines = max(1, len(text.text) // chars_per_line + 1)
        return lines * self.layout_config['text_line_height']
    
    def _calculate_image_height(self, image: ImageContent) -> float:
        """计算图片高度"""
        if not image.width or not image.height:
            return self.layout_config['image_height_max']
        
        target_width = self.page_dimensions.content_width * self.layout_config['image_width_ratio']
        scale_factor = target_width / image.width
        scaled_height = image.height * scale_factor
        
        return min(scaled_height, self.layout_config['image_height_max'])
    
    def _create_text_element(self, text: TextContent, y: float) -> LayoutElement:
        """创建文字元素"""
        return LayoutElement(
            content=text,
            x=self.page_dimensions.margin_left,
            y=y,
            width=self.page_dimensions.content_width,
            height=self._calculate_text_height(text),
            element_type="text"
        )
    
    def _create_image_element(self, image: ImageContent, y: float) -> LayoutElement:
        """创建图片元素"""
        width = self.page_dimensions.content_width * self.layout_config['image_width_ratio']
        height = self._calculate_image_height(image)
        x = self.page_dimensions.margin_left + (self.page_dimensions.content_width - width) / 2
        
        return LayoutElement(
            content=image,
            x=x, y=y,
            width=width, height=height,
            element_type="image"
        )


class BalancedLayout(LayoutEngine):
    """平衡布局 - 图片和文字平分空间"""

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'image_width_ratio': 0.7,
            'image_height_max': 350,
            'text_font_size': 11,
            'text_line_height': 16,
            'spacing': 18,
            'section_spacing': 30,
        }

    def layout_group(self, group: ContentGroup, page_number: int = 1) -> List[LayoutPage]:
        """平衡布局 - 图文并重"""
        pages = []
        current_page = LayoutPage(page_number, [], self.page_dimensions)
        current_y = self.page_dimensions.margin_top

        all_content = group.get_all_content()

        # 将内容按图文对进行分组
        content_pairs = self._group_content_pairs(all_content)

        for pair in content_pairs:
            pair_height = self._calculate_pair_height(pair)

            if (current_y + pair_height >
                self.page_dimensions.height - self.page_dimensions.margin_bottom):
                pages.append(current_page)
                page_number += 1
                current_page = LayoutPage(page_number, [], self.page_dimensions)
                current_y = self.page_dimensions.margin_top

            # 布局这一对内容
            current_y = self._layout_content_pair(pair, current_page, current_y)
            current_y += self.layout_config['section_spacing']

        if current_page.has_content:
            pages.append(current_page)

        return pages

    def _group_content_pairs(self, contents: List[TimeStampedContent]) -> List[List[TimeStampedContent]]:
        """将内容分组为图文对"""
        pairs = []
        current_pair = []

        for content in contents:
            current_pair.append(content)

            # 如果当前对已经有图片和文字，或者达到最大长度，开始新对
            if (len(current_pair) >= 2 and
                any(isinstance(c, ImageContent) for c in current_pair) and
                any(isinstance(c, TextContent) for c in current_pair)):
                pairs.append(current_pair)
                current_pair = []
            elif len(current_pair) >= 3:  # 最多3个元素一组
                pairs.append(current_pair)
                current_pair = []

        if current_pair:
            pairs.append(current_pair)

        return pairs

    def _calculate_pair_height(self, pair: List[TimeStampedContent]) -> float:
        """计算内容对的高度"""
        total_height = 0
        for content in pair:
            if isinstance(content, ImageContent):
                total_height += self._calculate_image_height(content)
            elif isinstance(content, TextContent):
                total_height += self._calculate_text_height(content)
            total_height += self.layout_config['spacing']
        return total_height

    def _layout_content_pair(self, pair: List[TimeStampedContent],
                           page: LayoutPage, start_y: float) -> float:
        """布局一对内容"""
        current_y = start_y

        for content in pair:
            if isinstance(content, ImageContent):
                element = self._create_image_element(content, current_y)
                page.add_element(element)
                current_y += element.height + self.layout_config['spacing']
            elif isinstance(content, TextContent):
                element = self._create_text_element(content, current_y)
                page.add_element(element)
                current_y += element.height + self.layout_config['spacing']

        return current_y

    def _calculate_image_height(self, image: ImageContent) -> float:
        """计算图片高度"""
        if not image.width or not image.height:
            return self.layout_config['image_height_max']

        target_width = self.page_dimensions.content_width * self.layout_config['image_width_ratio']
        scale_factor = target_width / image.width
        scaled_height = image.height * scale_factor

        return min(scaled_height, self.layout_config['image_height_max'])

    def _calculate_text_height(self, text: TextContent) -> float:
        """计算文字高度"""
        chars_per_line = 85
        lines = max(1, len(text.text) // chars_per_line + 1)
        return lines * self.layout_config['text_line_height']

    def _create_image_element(self, image: ImageContent, y: float) -> LayoutElement:
        """创建图片元素"""
        width = self.page_dimensions.content_width * self.layout_config['image_width_ratio']
        height = self._calculate_image_height(image)
        x = self.page_dimensions.margin_left + (self.page_dimensions.content_width - width) / 2

        return LayoutElement(
            content=image, x=x, y=y, width=width, height=height, element_type="image"
        )

    def _create_text_element(self, text: TextContent, y: float) -> LayoutElement:
        """创建文字元素"""
        return LayoutElement(
            content=text,
            x=self.page_dimensions.margin_left, y=y,
            width=self.page_dimensions.content_width,
            height=self._calculate_text_height(text),
            element_type="text"
        )


def create_layout_engine(layout_type: LayoutType,
                        page_dimensions: Optional[PageDimensions] = None,
                        **config) -> LayoutEngine:
    """
    工厂函数：创建布局引擎

    Args:
        layout_type: 布局类型
        page_dimensions: 页面尺寸
        **config: 布局配置参数

    Returns:
        布局引擎实例
    """
    if layout_type == LayoutType.IMAGE_DOMINANT:
        engine = ImageDominantLayout(page_dimensions)
    elif layout_type == LayoutType.TEXT_DOMINANT:
        engine = TextDominantLayout(page_dimensions)
    elif layout_type == LayoutType.BALANCED:
        engine = BalancedLayout(page_dimensions)
    else:
        raise ValueError(f"Unsupported layout type: {layout_type}")

    if config:
        engine.update_config(config)

    return engine


# 使用示例
if __name__ == "__main__":
    from .notebook_content import create_image_content, create_text_content, ContentGroup, TimeRange
    
    # 创建示例内容组
    group = ContentGroup(TimeRange(10.0, 60.0))
    group.add_content(create_image_content("slide1.jpg", 10.0, caption="第一张PPT"))
    group.add_content(create_text_content("欢迎大家参加讲座", 12.0))
    group.add_content(create_image_content("slide2.jpg", 30.0, caption="主题介绍"))
    group.add_content(create_text_content("今天我们讨论AI发展", 32.0))
    
    # 测试图片主导布局
    image_layout = create_layout_engine(LayoutType.IMAGE_DOMINANT)
    pages = image_layout.layout_group(group)
    
    print(f"Generated {len(pages)} pages with image-dominant layout")
    for i, page in enumerate(pages):
        print(f"  Page {page.page_number}: {len(page.elements)} elements")
    
    print("\nLayoutEngine ready")
