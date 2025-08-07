"""
图片预处理模块

提供灵活的图片预处理功能，支持多种裁剪策略：
- 交互式裁剪选择
- 智能裁剪（未来扩展）

主要用于视频帧抽取后的预处理，比如去除讲师只保留PPT内容等场景。
"""

import os
import json
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional, Union
from PIL import Image, ImageDraw
import tempfile


class CropRegion:
    """裁剪区域定义"""
    
    def __init__(self, 
                 left: Union[int, float], 
                 top: Union[int, float], 
                 right: Union[int, float], 
                 bottom: Union[int, float],
                 is_relative: bool = True):
        """
        定义裁剪区域
        
        Args:
            left, top, right, bottom: 裁剪区域坐标
            is_relative: 是否使用相对坐标(0-1)，False表示使用绝对像素坐标
        """
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.is_relative = is_relative
    
    def to_absolute(self, image_width: int, image_height: int) -> Tuple[int, int, int, int]:
        """转换为绝对坐标"""
        if self.is_relative:
            left = int(self.left * image_width)
            top = int(self.top * image_height)
            right = int(self.right * image_width)
            bottom = int(self.bottom * image_height)
        else:
            left, top, right, bottom = int(self.left), int(self.top), int(self.right), int(self.bottom)
        
        # 确保坐标在有效范围内
        left = max(0, min(left, image_width))
        top = max(0, min(top, image_height))
        right = max(left, min(right, image_width))
        bottom = max(top, min(bottom, image_height))
        
        return left, top, right, bottom
    
    def __str__(self):
        coord_type = "relative" if self.is_relative else "absolute"
        return f"CropRegion({self.left}, {self.top}, {self.right}, {self.bottom}) [{coord_type}]"


class ImagePreprocessor(ABC):
    """图片预处理器基类"""
    
    @abstractmethod
    def process_image(self, image_path: str, output_path: str) -> str:
        """
        处理单张图片
        
        Args:
            image_path: 输入图片路径
            output_path: 输出图片路径
            
        Returns:
            处理后的图片路径
        """
        pass
    
    def process_images(self, image_paths: List[str], output_dir: str) -> List[str]:
        """
        批量处理图片
        
        Args:
            image_paths: 输入图片路径列表
            output_dir: 输出目录
            
        Returns:
            处理后的图片路径列表
        """
        os.makedirs(output_dir, exist_ok=True)
        processed_paths = []
        
        for i, image_path in enumerate(image_paths):
            filename = f"processed_{i+1:06d}.jpg"
            output_path = os.path.join(output_dir, filename)
            
            try:
                processed_path = self.process_image(image_path, output_path)
                processed_paths.append(processed_path)
            except Exception as e:
                print(f"Warning: Failed to process {image_path}: {e}")
                continue
        
        print(f"Processed {len(processed_paths)}/{len(image_paths)} images")
        return processed_paths

class InteractiveCropper(ImagePreprocessor):
    """交互式裁剪器 - 通过预览图片让用户选择裁剪区域"""

    def __init__(self, quality: int = 95, preview_size: Tuple[int, int] = (800, 600)):
        """
        初始化交互式裁剪器

        Args:
            quality: 输出图片质量
            preview_size: 预览图片大小
        """
        self.quality = quality
        self.preview_size = preview_size
        self.crop_region = None

    def _create_preview_with_grid(self, image_path: str, preview_path: str):
        """创建带网格的预览图片"""
        with Image.open(image_path) as img:
            # 调整预览大小
            img.thumbnail(self.preview_size, Image.Resampling.LANCZOS)

            # 创建网格
            draw = ImageDraw.Draw(img)
            width, height = img.size

            # 绘制网格线
            grid_color = (255, 0, 0, 128)  # 红色半透明
            for i in range(1, 10):
                x = width * i // 10
                y = height * i // 10
                draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
                draw.line([(0, y), (width, y)], fill=grid_color, width=1)

            # 保存预览图片
            img.save(preview_path, "JPEG", quality=90)
            return img.size

    def _get_crop_region_from_user(self, image_size: Tuple[int, int]) -> CropRegion:
        """通过命令行交互获取裁剪区域"""
        print(f"\n📐 图片尺寸: {image_size[0]} x {image_size[1]}")
        print("请输入裁剪区域坐标 (使用相对坐标 0.0-1.0):")
        print("例如: 0.1 0.1 0.9 0.9 表示去除边缘10%的区域")

        while True:
            try:
                coords_input = input("请输入 left top right bottom (用空格分隔): ").strip()
                coords = [float(x) for x in coords_input.split()]

                if len(coords) != 4:
                    print("❌ 请输入4个坐标值")
                    continue

                left, top, right, bottom = coords

                # 验证坐标范围
                if not all(0 <= x <= 1 for x in coords):
                    print("❌ 坐标值必须在0-1之间")
                    continue

                if left >= right or top >= bottom:
                    print("❌ 左上角坐标必须小于右下角坐标")
                    continue

                return CropRegion(left, top, right, bottom, is_relative=True)

            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n用户取消操作")
                return CropRegion(0, 0, 1, 1, is_relative=True)  # 返回全图

    def setup_crop_region(self, sample_image_path: str) -> CropRegion:
        """
        设置裁剪区域（使用样本图片）

        Args:
            sample_image_path: 样本图片路径

        Returns:
            裁剪区域
        """
        print(f"🖼️  使用样本图片设置裁剪区域: {sample_image_path}")

        # 创建预览图片
        preview_path = tempfile.mktemp(suffix=".jpg")
        try:
            image_size = self._create_preview_with_grid(sample_image_path, preview_path)
            print(f"📁 预览图片已保存到: {preview_path}")
            print("💡 请打开预览图片查看网格，然后输入裁剪坐标")

            # 获取用户输入的裁剪区域
            self.crop_region = self._get_crop_region_from_user(image_size)
            print(f"✅ 裁剪区域设置完成: {self.crop_region}")

            return self.crop_region

        finally:
            # 清理预览文件
            if os.path.exists(preview_path):
                os.unlink(preview_path)

    def process_image(self, image_path: str, output_path: str) -> str:
        """裁剪图片"""
        if self.crop_region is None:
            raise ValueError("Crop region not set. Call setup_crop_region() first.")

        with Image.open(image_path) as img:
            left, top, right, bottom = self.crop_region.to_absolute(img.width, img.height)
            cropped_img = img.crop((left, top, right, bottom))
            cropped_img.save(output_path, "JPEG", quality=self.quality)

        return output_path