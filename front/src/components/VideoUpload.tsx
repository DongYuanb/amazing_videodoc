import React, { useState, useCallback } from 'react';
import { Upload, FileVideo, X, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { uploadVideo, processVideo as startVideoProcessing, pollTaskStatus, StatusResponse } from '@/lib/api';
import { config } from '@/lib/config';

interface VideoUploadProps {
  onVideoUploaded: (videoData: { file: File; url: string; taskId: string }) => void;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ onVideoUploaded }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // 验证文件
  const validateFile = (file: File): string | null => {
    // 检查文件类型
    if (!config.supportedVideoFormats.includes(file.type as any)) {
      return `不支持的文件格式。支持的格式：${config.supportedVideoFormats.join(', ')}`;
    }

    // 检查文件大小
    if (file.size > config.maxFileSize) {
      const maxSizeMB = config.maxFileSize / (1024 * 1024);
      return `文件过大。最大支持 ${maxSizeMB}MB`;
    }

    return null;
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files) as File[];
    const videoFile = files.find(file => file.type.startsWith('video/'));

    if (videoFile) {
      const validationError = validateFile(videoFile);
      if (validationError) {
        setError(validationError);
        return;
      }
      processVideo(videoFile);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith('video/')) {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      processVideo(file);
    }
  }, []);

  const processVideo = async (file: File) => {
    setSelectedFile(file);
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);
    setCurrentStep('上传文件...');

    try {
      // 1. 上传文件
      setUploadProgress(10);
      const uploadResponse = await uploadVideo(file);
      console.log('Upload response:', uploadResponse);

      setUploadProgress(20);
      setCurrentStep('开始处理视频...');

      // 2. 开始处理
      await startVideoProcessing(uploadResponse.task_id, {
        enable_multimodal: true,
        keep_temp: false,
      });

      setUploadProgress(30);
      setCurrentStep('正在处理视频...');

      // 3. 轮询状态
      await pollTaskStatus(
        uploadResponse.task_id,
        (status: StatusResponse) => {
          // 更新进度和状态
          const progressMap: Record<string, number> = {
            'pending': 30,
            'asr': 40,
            'merge': 60,
            'summary': 80,
            'multimodal': 90,
          };

          const stepMap: Record<string, string> = {
            'pending': '等待处理...',
            'asr': '语音转文字...',
            'merge': '合并文本...',
            'summary': '生成摘要...',
            'multimodal': '生成图文笔记...',
          };

          setUploadProgress(progressMap[status.current_step] || status.progress * 100);
          setCurrentStep(stepMap[status.current_step] || status.current_step);
        },
        2000 // 每2秒轮询一次
      );

      // 4. 处理完成
      setUploadProgress(100);
      setCurrentStep('处理完成！');

      // 创建视频URL
      const videoUrl = URL.createObjectURL(file);

      setTimeout(() => {
        setIsUploading(false);
        onVideoUploaded({
          file,
          url: videoUrl,
          taskId: uploadResponse.task_id
        });
      }, 1000);

    } catch (error) {
      console.error('Processing error:', error);
      setError(error instanceof Error ? error.message : '处理失败，请重试');
      setIsUploading(false);
      setUploadProgress(0);
      setCurrentStep('');
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setIsUploading(false);
    setCurrentStep('');
    setError(null);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-16 relative">
      <div className="wave-layer"></div>
      <div className="text-center mb-12">
        <p className="text-sm font-medium text-foreground-muted uppercase tracking-wide mb-4">
          AI-POWERED VIDEO INTELLIGENCE | AI 视频智能解析
        </p>
        <h1 className="text-5xl font-semibold text-foreground mb-6 leading-tight">
          Smart Video Insights
          <span className="block text-4xl mt-2 text-foreground-muted">
            智能视频重点提取
          </span>
        </h1>
        <p className="text-xl text-foreground-muted max-w-2xl mx-auto leading-relaxed">
          Transform any video into structured key insights with AI precision.
          <br />
          <span className="text-lg">
            将任何视频转化为结构化重点内容，AI 精准解析每个关键时刻
          </span>
        </p>
      </div>

      <div className="flex justify-center gap-4 mb-16">
        <Button size="lg" className="bg-primary text-primary-foreground hover:bg-primary-hover">
          <Upload className="w-4 h-4 mr-2" />
          开始解析 Start Analysis
        </Button>
        <Button variant="outline" size="lg">
          查看示例 View Demo
        </Button>
      </div>

      {/* 错误提示 */}
      {error && (
        <Alert className="mb-6 border-destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-destructive">
            {error}
          </AlertDescription>
        </Alert>
      )}

      <div
        className={`
          relative border rounded-lg p-16 text-center transition-all card-striped shadow-elegant
          ${isDragOver 
            ? 'border-primary bg-primary/5' 
            : 'border-border hover:border-primary/30 hover:bg-background-secondary'}
          ${isUploading ? 'pointer-events-none' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {!selectedFile && !isUploading && (
          <>
            <div className="flex justify-center mb-6">
              <div className="p-3 bg-background-tertiary rounded">
                <Upload className="w-6 h-6 text-foreground-muted" />
              </div>
            </div>
            <h3 className="text-lg font-medium text-foreground mb-2">
              拖拽视频到这里 | Drop your video here
            </h3>
            <p className="text-sm text-foreground-muted mb-6">
              支持 MP4, MOV, AVI 格式，最大 500MB | Supports MP4, MOV, AVI up to 500MB
            </p>
            <Button 
              variant="default" 
              onClick={() => document.getElementById('file-input')?.click()}
            >
              Choose File
            </Button>
            <input
              id="file-input"
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              className="hidden"
            />
          </>
        )}

        {selectedFile && (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-3">
              <FileVideo className="w-6 h-6 text-primary" />
              <span className="font-medium text-foreground">
                {selectedFile.name}
              </span>
              {!isUploading && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={removeFile}
                  className="text-foreground-muted hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
            
            {isUploading && (
              <div className="space-y-2">
                <Progress value={uploadProgress} className="w-full" />
                <p className="text-sm text-foreground-muted">
                  {currentStep || '处理中...'}
                </p>
                <p className="text-xs text-foreground-muted">
                  {Math.round(uploadProgress)}%
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoUpload;