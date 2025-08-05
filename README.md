# 视频音视频分流工具

基于ffmpeg的视频处理工具，支持本地文件和网络链接，实现音视频流分离。

## 功能特性

- 支持本地视频文件处理
- 支持网络视频链接下载和处理
- 自动音视频流分离
- 紧凑高效的代码设计
- 统一的处理接口

## 依赖要求

- Python 3.6+
- ffmpeg (需要在系统PATH中或指定路径)

## 安装ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# 下载ffmpeg并添加到PATH
```

## 使用方法

### 基本用法

```python
from video_process import split_video

# 处理本地文件
audio_file, video_file = split_video("input.mp4", "output/")

# 处理网络链接
audio_file, video_file = split_video("https://example.com/video.mp4", "output/")
```

### 高级用法

```python
from video_process import VideoProcessor

# 创建处理器实例
processor = VideoProcessor(ffmpeg_path="/path/to/ffmpeg")

# 处理文件
audio, video = processor.process_file("video.mp4", "output/")

# 处理URL
audio, video = processor.process_url("https://example.com/video.mp4", "output/")

# 统一接口
audio, video = processor.process("input.mp4")  # 自动判断类型
```

### 命令行使用

```bash
python example.py video.mp4
python example.py https://example.com/video.mp4 output/
```

## 输出文件

- 音频文件: `{原文件名}_audio.aac`
- 视频文件: `{原文件名}_video.mp4`

## 测试

```bash
python test_video.py
```

## 支持的视频格式

- MP4, AVI, MOV, MKV, WebM
- 其他ffmpeg支持的格式

# 视频去重功能

可调参数有

print("\n参数说明:")

print("  • similarity_threshold: 相似度阈值 (0-1)")

print("    - 0.9: 非常严格，只去除几乎完全相同的图片")

print("    - 0.8: 较严格，去除高度相似的图片")

print("    - 0.7: 适中，去除明显相似的图片")

print("    - 0.6: 宽松，去除大致相似的图片")

print("  • fps: 抽帧频率")

print("    - 1.0: 每秒1帧")

print("    - 0.5: 每2秒1帧")

print("    - 0.1: 每10秒1帧")
