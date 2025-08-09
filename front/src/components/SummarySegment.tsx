import React from 'react';
import { Clock, Play } from 'lucide-react';
import { Card } from '@/components/ui/card';
import LazyImage from '@/components/LazyImage';

interface Segment {
  id: string;
  timestamp: string;
  timeInSeconds: number;
  title: string;
  summary: string;
  keyframe: string;
  keyframes?: string[]; // 多图（来自 multimodal_notes）
}

export interface SegmentEditState {
  title: string;
  summary: string;
  cols: number; // 图片列数 1-4
  heroHeight: number; // 主图高度 px
}

interface SummarySegmentProps {
  segment: Segment;
  isActive: boolean;
  onClick: () => void;
  edit: SegmentEditState;
  onEditChange: (update: Partial<SegmentEditState>) => void;
}

const SummarySegment: React.FC<SummarySegmentProps> = ({ segment, isActive, onClick, edit, onEditChange }) => {
  const [expanded, setExpanded] = React.useState(false);
  const MAX_CHARS = 220;

  const allImages = React.useMemo(() => (segment.keyframes && segment.keyframes.length > 0)
    ? segment.keyframes
    : (segment.keyframe ? [segment.keyframe] : []), [segment.keyframes, segment.keyframe]);

  return (
    <Card
      className={`
        p-4 transition-all card-striped shadow-elegant hover:shadow-hover
        ${isActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30 hover:bg-background-secondary'}
      `}
    >
      <div className="flex flex-col md:flex-row gap-6">
        {/* Media column - 1/3 width */}
        <div className="md:w-1/3 w-full">
          <div className="rounded-lg overflow-hidden bg-muted">
            <div className="relative w-full" style={{ height: `${edit.heroHeight}px` }}>
              <LazyImage src={segment.keyframe} alt={`Keyframe for ${segment.title}`} className="absolute inset-0 object-cover" />
            </div>
          </div>

          <div className="flex items-center gap-3 mt-3">
            <button
              className="px-3 py-1.5 text-xs rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition"
              onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            >
              {expanded ? '收起图片' : '查看全部图片'}
            </button>
            <button
              className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-background-secondary transition flex items-center gap-1"
              onClick={(e) => { e.stopPropagation(); onClick(); }}
            >
              <Play className="w-3 h-3" /> 跳转到该时间
            </button>
          </div>

          {expanded && allImages.length > 0 && (
            <div className={`mt-3 grid gap-2`} style={{ gridTemplateColumns: `repeat(${edit.cols}, minmax(0, 1fr))` }}>
              {allImages.map((src, idx) => (
                <div key={idx} className="relative w-full pt-[56%] bg-muted rounded overflow-hidden">
                  <LazyImage src={src} alt={`frame-${idx}`} className="absolute inset-0 object-cover" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Content column - 2/3 width */}
        <div className="md:w-2/3 w-full min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-primary' : 'bg-muted'}`}></div>
              <Clock className="w-4 h-4 text-foreground-muted" />
              <span className={`font-medium ${isActive ? 'text-primary' : 'text-foreground-muted'}`}>{segment.timestamp}</span>
            </div>
          </div>

          {/* Editable title & summary */}
          <input
            className="w-full mb-2 px-3 py-2 rounded-md border bg-background text-foreground outline-none focus:ring-2 focus:ring-primary/40"
            value={edit.title}
            onChange={(e) => onEditChange({ title: e.target.value })}
          />
          <textarea
            className="w-full min-h-[96px] px-3 py-2 rounded-md border bg-background text-foreground outline-none focus:ring-2 focus:ring-primary/40"
            value={edit.summary}
            onChange={(e) => onEditChange({ summary: e.target.value })}
          />

          {/* Layout controls */}
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-foreground-muted">
            <label className="flex items-center gap-3">
              <span className="w-24">图片列数</span>
              <input type="range" min={1} max={4} value={edit.cols} onChange={(e)=> onEditChange({ cols: parseInt(e.target.value) })} />
              <span className="w-6 text-right">{edit.cols}</span>
            </label>
            <label className="flex items-center gap-3">
              <span className="w-24">主图高度</span>
              <input type="range" min={200} max={600} step={10} value={edit.heroHeight} onChange={(e)=> onEditChange({ heroHeight: parseInt(e.target.value) })} />
              <span className="w-10 text-right">{edit.heroHeight}px</span>
            </label>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default SummarySegment;