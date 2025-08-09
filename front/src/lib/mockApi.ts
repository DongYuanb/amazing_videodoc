// Mock API 实现 - 用于前端独立开发
import { UploadResponse, ProcessRequest, StatusResponse, ResultsResponse, Segment } from './api';

// 内存中的任务存储
interface MockTask {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_step: string;
  progress: number;
  created_at: string;
  error_message?: string;
  file?: File;
  notes?: string;
}

const mockTasks = new Map<string, MockTask>();

// 生成随机 ID
function generateTaskId(): string {
  return 'mock_' + Math.random().toString(36).substr(2, 9);
}

// 模拟延迟
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Mock 上传视频
export async function mockUploadVideo(file: File): Promise<UploadResponse> {
  await delay(500); // 模拟网络延迟

  const taskId = generateTaskId();
  const task: MockTask = {
    id: taskId,
    filename: file.name,
    status: 'pending',
    current_step: 'pending',
    progress: 0,
    created_at: new Date().toISOString(),
    file,
    notes: ''
  };

  mockTasks.set(taskId, task);

  return {
    task_id: taskId,
    filename: file.name,
    message: '文件上传成功'
  };
}

// Mock 开始处理视频
export async function mockProcessVideo(taskId: string, options: ProcessRequest = {}): Promise<void> {
  await delay(300);

  const task = mockTasks.get(taskId);
  if (!task) {
    throw new Error('任务不存在');
  }

  task.status = 'processing';
  task.current_step = 'asr';
  task.progress = 0.1;

  // 启动模拟进度更新
  startMockProgress(taskId);
}

// 模拟进度更新
function startMockProgress(taskId: string) {
  const steps = [
    { step: 'asr', progress: 0.2, duration: 2000 },
    { step: 'merge', progress: 0.4, duration: 1500 },
    { step: 'summary', progress: 0.7, duration: 2500 },
    { step: 'multimodal', progress: 0.9, duration: 3000 },
    { step: 'completed', progress: 1.0, duration: 500 }
  ];

  let currentStepIndex = 0;

  function updateStep() {
    const task = mockTasks.get(taskId);
    if (!task || currentStepIndex >= steps.length) return;

    const currentStep = steps[currentStepIndex];
    task.current_step = currentStep.step;
    task.progress = currentStep.progress;

    if (currentStep.step === 'completed') {
      task.status = 'completed';
      task.current_step = 'finished';
    }

    currentStepIndex++;

    if (currentStepIndex < steps.length) {
      setTimeout(updateStep, currentStep.duration);
    }
  }

  setTimeout(updateStep, 1000);
}

// Mock 获取任务状态
export async function mockGetTaskStatus(taskId: string): Promise<StatusResponse> {
  await delay(200);

  const task = mockTasks.get(taskId);
  if (!task) {
    throw new Error('任务不存在');
  }

  return {
    task_id: taskId,
    status: task.status,
    current_step: task.current_step,
    progress: task.progress,
    created_at: task.created_at,
    error_message: task.error_message
  };
}

// Mock 获取处理结果
export async function mockGetTaskResults(taskId: string): Promise<ResultsResponse> {
  await delay(500);

  const task = mockTasks.get(taskId);
  if (!task) {
    throw new Error('任务不存在');
  }

  if (task.status !== 'completed') {
    throw new Error('任务尚未完成');
  }

  // 生成模拟的分段数据
  const segments: Segment[] = [
    {
      id: 'segment_0',
      timestamp: '00:00 - 02:30',
      timeInSeconds: 0,
      title: '片段 1 (00:00 - 02:30)',
      summary: '视频开始部分，介绍了项目的背景和目标。讲述了为什么需要开发这个视频处理系统，以及它能解决什么问题。',
      keyframe: '/demo/frame1.jpg',
      keyframes: ['/demo/frame1.jpg', '/demo/frame2.jpg']
    },
    {
      id: 'segment_1',
      timestamp: '02:30 - 05:15',
      timeInSeconds: 150,
      title: '片段 2 (02:30 - 05:15)',
      summary: '技术架构介绍。详细说明了系统的整体架构，包括前端、后端、AI模型等各个组件的作用和交互方式。',
      keyframe: '/demo/frame3.jpg',
      keyframes: ['/demo/frame3.jpg', '/demo/frame4.jpg']
    },
    {
      id: 'segment_2',
      timestamp: '05:15 - 08:00',
      timeInSeconds: 315,
      title: '片段 3 (05:15 - 08:00)',
      summary: '功能演示环节。展示了视频上传、处理、生成摘要等核心功能的实际操作过程，包括用户界面和处理结果。',
      keyframe: '/demo/frame5.jpg',
      keyframes: ['/demo/frame5.jpg', '/demo/frame6.jpg']
    },
    {
      id: 'segment_3',
      timestamp: '08:00 - 10:30',
      timeInSeconds: 480,
      title: '片段 4 (08:00 - 10:30)',
      summary: '总结与展望。回顾了项目的主要成果，讨论了未来的改进方向和可能的扩展功能。',
      keyframe: '/demo/frame7.jpg',
      keyframes: ['/demo/frame7.jpg', '/demo/frame8.jpg']
    }
  ];

  return {
    task_id: taskId,
    filename: task.filename,
    status: task.status,
    segments,
    total_duration: 630, // 10分30秒
    created_at: task.created_at
  };
}

// Mock 获取/保存笔记（编辑）
export async function mockGetNotes(taskId: string): Promise<string> {
  await delay(200);
  const task = mockTasks.get(taskId);
  if (!task) throw new Error('任务不存在');
  if (task.notes && task.notes.trim()) return task.notes;
  // 默认用 segments 生成一份初稿
  const results = await mockGetTaskResults(taskId);
  const md: string[] = ['# 视频摘要笔记', '', `文件名: ${results.filename}`, ''];
  results.segments.forEach((s) => {
    md.push(`## ${s.title}`, '', s.summary, '');
  });
  return md.join('\n');
}

export async function mockSaveNotes(taskId: string, content: string): Promise<void> {
  await delay(200);
  const task = mockTasks.get(taskId);
  if (!task) throw new Error('任务不存在');
  task.notes = content;
}

// Mock 导出 Markdown
export async function mockExportMarkdown(taskId: string): Promise<Blob> {
  await delay(400);
  const task = mockTasks.get(taskId);
  if (!task) throw new Error('任务不存在');
  const content = task.notes || (await mockGetNotes(taskId));
  return new Blob([content], { type: 'text/markdown' });
}
