import React, { useState, useEffect } from 'react';
import { Clock, Download, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import SummarySegment from './SummarySegment';
import { getTaskResults, exportMarkdown, ResultsResponse } from '@/lib/api';

interface VideoData {
  file: File;
  url: string;
  taskId: string;
}



interface VideoSummaryProps {
  videoData: VideoData;
  onBack: () => void;
}



const VideoSummary: React.FC<VideoSummaryProps> = ({ videoData, onBack }) => {
  const [currentTime, setCurrentTime] = useState(0);
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // 获取处理结果
  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getTaskResults(videoData.taskId);
        setResults(data);
      } catch (error) {
        console.error('Failed to fetch results:', error);
        setError(error instanceof Error ? error.message : '获取结果失败');
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [videoData.taskId]);

  const handleSegmentClick = (timeInSeconds: number) => {
    setCurrentTime(timeInSeconds);
    // 跳转到视频指定时间
    const videoElement = document.querySelector('video') as HTMLVideoElement;
    if (videoElement) {
      videoElement.currentTime = timeInSeconds;
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      const blob = await exportMarkdown(videoData.taskId);

      // 创建下载链接
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${videoData.file.name}_summary.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      setError(error instanceof Error ? error.message : '导出失败');
    } finally {
      setExporting(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // 如果正在加载，显示加载状态
  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-foreground-muted">正在获取处理结果...</p>
          </div>
        </div>
      </div>
    );
  }

  // 如果有错误，显示错误信息
  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <Button
            variant="ghost"
            onClick={onBack}
            className="text-foreground-muted hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回上传
          </Button>
        </div>
        <Alert className="border-destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-destructive">
            {error}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // 如果没有结果数据
  if (!results) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-center py-20">
          <p className="text-foreground-muted">暂无处理结果</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Top Video - smaller, centered */}
      <div className="w-full">
        <div className="max-w-6xl mx-auto px-4 pt-4">
          <div className="relative w-full h-[60vh] md:h-[70vh] bg-black rounded-lg overflow-hidden shadow-elegant flex items-center justify-center">
            <video
              src={videoData.url}
              controls
              className="w-full h-full object-contain"
              onTimeUpdate={(e: React.SyntheticEvent<HTMLVideoElement>) => setCurrentTime(e.currentTarget.currentTime)}
            />
            <div className="absolute left-4 bottom-4 text-xs text-white/80 flex items-center gap-2">
              <Clock className="w-3 h-3" />
              <span>Current: {formatDuration(Math.floor(currentTime))}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Header & Actions under the video */}
      <div className="max-w-6xl mx-auto px-4 py-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={onBack}
            className="text-foreground-muted hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Upload
          </Button>
          <div>
            <h1 className="text-2xl font-medium text-foreground">
              Video Summary
            </h1>
            <p className="text-sm text-foreground-muted">
              {videoData.file.name}
            </p>
          </div>
        </div>
        <Button
          onClick={handleExport}
          disabled={exporting}
          className="bg-primary text-primary-foreground hover:bg-primary-hover"
        >
          {exporting ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Download className="w-4 h-4 mr-2" />
          )}
          {exporting ? '导出中...' : '导出摘要'}
        </Button>
      </div>

      {/* Summary Notes below */}
      <div className="max-w-6xl mx-auto px-4 pb-12">
        <div className="space-y-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <h2 className="text-xl font-medium text-foreground">
              Summary Notes
            </h2>
          </div>
          <div className="space-y-4">
            {results?.segments?.map((segment, index) => (
              <SummarySegment
                key={segment.id}
                segment={segment}
                isActive={currentTime >= segment.timeInSeconds &&
                  (index === (results?.segments?.length || 0) - 1 || currentTime < (results?.segments?.[index + 1]?.timeInSeconds || 0))}
                onClick={() => handleSegmentClick(segment.timeInSeconds)}
              />
            )) || (
              <div className="text-center text-muted-foreground py-8">
                暂无摘要数据
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoSummary;