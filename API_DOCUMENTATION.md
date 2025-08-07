# 视频处理 API 文档

## 🚀 快速开始

### 启动服务
```bash
python main.py
```
服务地址：`http://localhost:8000`  
API文档：http://localhost:8000/docs

---

## 📡 核心接口

### 1. 上传视频
**POST** `/api/upload`

上传视频文件（支持 mp4, avi, mov, mkv, webm）

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@demo_video.mp4"
```

**响应**:
```json
{
  "task_id": "dcaac6f6-d824-4743-a793-4d240a62c289",
  "filename": "demo_video.mp4",
  "message": "文件上传成功"
}
```

### 2. 开始处理
**POST** `/api/process/{task_id}`

开始处理视频

```bash
curl -X POST "http://localhost:8000/api/process/{task_id}" \
  -H "Content-Type: application/json" \
  -d '{"enable_multimodal": true, "keep_temp": false}'
```

**参数**:
- `enable_multimodal`: 是否生成图文笔记（默认 true）
- `keep_temp`: 是否保留临时文件（默认 false）

### 3. 查询状态
**GET** `/api/status/{task_id}`

```bash
curl "http://localhost:8000/api/status/{task_id}"
```

**响应**:
```json
{
  "task_id": "xxx",
  "status": "processing",
  "current_step": "asr",
  "progress": 0.3,
  "created_at": "2024-01-15T10:30:00"
}
```

**状态值**:
- `pending` - 等待处理
- `processing` - 正在处理  
- `completed` - 处理完成
- `failed` - 处理失败

### 4. 获取结果
**GET** `/api/results/{task_id}`

获取所有处理结果（JSON格式）

### 5. 导出笔记
**GET** `/api/export/{task_id}/markdown`

下载 Markdown 格式的图文笔记

---

## 🔄 完整流程

```bash
# 1. 上传视频
TASK_ID=$(curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@video.mp4" | jq -r '.task_id')

# 2. 开始处理
curl -X POST "http://localhost:8000/api/process/$TASK_ID" \
  -H "Content-Type: application/json" \
  -d '{"enable_multimodal": true}'

# 3. 查询状态（轮询直到完成）
curl "http://localhost:8000/api/status/$TASK_ID"

# 4. 导出笔记
curl -O "http://localhost:8000/api/export/$TASK_ID/markdown"
```

---

## 📋 处理步骤

系统自动按顺序执行：

1. **音频提取** - 从视频提取音频
2. **ASR转录** - 语音转文字
3. **文本合并** - 短句合并为段落
4. **摘要生成** - 生成分段摘要
5. **图文笔记** - 提取关键帧并生成图文笔记

---

## ⚠️ 注意事项

- **文件限制**: 建议视频不超过 500MB
- **处理时间**: 根据视频长度，需要几分钟到几十分钟
- **环境变量**: 需要配置 `JINA_API_KEY` 用于图片处理
- **存储空间**: 确保有足够磁盘空间
- **轮询频率**: 建议每 2-5 秒查询一次状态

---

## 📁 输出文件

处理完成后在 `storage/tasks/{task_id}/` 目录生成：

```
├── original_video.mp4      # 原始视频
├── asr_result.json        # 转录结果
├── merged_text.json       # 合并文本
├── summary.json           # 摘要
├── multimodal_notes.json  # 图文笔记数据
├── notes.md              # Markdown笔记
└── frames/               # 关键帧图片
```

---

## 🐛 常见问题

**Q: 上传失败怎么办？**  
A: 检查文件格式是否支持，文件大小是否超限

**Q: 处理卡住了？**  
A: 查看服务器日志，可能是API密钥配置问题

**Q: 图文笔记生成失败？**  
A: 确认 `JINA_API_KEY` 环境变量已正确配置

**Q: 如何提高处理速度？**  
A: 设置 `enable_multimodal: false` 跳过图文笔记生成
