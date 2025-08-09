// API服务层 - 与后端视频处理API通信
import { config } from './config';
import {
  mockUploadVideo,
  mockProcessVideo,
  mockGetTaskStatus,
  mockGetTaskResults,
  mockExportMarkdown,
  mockGetNotes,
  mockSaveNotes,
} from './mockApi';

const API_BASE_URL = config.apiBaseUrl;
const IMAGE_BASE_URL = config.imageBaseUrl;

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
  keyframe: string; // 首图（用于卡片预览）
  keyframes?: string[]; // 多张图片（来自 multimodal_notes ）
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
  if (config.useMock) {
    return mockUploadVideo(file);
  }

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
  if (config.useMock) {
    return mockProcessVideo(taskId, options);
  }

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
  if (config.useMock) {
    return mockGetTaskStatus(taskId);
  }
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

// 4. 获取处理结果（含多模态图片）
export async function getTaskResults(taskId: string): Promise<ResultsResponse> {
  if (config.useMock) {
    return mockGetTaskResults(taskId);
  }

  // 1) 获取后端原始数据（摘要等）
  const backendData = await apiRequest<BackendResultsResponse>(`/api/results/${taskId}`);

  // 2) 获取多模态 JSON（可能不存在，失败时忽略）
  let multimodal: any | null = null;
  try {
    const res = await fetch(`${API_BASE_URL}/api/export/${taskId}/json`);
    if (res.ok) {
      multimodal = await res.json();
    }
  } catch (_) {}

  // 转换为前端期望的格式
  const segments: Segment[] = [];
  let totalDuration = 0;

  // 将多模态段落索引，方便按时间匹配
  const mmSegments: Array<any> = multimodal?.segments || [];

  // 从摘要数据中提取片段
  if (backendData.results.summary?.summaries) {
    backendData.results.summary.summaries.forEach((item, index) => {
      const startSeconds = timeToSeconds(item.start_time);
      const endSeconds = timeToSeconds(item.end_time);
      totalDuration = Math.max(totalDuration, endSeconds);

      // 匹配相同时间段的多模态条目
      const mm = mmSegments.find(s => s.start_time === item.start_time && s.end_time === item.end_time);
      const keyframes: string[] = (mm?.key_frames || []).map((relPath: string) => {
        // 将相对路径转为可访问 URL（可配置图片域）
        const base = `${IMAGE_BASE_URL}/tasks/${taskId}/multimodal_notes`;
        return `${base}/${relPath}`;
      });

      segments.push({
        id: `segment_${index}`,
        timestamp: `${item.start_time} - ${item.end_time}`,
        timeInSeconds: startSeconds,
        title: `片段 ${index + 1} (${item.start_time} - ${item.end_time})`,
        summary: item.summary,
        keyframe: keyframes[0] || '',
        keyframes,
      });
    });
  }

  return {
    task_id: backendData.task_id,
    filename: '',
    status: backendData.status,
    segments,
    total_duration: totalDuration,
    created_at: ''
  };
}

// 5. 导出Markdown笔记（如果已保存到后端，会走后端；否则用前端当前内容生成）
export async function exportMarkdown(taskId: string): Promise<Blob> {
  if (config.useMock) {
    return mockExportMarkdown(taskId);
  }

  const url = `${API_BASE_URL}/api/export/${taskId}/markdown`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new ApiError(`导出失败: ${response.statusText}`, response.status);
  }

  return response.blob();
}

// 6. 获取/保存笔记内容（用于编辑）
export async function getNotes(taskId: string): Promise<string> {
  if (config.useMock) {
    return mockGetNotes(taskId);
  }
  const res = await fetch(`${API_BASE_URL}/api/notes/${taskId}`);
  if (!res.ok) throw new ApiError('获取笔记失败', res.status);
  return await res.text();
}

export async function saveNotes(taskId: string, content: string): Promise<void> {
  if (config.useMock) {
    return mockSaveNotes(taskId, content);
  }
  const res = await fetch(`${API_BASE_URL}/api/notes/${taskId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new ApiError('保存笔记失败', res.status);
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
