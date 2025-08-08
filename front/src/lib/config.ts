// 应用配置
export const config = {
  // API基础URL - 可以通过环境变量覆盖
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  
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
