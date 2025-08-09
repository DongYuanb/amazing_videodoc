// 应用配置
export const config = {
  // Mock 模式开关 - 开发时可以不依赖后端
  useMock: import.meta.env.VITE_USE_MOCK === 'true' || import.meta.env.VITE_USE_MOCK === '1',

  // API基础URL - 可以通过环境变量覆盖
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',

  // 图片基础URL - 可独立配置（默认跟随 API_BASE_URL 的 /storage）
  // 如果后端未挂载 /storage，可将其指向一个单独的静态文件服务器，如 http://localhost:8001
  imageBaseUrl: (import.meta as any).env.VITE_IMAGE_BASE_URL || `${(import.meta as any).env.VITE_API_BASE_URL || 'http://localhost:8000'}/storage`,

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
