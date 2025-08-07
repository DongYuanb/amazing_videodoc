# 视频音频转录和摘要生成系统

## 🎯 功能概述

完整的视频处理流程：
1. **音视频分流** - 使用ffmpeg提取音频
2. **ASR转录** - 腾讯云语音识别转文字
3. **文本合并** - AI智能合并短句为段落
4. **摘要生成** - 生成分段摘要和要点

## 📁 文件结构

```
asr_tencent/
├── main.py                      # 主流程脚本
├── text_merge.py               # 文本合并器（精简版）
├── summary_generator_compact.py # 摘要生成器（精简版）
├── flash_run.py                # ASR转录脚本
└── asr/                        # ASR相关模块
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install openai python-dotenv

# 设置环境变量
export ARK_API_KEY="your_openrouter_api_key"

# 确保ffmpeg可用
ffmpeg -version
```

### 2. 基本使用

```bash
# 处理单个视频
python main.py video.mp4

# 指定输出目录
python main.py video.mp4 my_output

# 在Python中使用
from main import VideoProcessor
processor = VideoProcessor()
result = processor.process_video("video.mp4")
```

### 3. 输出结果

处理完成后会生成：
- `asr_result.json` - ASR原始转录结果
- `merged_text.json` - 合并后的文本段落
- `summary.json` - 分段摘要和要点

## 📋 输出格式

### ASR结果格式
```json
{
  "result_sentences": [
    {
      "text": "转录文字",
      "start_time": 1000,
      "end_time": 2000
    }
  ]
}
```

### 合并文本格式
```json
{
  "merged_sentences": [
    {
      "text": "合并后的段落文字",
      "start_time": "00:00:01.000",
      "end_time": "00:00:05.000"
    }
  ]
}
```

### 摘要格式
```json
{
  "summaries": [
    {
      "start_time": "00:00:01.000",
      "end_time": "00:00:05.000",
      "start_time_ms": 1000,
      "end_time_ms": 5000,
      "summary": "段落摘要",
      "key_points": ["要点1", "要点2"]
    }
  ]
}
```

## 🔧 配置选项

### VideoProcessor参数
```python
processor = VideoProcessor(
    model_id="openrouter/horizon-beta",  # AI模型
    ffmpeg_path="ffmpeg"                 # ffmpeg路径
)
```

### 处理选项
```python
result = processor.process_video(
    video_path="video.mp4",
    output_dir="output",      # 输出目录
    keep_temp=False          # 是否保留临时文件
)
```

## 🎨 精简优化

按照要求对代码进行了精简：

### ✅ 已优化项目
- **最小化缩进和空格** - 紧凑的代码格式
- **简化变量名** - 内部使用短变量名
- **精简注释** - 只保留必要的顶层注释
- **合并相关功能** - 将相关功能集中在单个文件
- **使用语法糖** - lambda、列表推导式等
- **避免重复代码** - 抽象通用逻辑

### 🔄 主要改进
1. **text_merge.py** - 从162行精简到80行
2. **summary_generator_compact.py** - 新建精简版本
3. **main.py** - 整合完整workflow

## 🔗 与现有系统集成

### 与视频帧去重系统集成
```python
from main import VideoProcessor
from notebook import create_notebook_generator

# 1. 处理视频音频
processor = VideoProcessor()
audio_result = processor.process_video("lecture.mp4")

# 2. 处理视频帧（现有系统）
from video_frame_deduplicator import VideoFrameDeduplicator
deduplicator = VideoFrameDeduplicator(api_key="jina_key")
frame_result = deduplicator.process_video_frames(...)

# 3. 生成图文混排笔记
generator = create_notebook_generator()

# 添加文字内容（从音频转录）
with open(audio_result["summary"], 'r') as f:
    summaries = json.load(f)["summaries"]
    
for summary in summaries:
    generator.add_text(
        text=summary["summary"],
        timestamp=summary["start_time_ms"] / 1000,  # 转换为秒
        source="audio_transcription"
    )

# 添加图片内容（从视频帧）
for frame_path in frame_result["saved_paths"]:
    timestamp = extract_timestamp(frame_path)
    generator.add_image(frame_path, timestamp, source="video_frame")

# 生成最终笔记
notebook_path = generator.generate_notebook()
```

## 📊 性能特点

- **紧凑代码** - 大幅减少代码行数
- **高效处理** - 流水线式处理流程
- **错误恢复** - 各步骤独立，支持错误恢复
- **灵活配置** - 支持自定义模型和参数

## 🛠️ 故障排除

### 常见问题
1. **ffmpeg不可用** - 确保ffmpeg已安装并在PATH中
2. **API密钥错误** - 检查ARK_API_KEY环境变量
3. **ASR失败** - 检查flash_run.py和相关配置
4. **内存不足** - 处理大文件时可能需要更多内存

### 调试技巧
```python
# 启用详细日志
processor = VideoProcessor()
result = processor.process_video("video.mp4", keep_temp=True)

# 检查中间结果
print(json.dumps(result, indent=2))
```

## 🎉 使用示例

```bash
# 完整示例
python main.py demo.mp4 demo_output

# 输出：
# 🎬 开始处理视频: demo.mp4
# 📁 输出目录: demo_output
# 1️⃣ 提取音频...
# 音频提取完成: demo_output/audio.wav
# 2️⃣ ASR转录...
# ASR转录完成: demo_output/asr_result.json
# 3️⃣ 文本合并...
# 文本合并完成: demo_output/merged_text.json
# 4️⃣ 生成摘要...
# 摘要生成完成: demo_output/summary.json
# ✅ 处理完成！
```

现在你有了一个完整的、精简的视频音频处理流程！