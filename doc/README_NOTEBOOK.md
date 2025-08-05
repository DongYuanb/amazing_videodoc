# 图文混排笔记生成系统

## 🎉 成功解决模块导入问题！

你的图文混排笔记生成系统现在已经完全可以正常运行了！

## 📁 项目结构

```
amazing_videodoc/
├── notebook/                    # 笔记生成模块
│   ├── __init__.py             # 模块初始化文件
│   ├── notebook_content.py     # 内容数据结构
│   ├── content_manager.py      # 内容管理器
│   ├── layout_engine.py        # 布局引擎
│   ├── pdf_renderer.py         # PDF渲染器
│   ├── notebook_generator.py   # 主控制器
│   ├── example_notebook_generation.py  # 完整示例
│   ├── notebook_config_example.json    # 配置示例
│   └── NOTEBOOK_GUIDE.md       # 详细使用指南
├── run_notebook_example.py     # 启动脚本（推荐使用）
├── test_notebook_simple.py     # 简单测试脚本
└── output/notebooks/           # 生成的PDF文件
```

## 🚀 快速开始

### 1. 运行测试
```bash
python3 test_notebook_simple.py
```

### 2. 运行完整示例
```bash
python3 run_notebook_example.py
```

### 3. 基本使用
```python
from notebook import create_notebook_generator, LayoutType

# 创建生成器
generator = create_notebook_generator(
    pdf_title="我的笔记",
    layout_type=LayoutType.BALANCED
)

# 添加内容
generator.add_image("image.jpg", 10.0, caption="图片说明")
generator.add_text("这是文字内容", 12.0, speaker="讲师")

# 生成PDF
notebook_path = generator.generate_notebook()
```

## 🎯 主要功能

### ✅ 已实现的功能
- [x] 带时间戳的内容管理
- [x] 多种布局模式（图片主导、文字主导、平衡布局）
- [x] 高质量PDF生成
- [x] 时间范围过滤
- [x] 配置文件支持
- [x] 批量图片导入
- [x] 内容验证和统计
- [x] 模块化设计

### 🎨 布局模式
1. **图片主导** (`LayoutType.IMAGE_DOMINANT`)
   - 图片占据主要空间
   - 适合PPT截图场景

2. **文字主导** (`LayoutType.TEXT_DOMINANT`)
   - 文字为主体内容
   - 适合讲座笔记场景

3. **平衡布局** (`LayoutType.BALANCED`)
   - 图文并重显示
   - 适合大多数场景

## 🔗 与视频去重系统集成

```python
# 1. 处理视频帧
from video_frame_deduplicator import VideoFrameDeduplicator
deduplicator = VideoFrameDeduplicator(api_key="your_key")
result = deduplicator.process_video_frames(...)

# 2. 创建笔记生成器
from notebook import create_notebook_generator
generator = create_notebook_generator()

# 3. 添加去重后的帧
for frame_path in result['saved_paths']:
    timestamp = extract_timestamp(frame_path)  # 自定义时间戳提取
    generator.add_image(frame_path, timestamp, source="video_deduplicator")

# 4. 生成笔记
generator.generate_notebook()
```

## 📊 生成的文件

运行示例后，你会在 `output/notebooks/` 目录下看到：

- `notebook_*.pdf` - 完整笔记
- `preview_*.pdf` - 预览版本（前3页）
- `test_*.pdf` - 不同布局模式的测试文件

## ⚙️ 配置选项

### 时间窗口设置
```python
generator.update_config(time_window=30.0)  # 30秒时间窗口
```

### 布局参数
```python
generator.layout_engine.update_config({
    'image_width_ratio': 0.8,    # 图片宽度占比
    'image_height_max': 400,     # 图片最大高度
    'text_font_size': 12,        # 文字字体大小
})
```

### PDF设置
```python
generator.update_config(
    show_timestamps=True,        # 显示时间戳
    show_page_numbers=True,      # 显示页码
    image_quality=85            # 图片质量
)
```

## 🛠️ 解决方案总结

### 问题：模块导入错误
```
ModuleNotFoundError: No module named 'notebook'
```

### 解决方案：
1. **创建了 `__init__.py` 文件**，让Python识别notebook为一个包
2. **修复了所有相对导入**，使用 `.` 前缀
3. **重新设计了数据类**，避免dataclass继承问题
4. **创建了启动脚本**，在项目根目录运行

### 关键文件：
- `notebook/__init__.py` - 包初始化和公共接口
- `run_notebook_example.py` - 推荐的启动方式
- `test_notebook_simple.py` - 快速测试脚本

## 💡 使用建议

1. **开发时**：使用 `test_notebook_simple.py` 快速测试
2. **演示时**：使用 `run_notebook_example.py` 展示完整功能
3. **集成时**：直接导入 `from notebook import ...`
4. **配置时**：参考 `notebook_config_example.json`

## 📚 更多信息

- 详细使用指南：`notebook/NOTEBOOK_GUIDE.md`
- 配置示例：`notebook/notebook_config_example.json`
- 完整示例：`notebook/example_notebook_generation.py`

现在你可以：
✅ 正常导入和使用notebook模块
✅ 生成高质量的图文混排PDF
✅ 与现有视频处理系统集成
✅ 自定义布局和配置

🎉 **恭喜！你的图文混排笔记生成系统已经完全可用了！**
