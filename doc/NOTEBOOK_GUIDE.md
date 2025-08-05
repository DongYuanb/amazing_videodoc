# 图文混排笔记生成系统使用指南

## 概述

图文混排笔记生成系统是一个模块化的PDF笔记生成工具，专门设计用于将带时间戳的图片和文字内容组合成结构化的PDF文档。特别适用于：

- **讲座笔记**: 将PPT截图和语音转文字结合
- **会议记录**: 整合屏幕共享和讨论内容
- **学习资料**: 创建图文并茂的学习笔记
- **培训材料**: 生成标准化的培训文档

## 核心特性

### 🎯 智能内容管理
- 基于时间戳的内容组织
- 自动内容分组和排序
- 支持时间范围过滤
- 内容有效性验证

### 🎨 多种布局模式
- **图片主导**: 适合PPT截图场景
- **文字主导**: 适合讲座笔记场景
- **平衡布局**: 图文并重显示
- **时间线布局**: 按时间顺序展示（规划中）

### 📄 专业PDF输出
- 高质量PDF生成
- 自定义样式和格式
- 时间戳和元数据显示
- 分页和排版优化

### 🔧 模块化设计
- 与现有视频处理系统解耦
- 标准化接口便于集成
- 配置驱动的行为控制

## 快速开始

### 1. 安装依赖

```bash
pip install reportlab pillow
```

### 2. 基本使用

```python
from notebook_generator import create_notebook_generator
from layout_engine import LayoutType

# 创建生成器
generator = create_notebook_generator(
    pdf_title="我的笔记",
    layout_type=LayoutType.BALANCED,
    time_window=30.0
)

# 添加内容
generator.add_image("slide1.jpg", 10.0, caption="开场PPT")
generator.add_text("欢迎大家参加讲座", 12.0, speaker="讲师")

# 生成PDF
notebook_path = generator.generate_notebook()
print(f"笔记已生成: {notebook_path}")
```

### 3. 与视频去重系统集成

```python
# 从视频去重系统获取结果
from video_frame_deduplicator import VideoFrameDeduplicator

# 处理视频帧
deduplicator = VideoFrameDeduplicator(api_key="your_key")
result = deduplicator.process_video_frames(
    video_path="lecture.mp4",
    start_time=10.0,
    end_time=300.0,
    output_dir="frames"
)

# 创建笔记生成器
generator = create_notebook_generator()

# 添加去重后的帧
for frame_path in result['saved_paths']:
    # 从文件名提取时间戳（需要根据实际命名规则调整）
    timestamp = extract_timestamp_from_filename(frame_path)
    generator.add_image(frame_path, timestamp, source="video_deduplicator")

# 生成笔记
generator.generate_notebook()
```

## 详细功能说明

### 内容管理

#### 添加图片内容
```python
generator.add_image(
    image_path="slide1.jpg",
    timestamp=10.0,
    caption="图片说明",
    quality_score=0.95,  # 质量评分
    source="video_frame"  # 来源标识
)
```

#### 添加文字内容
```python
generator.add_text(
    text="这是讲座内容",
    timestamp=12.0,
    confidence=0.92,  # 识别置信度
    speaker="讲师",   # 说话人
    source="speech_to_text"
)
```

#### 批量添加图片
```python
def extract_timestamp(filename):
    # 从文件名提取时间戳的自定义函数
    return float(filename.split('_')[1].split('.')[0])

generator.add_images_from_directory(
    directory="frames/",
    timestamp_extractor=extract_timestamp,
    source="video_processing"
)
```

### 布局配置

#### 选择布局模式
```python
from layout_engine import LayoutType

# 图片主导 - 适合PPT截图
generator.update_config(layout_type=LayoutType.IMAGE_DOMINANT)

# 文字主导 - 适合讲座笔记
generator.update_config(layout_type=LayoutType.TEXT_DOMINANT)

# 平衡布局 - 图文并重
generator.update_config(layout_type=LayoutType.BALANCED)
```

#### 自定义布局参数
```python
# 更新布局配置
generator.layout_engine.update_config({
    'image_width_ratio': 0.8,    # 图片宽度占比
    'image_height_max': 400,     # 图片最大高度
    'text_font_size': 12,        # 文字字体大小
    'spacing': 20                # 元素间距
})
```

### 时间管理

#### 设置时间过滤
```python
# 只处理指定时间范围的内容
generator.set_time_filter(start_time=30.0, end_time=120.0)

# 清除时间过滤
generator.clear_time_filter()
```

