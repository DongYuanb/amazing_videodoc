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

interface SummarySegmentProps {
  segment: Segment;
  isActive: boolean;
  onClick: () => void;
}

const SummarySegment: React.FC<SummarySegmentProps> = ({ segment, isActive, onClick }) => {
  const [expanded, setExpanded] = React.useState(false);
  const MAX_CHARS = 220; // 超过则折叠

  const isLong = (segment.summary?.length || 0) > MAX_CHARS;
  const displayText = !isLong || expanded
    ? segment.summary
    : segment.summary.slice(0, MAX_CHARS) + '...';

  return (
    <Card
      className={`
        p-4 cursor-pointer transition-all card-striped shadow-elegant hover:shadow-hover
        ${isActive
          ? 'border-primary bg-primary/5'
          : 'border-border hover:border-primary/30 hover:bg-background-secondary'
        }
      `}
      onClick={onClick}
    >
      <div className="flex gap-4">
        {/* Thumbnails */}
        <div className="flex-shrink-0">
          {/* 预览区：首图 + 折叠按钮 */}
          <div className="relative w-28 h-16 rounded-lg overflow-hidden bg-muted">
            <LazyImage
              src={segment.keyframe}
              alt={`Keyframe for ${segment.title}`}
              className="w-full h-full"
            />
            {!!(segment.keyframes && segment.keyframes.length > 1) && (
              <div className="absolute right-1 bottom-1 text-[10px] bg-black/70 text-white px-1.5 py-0.5 rounded">
                +{segment.keyframes.length - 1}
              </div>
            )}
          </div>

          {/* 折叠的多图网格（展开状态下显示）*/}
          {expanded && segment.keyframes && segment.keyframes.length > 1 && (
            <div className="mt-2 grid grid-cols-3 gap-1 w-56">
              {segment.keyframes.slice(0, 12).map((src, idx) => (
                <div key={idx} className="relative w-full pt-[56%] bg-muted rounded overflow-hidden">
                  <LazyImage src={src} alt={`frame-${idx}`} className="absolute inset-0" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex items-center gap-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-primary' : 'bg-muted'}`}></div>
              <Clock className="w-4 h-4 text-foreground-muted" />
              <span className={`font-medium ${isActive ? 'text-primary' : 'text-foreground-muted'}`}>
                {segment.timestamp}
              </span>
            </div>
          </div>

          <h3 className="font-semibold text-foreground mb-2 line-clamp-1">
            {segment.title}
          </h3>

          <p className={`text-foreground-muted text-sm leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>
            {displayText}
          </p>
          {isLong && (
            <button
              className="mt-2 text-xs text-primary hover:underline"
              onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            >
              {expanded ? '收起' : '展开更多'}
            </button>
          )}
        </div>
      </div>
    </Card>
  );
};

export default SummarySegment;