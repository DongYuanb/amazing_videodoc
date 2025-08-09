import React, { useState, useEffect, useMemo } from 'react';
import { Clock, Download, ArrowLeft, Loader2, AlertCircle, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import SummarySegment, { SegmentEditState } from './SummarySegment';
import { getTaskResults, exportMarkdown, ResultsResponse, getNotes, saveNotes } from '@/lib/api';

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

  const [notes, setNotes] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [edits, setEdits] = useState<Record<string, SegmentEditState>>({});

  const updateEdit = (id: string, update: Partial<SegmentEditState>) => {
    setEdits((prev) => ({
      ...prev,
      [id]: { ...prev[id], ...update },
    }));
  };


  // 获取处理结果 + 初始化编辑笔记
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getTaskResults(videoData.taskId);
        setResults(data);

        // 初始化每段的编辑状态（标题/摘要来自数据，布局用默认值）
        const initial: Record<string, SegmentEditState> = {};
        (data.segments || []).forEach((s) => {
          initial[s.id] = {
            title: s.title || '',
            summary: (s as any).summary || '',
            cols: 3,
            heroHeight: 280,
          };
        });
        setEdits(initial);
        setNotes('');
      } catch (error) {
        console.error('Failed to fetch results:', error);
        setError(error instanceof Error ? error.message : '获取结果失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [videoData.taskId, videoData.file.name]);

  // HTML 预览（根据分段编辑状态生成富展示）
  const preview = useMemo(() => {
    if (!results?.segments) return null;
    return (
      <div className="space-y-8">
        {results.segments.map((s) => {
          const e = edits[s.id] || { title: s.title, summary: (s as any).summary || '', cols: 3, heroHeight: 280 };
          const images = (s.keyframes && s.keyframes.length > 0) ? s.keyframes : (s.keyframe ? [s.keyframe] : []);
          return (
            <div key={s.id} className="rounded-lg border p-4">
              <div className="text-sm text-foreground-muted mb-2">{s.timestamp}</div>
              <h3 className="text-xl font-semibold mb-2">{e.title}</h3>
              <p className="mb-3 whitespace-pre-wrap">{e.summary}</p>
              <div className="rounded-lg overflow-hidden bg-muted mb-3">
                <div className="relative w-full" style={{ height: `${e.heroHeight}px` }}>
                  <img src={s.keyframe} alt="cover" className="absolute inset-0 w-full h-full object-cover" />
                </div>
              </div>
              {images.length > 0 && (
                <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${e.cols}, minmax(0, 1fr))` }}>
                  {images.map((src, idx) => (
                    <img key={idx} src={src} alt={`frame-${idx}`} className="w-full h-auto rounded-md object-cover" />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }, [results?.segments, edits]);

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
  // 由编辑状态构建 HTML 字符串（用于保存/导出）
  const buildHtmlFromEdits = (res: ResultsResponse | null, es: Record<string, SegmentEditState>) => {
    if (!res?.segments) return '';
    const blocks = res.segments.map((s) => {
      const e = es[s.id] || { title: s.title, summary: (s as any).summary || '', cols: 3, heroHeight: 280 };
      const images = (s.keyframes && s.keyframes.length > 0) ? s.keyframes : (s.keyframe ? [s.keyframe] : []);
      const gridCols = `repeat(${e.cols}, minmax(0, 1fr))`;
      const imgs = images.map((src) => `<img src="${src}" style="width:100%;height:auto;border-radius:8px;object-fit:cover;"/>`).join('');
      return `
        <section style="border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:24px;">
          <div style="color:var(--muted-foreground);font-size:12px;margin-bottom:8px;">${s.timestamp}</div>
          <h3 style="font-size:20px;font-weight:600;margin:0 0 8px 0;">${e.title}</h3>
          <p style="white-space:pre-wrap;margin:0 0 12px 0;">${e.summary || ''}</p>
          <div style="border-radius:12px;overflow:hidden;background:var(--muted);margin:0 0 12px 0;">
            <div style="position:relative;width:100%;height:${e.heroHeight}px;">
              <img src="${s.keyframe}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;" />
            </div>
          </div>
          ${images.length ? `<div style=\"display:grid;grid-template-columns:${gridCols};gap:8px;\">${imgs}</div>` : ''}
        </section>
      `;
    });
    return `<article>${blocks.join('')}</article>`;
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
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                setSaving(true);
                // 将 edits + results 生成 HTML，再保存
                const html = buildHtmlFromEdits(results, edits);
                await saveNotes(videoData.taskId, html);
              } finally {
                setSaving(false);
              }
            }}
            disabled={saving}
          >
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            {saving ? '保存中...' : '保存笔记'}
          </Button>
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
      </div>

      {/* Segments and Live HTML Preview below */}
      <div className="max-w-6xl mx-auto px-4 pb-12">
        <div className="space-y-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <h2 className="text-xl font-medium text-foreground">Segments</h2>
          </div>
          <div className="space-y-4">
            {results?.segments?.map((segment, index) => (
              <SummarySegment
                key={segment.id}
                segment={segment}
                isActive={currentTime >= segment.timeInSeconds &&
                  (index === (results?.segments?.length || 0) - 1 || currentTime < (results?.segments?.[index + 1]?.timeInSeconds || 0))}
                onClick={() => handleSegmentClick(segment.timeInSeconds)}
                edit={edits[segment.id] || { title: segment.title, summary: (segment as any).summary || '', cols: 3, heroHeight: 280 }}
                onEditChange={(u) => updateEdit(segment.id, u)}
              />
            )) || (
              <div className="text-center text-muted-foreground py-8">暂无摘要数据</div>
            )}
          </div>

          {/* Live HTML Preview */}
          <div className="mt-10">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 bg-primary rounded-full"></div>
              <h2 className="text-xl font-medium text-foreground">预览</h2>
            </div>
            <div className="prose dark:prose-invert max-w-none border rounded-md p-4 overflow-auto">
              {preview}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoSummary;