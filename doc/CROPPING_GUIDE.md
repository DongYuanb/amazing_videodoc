# 视频帧裁剪功能使用指南

## 概述

视频帧裁剪功能允许你在抽取视频帧后、进行向量化之前对图片进行预处理。这对于以下场景特别有用：

- **讲课视频**: 只保留PPT内容，去除讲师
- **会议录像**: 只保留屏幕共享内容
- **演示视频**: 裁剪掉无关区域，专注于核心内容
- **PDF制作**: 为后续制作PDF笔记准备统一格式的图片

## 支持的裁剪方式

### 1. 预设模板裁剪 (推荐)

使用预定义的模板，适合常见场景：

```python
from image_preprocessor import create_preprocessor, TemplateCropper

# 查看可用模板
for name, desc in TemplateCropper.list_templates().items():
    print(f"{name}: {desc}")

# 创建模板裁剪器
preprocessor = create_preprocessor('template', template_name='lecture_ppt_only')
```

**可用模板:**
- `lecture_ppt_only`: 讲课场景，只保留PPT区域
- `ppt_16_9_center`: 16:9 PPT居中显示
- `ppt_16_9_left`: PPT在左侧，去除右侧讲师
- `ppt_16_9_right`: PPT在右侧，去除左侧讲师
- `meeting_screen`: 会议屏幕共享区域
- `full_screen`: 全屏，不裁剪

### 2. 手动指定坐标

精确控制裁剪区域：

```python
from image_preprocessor import CropRegion, ManualCropper

# 定义裁剪区域 (相对坐标 0-1)
crop_region = CropRegion(
    left=0.1,    # 左边界：10%
    top=0.1,     # 上边界：10%  
    right=0.9,   # 右边界：90%
    bottom=0.9,  # 下边界：90%
    is_relative=True
)

preprocessor = ManualCropper(crop_region)
```

### 3. 配置文件方式

使用JSON配置文件：

```json
{
  "crop_region": {
    "left": 0.05,
    "top": 0.1,
    "right": 0.75,
    "bottom": 0.9,
    "is_relative": true
  },
  "quality": 95
}
```

```python
from image_preprocessor import ConfigurableCropper

preprocessor = ConfigurableCropper("crop_config.json")
```

### 4. 交互式裁剪

通过预览图片选择裁剪区域：

```python
from image_preprocessor import InteractiveCropper

preprocessor = InteractiveCropper()
# 使用样本图片设置裁剪区域
crop_region = preprocessor.setup_crop_region("sample_frame.jpg")
```

## 集成到视频去重系统

```python
from video_frame_deduplicator import VideoFrameDeduplicator
from image_preprocessor import create_preprocessor

# 创建裁剪器
preprocessor = create_preprocessor('template', template_name='lecture_ppt_only')

# 创建去重处理器（带裁剪功能）
deduplicator = VideoFrameDeduplicator(
    jina_api_key="your_api_key",
    similarity_threshold=0.85,
    image_preprocessor=preprocessor  # 添加预处理器
)

# 处理视频
result = deduplicator.process_video_frames(
    video_path="lecture.mp4",
    start_time=10.0,
    end_time=60.0,
    output_dir="output/cropped_frames",
    fps=0.5
)
```

## 坐标系统说明

### 相对坐标 (推荐)
- 范围: 0.0 - 1.0
- 优点: 适用于不同分辨率的视频
- 示例: `left=0.1` 表示从左边10%的位置开始

### 绝对坐标
- 范围: 像素值
- 优点: 精确控制
- 示例: `left=100` 表示从左边第100个像素开始

## 常见场景配置

### 讲师在右侧的讲课视频
```python
crop_region = CropRegion(0.0, 0.1, 0.7, 0.9, is_relative=True)
```

### 讲师在左侧的讲课视频  
```python
crop_region = CropRegion(0.3, 0.1, 1.0, 0.9, is_relative=True)
```

### 去除边缘杂乱内容
```python
crop_region = CropRegion(0.05, 0.05, 0.95, 0.95, is_relative=True)
```

### 会议屏幕共享
```python
crop_region = CropRegion(0.1, 0.15, 0.9, 0.85, is_relative=True)
```

## 质量设置

- `quality=95`: 高质量，文件较大
- `quality=85`: 平衡质量和大小 (推荐)
- `quality=75`: 较小文件，质量可接受

## 使用技巧

1. **先用交互式裁剪确定区域**: 对于新的视频类型，先用交互式裁剪确定最佳裁剪区域
2. **保存配置**: 将确定的裁剪区域保存为配置文件，方便重复使用
3. **批量处理**: 对于同类型的视频，使用相同的模板或配置
4. **质量平衡**: 根据后续用途选择合适的质量设置

## 故障排除

### 裁剪区域为空
- 检查坐标是否正确: `left < right`, `top < bottom`
- 确保坐标在有效范围内: 相对坐标0-1，绝对坐标不超过图片尺寸

### 图片质量下降
- 提高quality参数值
- 检查裁剪区域是否过小

### 处理速度慢
- 降低quality参数值
- 使用相对坐标而非绝对坐标
- 减少抽帧频率

## 示例代码

完整的示例代码请参考:
- `example_with_cropping.py`: 各种裁剪方式的完整示例
- `crop_config_example.json`: 配置文件示例
