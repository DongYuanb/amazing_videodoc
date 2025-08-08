# 视频处理前端集成说明

## 🎯 功能概述

前端已完成与后端API的完整集成，支持：

- ✅ **拖拽/点击上传视频**
- ✅ **实时处理进度显示**
- ✅ **自动状态轮询**
- ✅ **动态生成视频摘要**
- ✅ **关键帧图片显示**
- ✅ **时间轴同步**
- ✅ **Markdown导出**
- ✅ **错误处理和用户反馈**

## 🔄 完整工作流程

### 1. 视频上传阶段
```typescript
// 用户拖拽或选择视频文件
// ↓ 文件验证（格式、大小）
// ↓ 调用 POST /api/upload
// ↓ 获取 task_id
```

### 2. 处理启动阶段
```typescript
// 自动调用 POST /api/process/{task_id}
// ↓ 开始视频处理
// ↓ 显示"开始处理视频..."
```

### 3. 状态轮询阶段
```typescript
// 每2秒调用 GET /api/status/{task_id}
// ↓ 更新进度条和状态文本
// ↓ 显示当前处理步骤：
//   - "语音转文字..." (asr)
//   - "合并文本..." (merge)  
//   - "生成摘要..." (summary)
//   - "生成图文笔记..." (multimodal)
```

### 4. 结果展示阶段
```typescript
// 处理完成后调用 GET /api/results/{task_id}
// ↓ 获取分段数据和关键帧
// ↓ 动态生成摘要界面
// ↓ 支持视频时间轴跳转
```

## 📁 核心文件说明

### API服务层
- `src/lib/api.ts` - 所有后端API调用
- `src/lib/config.ts` - 配置管理

### 主要组件
- `src/components/VideoUpload.tsx` - 上传和处理组件
- `src/components/VideoSummary.tsx` - 结果展示组件
- `src/components/SummarySegment.tsx` - 分段显示组件

### 页面
- `src/pages/Index.tsx` - 主页面，管理状态切换

## 🔧 配置说明

### 环境变量
```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
```

### 默认配置
```typescript
// src/lib/config.ts
{
  apiBaseUrl: 'http://localhost:8000',
  pollInterval: 2000, // 2秒轮询
  maxFileSize: 500MB,
  supportedFormats: ['mp4', 'avi', 'mov', 'mkv', 'webm']
}
```

## 🚀 启动说明

### 1. 启动后端服务
```bash
cd amazing_videodoc
python main.py
# 服务运行在 http://localhost:8000
```

### 2. 启动前端服务
```bash
cd amazing_videodoc/front
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

## 📊 数据流示例

### 后端返回的JSON结构
```json
{
  "task_id": "dcaac6f6-d824-4743-a793-4d240a62c289",
  "filename": "demo_video.mp4",
  "status": "completed",
  "segments": [
    {
      "id": "1",
      "timestamp": "00:00",
      "timeInSeconds": 0,
      "title": "Introduction & Overview",
      "summary": "视频介绍和概述内容...",
      "keyframe": "http://localhost:8000/storage/tasks/{task_id}/frames/frame_001.jpg"
    }
  ],
  "total_duration": 660,
  "created_at": "2024-01-15T10:30:00"
}
```

### 前端状态管理
```typescript
interface VideoData {
  file: File;        // 原始文件
  url: string;       // 本地预览URL
  taskId: string;    // 后端任务ID
}
```

## ⚠️ 注意事项

1. **CORS配置**: 确保后端允许前端域名的跨域请求
2. **文件大小**: 前端限制500MB，后端也需要相应配置
3. **轮询频率**: 默认2秒，可根据服务器性能调整
4. **错误处理**: 网络错误、处理失败都有相应提示
5. **资源清理**: 组件卸载时会清理本地URL对象

## 🔍 调试技巧

### 查看API调用
```javascript
// 浏览器控制台会显示所有API调用日志
console.log('Upload response:', uploadResponse);
console.log('Status update:', status);
```

### 检查网络请求
- 打开浏览器开发者工具
- 查看Network标签页
- 监控API请求和响应

### 常见问题
1. **上传失败**: 检查文件格式和大小
2. **处理卡住**: 查看后端日志和API密钥配置
3. **图片不显示**: 检查关键帧URL是否可访问
4. **导出失败**: 确认后端导出接口正常工作

## 🎨 UI特性

- **Zed风格设计**: 现代化的编辑器风格界面
- **实时进度**: 动态进度条和状态文本
- **响应式布局**: 支持桌面和移动设备
- **错误提示**: 友好的错误信息显示
- **加载状态**: 各种操作的加载指示器
