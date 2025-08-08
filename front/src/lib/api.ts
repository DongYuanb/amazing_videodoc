// API服务层 - 与后端视频处理API通信
import { config } from './config';

const API_BASE_URL = config.apiBaseUrl;

// API响应类型定义
export interface UploadResponse {
  task_id: string;
  filename: string;
  message: string;
}

export interface ProcessRequest {
  enable_multimodal?: boolean;
  keep_temp?: boolean;
}

export interface StatusResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_step: string;
  progress: number;
  created_at: string;
  error_message?: string;
}

export interface Segment {
  id: string;
  timestamp: string;
  timeInSeconds: number;
  title: string;
  summary: string;
  keyframe: string;
}

// 后端返回的原始结果格式
export interface BackendResultsResponse {
  task_id: string;
  status: string;
  results: {
    asr_result?: any;
    merged_text?: any;
    summary?: {
      summaries: Array<{
        start_time: string;
        end_time: string;
        summary: string;
      }>;
    };
    multimodal_notes?: any;
  };
}

// 前端使用的结果格式
export interface ResultsResponse {
  task_id: string;
  filename: string;
  status: string;
  segments: Segment[];
  total_duration: number;
  created_at: string;
}

// API错误类
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// 通用请求函数
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : '网络请求失败'
    );
  }
}

// 1. 上传视频文件
export async function uploadVideo(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest<UploadResponse>('/api/upload', {
    method: 'POST',
    body: formData,
  });
}

// 2. 开始处理视频
export async function processVideo(
  taskId: string,
  options: ProcessRequest = {}
): Promise<void> {
  const defaultOptions: ProcessRequest = {
    enable_multimodal: true,
    keep_temp: false,
    ...options,
  };

  return apiRequest<void>(`/api/process/${taskId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(defaultOptions),
  });
}

// 3. 查询处理状态
export async function getTaskStatus(taskId: string): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(`/api/status/${taskId}`);
}

// 时间字符串转换为秒数的辅助函数
function timeToSeconds(timeStr: string): number {
  try {
    const parts = timeStr.split(':');
    if (parts.length === 2) {
      return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    } else if (parts.length === 3) {
      return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
    }
    return 0;
  } catch {
    return 0;
  }
}

// 4. 获取处理结果
export async function getTaskResults(taskId: string): Promise<ResultsResponse> {
  // 获取后端原始数据
  const backendData = await apiRequest<BackendResultsResponse>(`/api/results/${taskId}`);

  // 转换为前端期望的格式
  const segments: Segment[] = [];
  let totalDuration = 0;

  // 从摘要数据中提取片段
  if (backendData.results.summary?.summaries) {
    backendData.results.summary.summaries.forEach((item, index) => {
      const startSeconds = timeToSeconds(item.start_time);
      const endSeconds = timeToSeconds(item.end_time);
      totalDuration = Math.max(totalDuration, endSeconds);

      segments.push({
        id: `segment_${index}`,
        timestamp: `${item.start_time} - ${item.end_time}`,
        timeInSeconds: startSeconds,
        title: `片段 ${index + 1} (${item.start_time} - ${item.end_time})`,
        summary: item.summary,
        keyframe: '' // 暂时为空，后续可以添加关键帧
      });
    });
  }

  return {
    task_id: backendData.task_id,
    filename: '', // 后端没有返回文件名，暂时为空
    status: backendData.status,
    segments,
    total_duration: totalDuration,
    created_at: '' // 后端没有返回创建时间，暂时为空
  };
}

// 5. 导出Markdown笔记
export async function exportMarkdown(taskId: string): Promise<Blob> {
  const url = `${API_BASE_URL}/api/export/${taskId}/markdown`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new ApiError(`导出失败: ${response.statusText}`, response.status);
  }
  
  return response.blob();
}

// 轮询状态直到完成的辅助函数
export async function pollTaskStatus(
  taskId: string,
  onProgress?: (status: StatusResponse) => void,
  pollInterval: number = 2000
): Promise<StatusResponse> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getTaskStatus(taskId);
        
        // 调用进度回调
        if (onProgress) {
          onProgress(status);
        }

        // 检查是否完成
        if (status.status === 'completed') {
          resolve(status);
          return;
        }
        
        if (status.status === 'failed') {
          reject(new ApiError(status.error_message || '处理失败'));
          return;
        }

        // 继续轮询
        setTimeout(poll, pollInterval);
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
}