#### 调整时间窗口
```python
# 设置内容分组的时间窗口
generator.update_config(time_window=45.0)  # 45秒窗口
```

### 配置管理

#### 保存和加载配置
```python
# 保存当前配置
generator.save_config("my_config.json")

# 从配置文件创建生成器
generator = create_notebook_generator(config_path="my_config.json")
```

#### 配置文件格式
```json
{
  "time_window": 30.0,
  "layout_type": "balanced",
  "pdf_title": "我的笔记",
  "pdf_author": "自动生成",
  "show_timestamps": true,
  "show_page_numbers": true,
  "image_quality": 85,
  "output_dir": "output/notebooks",
  "filename_template": "notebook_{timestamp}.pdf"
}
```

### PDF生成选项

#### 生成预览
```python
# 生成前3页预览
preview_path = generator.generate_preview()
```

#### 自定义输出
```python
# 指定输出路径
notebook_path = generator.generate_notebook("my_notebook.pdf")

# 只生成预览
preview_path = generator.generate_notebook(
    "preview.pdf", 
    preview_only=True, 
    max_preview_pages=5
)
```

## 最佳实践

### 1. 时间戳管理
- 确保所有内容都有准确的时间戳
- 使用统一的时间基准（如视频开始时间）
- 为相关内容设置合理的时间窗口

### 2. 内容质量控制
- 为图片设置质量评分，便于后续筛选
- 为文字设置置信度，标识识别准确性
- 定期验证内容有效性

### 3. 布局选择
- **PPT截图场景**: 使用图片主导布局
- **讲座记录场景**: 使用平衡布局
- **纯文字笔记**: 使用文字主导布局

### 4. 性能优化
- 合理设置时间窗口，避免过多小组
- 压缩图片以减少PDF文件大小
- 使用预览功能验证效果后再生成完整PDF

## 集成示例

### 与视频处理系统完整集成

```python
def create_lecture_notebook(video_path, output_dir):
    """完整的讲座笔记生成流程"""
    
    # 1. 视频帧去重
    from video_frame_deduplicator import VideoFrameDeduplicator
    deduplicator = VideoFrameDeduplicator(api_key="your_key")
    frame_result = deduplicator.process_video_frames(
        video_path=video_path,
        start_time=0,
        end_time=3600,  # 1小时
        output_dir=f"{output_dir}/frames"
    )
    
    # 2. 语音转文字（示例接口）
    # speech_result = speech_to_text_system.process(video_path)
    
    # 3. 创建笔记生成器
    generator = create_notebook_generator(
        pdf_title=f"讲座笔记 - {Path(video_path).stem}",
        layout_type=LayoutType.BALANCED,
        time_window=30.0
    )
    
    # 4. 添加帧内容
    for frame_path in frame_result['saved_paths']:
        timestamp = extract_timestamp_from_path(frame_path)
        generator.add_image(frame_path, timestamp, source="video_frame")
    
    # 5. 添加文字内容（如果有）
    # for text_item in speech_result:
    #     generator.add_text(
    #         text_item['text'], 
    #         text_item['timestamp'],
    #         confidence=text_item['confidence']
    #     )
    
    # 6. 生成笔记
    notebook_path = generator.generate_notebook(
        f"{output_dir}/lecture_notebook.pdf"
    )
    
    return notebook_path
```

## 故障排除

### 常见问题

1. **PDF生成失败**
   - 检查reportlab是否正确安装
   - 确保输出目录有写入权限
   - 验证图片文件是否存在且可读

2. **图片显示异常**
   - 检查图片路径是否正确
   - 确保图片格式受支持（JPG, PNG等）
   - 验证图片文件是否损坏

3. **布局效果不理想**
   - 调整时间窗口大小
   - 尝试不同的布局模式
   - 自定义布局参数

4. **内存使用过高**
   - 减少同时处理的内容数量
   - 压缩图片尺寸
   - 使用时间过滤限制处理范围

### 调试技巧

```python
# 查看内容统计
stats = generator.get_statistics()
print(f"内容统计: {stats}")

# 验证内容有效性
validation = generator.validate_content()
print(f"验证结果: {validation}")

# 生成预览进行测试
preview_path = generator.generate_preview()
```

## 扩展开发

系统采用模块化设计，便于扩展：

- **新布局模式**: 继承`LayoutEngine`基类
- **新内容类型**: 继承`TimeStampedContent`基类
- **自定义渲染**: 扩展`PDFRenderer`类
- **新数据源**: 实现标准的内容添加接口

详细的API文档和扩展示例请参考源代码注释。
