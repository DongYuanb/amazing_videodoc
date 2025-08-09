// 应用配置
export const config = {
  // Mock 模式开关 - 开发时可以不依赖后端
  useMock: import.meta.env.VITE_USE_MOCK === 'true' || import.meta.env.VITE_USE_MOCK === '1',
  // 伪后端任务ID（如果提供，则优先从 /storage/tasks/{ID}/multimodal_notes 读取数据）
  pseudoTaskId: (import.meta as any).env.VITE_PSEUDO_TASK_ID || '',

  // API基础URL - 可以通过环境变量覆盖
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',

  // 图片基础URL - 可独立配置（默认跟随 API_BASE_URL 的 /storage）
  // 开发时本地静态文件将通过 Vite 中间件提供（/storage 路由）
  imageBaseUrl: (import.meta as any).env.VITE_IMAGE_BASE_URL || '/storage',

  // 轮询间隔（毫秒）
  pollInterval: 2000,

  // 支持的视频格式
  supportedVideoFormats: [
    'video/mp4',
    'video/avi',
    'video/mov',
    'video/mkv',
    'video/webm'
  ],

  // 最大文件大小（字节）
  maxFileSize: 500 * 1024 * 1024, // 500MB
} as const;
