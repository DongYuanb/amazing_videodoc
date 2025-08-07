# 📚 视频处理 API 文档

## 🌟 概述

视频处理 API 是一个完整的视频转录、摘要和图文笔记生成服务，支持从视频文件自动提取音频、进行语音识别、生成文本摘要，并创建包含关键帧的图文混排笔记。

**基础 URL**: `http://localhost:8000`

**API 文档**: `http://localhost:8000/docs` (Swagger UI)

## 🚀 快速开始

### 1. 启动服务
```bash
python start_api.py
```

### 2. 基本工作流程
1. **上传视频** → 2. **开始处理** → 3. **监控状态** → 4. **获取结果** → 5. **导出笔记**

## 📋 API 端点

### 🏥 健康检查

#### `GET /api/health`
检查服务状态

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 📤 文件上传

#### `POST /api/upload`
上传视频文件

**请求**:
- **Content-Type**: `multipart/form-data`
- **参数**: `file` (视频文件)

**支持格式**: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "demo.mp4",
  "message": "文件上传成功"
}
```

---

### ⚙️ 处理控制

#### `POST /api/process/{task_id}`
开始处理视频

**路径参数**:
- `task_id`: 任务ID

**请求体**:
```json
{
  "start_from": "audio_extract",
  "enable_multimodal": true,
  "keep_temp": false
}
```

**参数说明**:
- `start_from`: 开始步骤 (`audio_extract`, `asr`, `text_merge`, `summary`, `multimodal`)
- `enable_multimodal`: 是否启用图文笔记生成
- `keep_temp`: 是否保留临时文件

**响应示例**:
```json
{
  "message": "处理已开始",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 📊 状态查询

#### `GET /api/status/{task_id}`
获取任务处理状态

**路径参数**:
- `task_id`: 任务ID

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "current_step": "asr",
  "progress": 0.6,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:05:00",
  "error_message": null
}
```

**状态值**:
- `pending`: 等待处理
- `processing`: 正在处理
- `completed`: 处理完成
- `failed`: 处理失败

**处理步骤**:
- `audio_extract`: 音频提取
- `asr`: 语音识别
- `text_merge`: 文本合并
- `summary`: 摘要生成
- `multimodal`: 图文笔记生成

---

### 📋 结果获取

#### `GET /api/results/{task_id}`
获取处理结果

**路径参数**:
- `task_id`: 任务ID

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "results": {
    "asr_result": [...],
    "merged_text": [...],
    "summary": {
      "summaries": [...]
    },
    "multimodal_notes": {
      "video_info": {...},
      "segments": [...],
      "statistics": {...}
    }
  }
}
```

---

### 📤 导出功能

#### `GET /api/export/{task_id}/markdown`
导出 Markdown 格式笔记

**响应**: 下载 `.md` 文件

#### `GET /api/export/{task_id}/html`
导出 HTML 格式笔记

**响应**: 下载 `.html` 文件

#### `GET /api/export/{task_id}/json`
导出原始 JSON 格式笔记

**响应**: 下载 `.json` 文件

---

## 🔧 使用示例

### Python 客户端示例

```python
import requests
import time

API_BASE = "http://localhost:8000"

# 1. 上传视频
with open("video.mp4", "rb") as f:
    files = {"file": ("video.mp4", f, "video/mp4")}
    response = requests.post(f"{API_BASE}/api/upload", files=files)
    task_id = response.json()["task_id"]

# 2. 开始处理
data = {
    "start_from": "audio_extract",
    "enable_multimodal": True,
    "keep_temp": False
}
requests.post(f"{API_BASE}/api/process/{task_id}", json=data)

# 3. 监控状态
while True:
    response = requests.get(f"{API_BASE}/api/status/{task_id}")
    status = response.json()["status"]
    
    if status == "completed":
        break
    elif status == "failed":
        print("处理失败")
        break
    
    time.sleep(5)

# 4. 获取结果
results = requests.get(f"{API_BASE}/api/results/{task_id}").json()

# 5. 导出 HTML 笔记
html_response = requests.get(f"{API_BASE}/api/export/{task_id}/html")
with open("notes.html", "wb") as f:
    f.write(html_response.content)
```

### cURL 示例

```bash
# 上传视频
curl -X POST "http://localhost:8000/api/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@video.mp4"

# 开始处理
curl -X POST "http://localhost:8000/api/process/{task_id}" \
  -H "Content-Type: application/json" \
  -d '{"start_from": "audio_extract", "enable_multimodal": true}'

# 查询状态
curl "http://localhost:8000/api/status/{task_id}"

# 导出 Markdown
curl -O "http://localhost:8000/api/export/{task_id}/markdown"
```

---

## 📁 文件结构

处理完成后，每个任务会在 `storage/tasks/{task_id}/` 目录下生成以下文件：

```
storage/tasks/{task_id}/
├── metadata.json           # 任务元数据
├── original_video.mp4      # 原始视频
├── audio.wav              # 提取的音频
├── asr_result.json        # ASR 转录结果
├── merged_text.json       # 合并文本
├── summary.json           # 摘要结果
├── multimodal_notes.json  # 图文笔记数据
├── notes.md              # Markdown 笔记
├── notes.html            # HTML 笔记
└── frames/               # 关键帧图片目录
    ├── segment_1/
    └── segment_2/
```

---

## ⚠️ 注意事项

1. **文件大小限制**: 建议视频文件不超过 500MB
2. **处理时间**: 根据视频长度，处理时间从几分钟到几十分钟不等
3. **存储空间**: 确保有足够的磁盘空间存储临时文件和结果
4. **API 密钥**: 需要配置 `JINA_API_KEY` 环境变量用于图片去重
5. **并发限制**: 当前版本不支持并发处理，建议逐个处理任务

---

## 🐛 错误处理

### 常见错误码

- `400`: 请求参数错误
- `404`: 任务不存在
- `500`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

---

## 🔄 版本历史

### v1.0.0 (当前版本)
- ✅ 基础视频处理功能
- ✅ ASR 转录和摘要生成
- ✅ 图文笔记生成
- ✅ 多格式导出 (Markdown, HTML, JSON)
- ✅ RESTful API 接口
