import React from 'react';
import { Clock, Play, X, ChevronLeft, ChevronRight } from 'lucide-react';
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
  const [lightboxOpen, setLightboxOpen] = React.useState(false);
  const [lightboxIndex, setLightboxIndex] = React.useState(0);
  const MAX_CHARS = 220; // 超过则折叠

  const isLong = (segment.summary?.length || 0) > MAX_CHARS;
  const displayText = !isLong || expanded
    ? segment.summary
    : segment.summary.slice(0, MAX_CHARS) + '...';

  const allImages = React.useMemo(() => (segment.keyframes && segment.keyframes.length > 0)
    ? segment.keyframes
    : (segment.keyframe ? [segment.keyframe] : []), [segment.keyframes, segment.keyframe]);

  const openLightboxAt = (idx: number) => {
    setLightboxIndex(idx);
    setLightboxOpen(true);
  };
  const closeLightbox = () => setLightboxOpen(false);
  const prevImage = (e?: React.MouseEvent) => { if (e) e.stopPropagation(); setLightboxIndex((i) => (i - 1 + allImages.length) % allImages.length); };
  const nextImage = (e?: React.MouseEvent) => { if (e) e.stopPropagation(); setLightboxIndex((i) => (i + 1) % allImages.length); };
  const onKeyDown = React.useCallback((e: KeyboardEvent) => {
    if (!lightboxOpen) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
  }, [lightboxOpen, allImages.length]);

  React.useEffect(() => {
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onKeyDown]);

  return (
    <Card
      className={`
        p-4 transition-all card-striped shadow-elegant hover:shadow-hover
        ${isActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30 hover:bg-background-secondary'}
      `}
    >
      <div className="flex flex-col md:flex-row gap-4">
        {/* Media column - 1/3 width */}
        <div className="md:w-1/3 w-full">
          <div className="relative w-full pt-[56%] rounded-lg overflow-hidden bg-muted cursor-zoom-in"
               onClick={(e) => { e.stopPropagation(); openLightboxAt(0); }}>
            <LazyImage src={segment.keyframe} alt={`Keyframe for ${segment.title}`} className="absolute inset-0" />
            {!!(segment.keyframes && segment.keyframes.length > 1) && (
              <div className="absolute right-2 bottom-2 text-[10px] bg-black/70 text-white px-2 py-0.5 rounded-full">
                +{segment.keyframes.length - 1}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 mt-3">
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

          {expanded && segment.keyframes && segment.keyframes.length > 0 && (
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">
              {segment.keyframes.map((src, idx) => (
                <div key={idx} className="relative w-full pt-[56%] bg-muted rounded overflow-hidden cursor-zoom-in"
                     onClick={(e) => { e.stopPropagation(); openLightboxAt(idx); }}>
                  <LazyImage src={src} alt={`frame-${idx}`} className="absolute inset-0" />
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

          <h3 className="font-semibold text-foreground mb-2 line-clamp-1">{segment.title}</h3>
          <p className={`text-foreground-muted text-sm leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>{displayText}</p>
          {isLong && (
            <button
              className="mt-2 text-xs text-primary hover:underline"
              onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            >
              {expanded ? '收起文本' : '展开更多'}
            </button>
          )}
        </div>
      </div>

      {/* Lightbox overlay */}
      {lightboxOpen && allImages.length > 0 && (
        <div className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center"
             onClick={closeLightbox}>
          <button className="absolute top-4 right-4 text-white/90 hover:text-white bg-white/10 hover:bg-white/20 rounded-full p-2"
                  onClick={(e)=>{ e.stopPropagation(); closeLightbox(); }}>
            ✕
          </button>
          <button className="absolute left-4 top-1/2 -translate-y-1/2 text-white/90 hover:text-white bg-white/10 hover:bg-white/20 rounded-full p-3"
                  onClick={(e)=>{ e.stopPropagation(); prevImage(e); }}>
            ‹
          </button>
          <div className="relative max-w-[90vw] max-h-[85vh] w-auto h-auto">
            <img src={allImages[lightboxIndex]} alt="preview" className="max-w-full max-h-[85vh] object-contain rounded-md shadow-2xl" />
          </div>
          <button className="absolute right-4 top-1/2 -translate-y-1/2 text-white/90 hover:text-white bg-white/10 hover:bg-white/20 rounded-full p-3"
                  onClick={(e)=>{ e.stopPropagation(); nextImage(e); }}>
            ›
          </button>
        </div>
      )}
    </Card>
  );
};

export default SummarySegment;