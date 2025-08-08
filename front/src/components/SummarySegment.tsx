import React from 'react';
import { Clock, Play } from 'lucide-react';
import { Card } from '@/components/ui/card';

interface Segment {
  id: string;
  timestamp: string;
  timeInSeconds: number;
  title: string;
  summary: string;
  keyframe: string;
}

interface SummarySegmentProps {
  segment: Segment;
  isActive: boolean;
  onClick: () => void;
}

const SummarySegment: React.FC<SummarySegmentProps> = ({ segment, isActive, onClick }) => {
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
        {/* Keyframe Image */}
        <div className="flex-shrink-0">
          <div className="relative w-24 h-14 rounded-lg overflow-hidden bg-muted">
            <img
              src={segment.keyframe}
              alt={`Keyframe for ${segment.title}`}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOTYiIGhlaWdodD0iNTYiIHZpZXdCb3g9IjAgMCA5NiA1NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9Ijk2IiBoZWlnaHQ9IjU2IiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik00OCAyOEwyNCA0MEwyNCA0MEwyNCAzNkwyNCAzNkwyNCAzMkwyNCAzMkwyNCAyOEwyNCAyOEwyNCAyNEwyNCAyNEwyNCAyMEwyNCAyMEwyNCAzNkw0OCA0OEw3MiAzNkw3MiAzNkw3MiAzMkw3MiAzMkw3MiAyOEw3MiAyOEw3MiAyNEw3MiAyNEw3MiAyMEw3MiAyMEw0OCAyOFoiIGZpbGw9IiM5Q0E5QkEiLz4KPC9zdmc+Cg==';
              }}
            />
            {/* Play overlay */}
            <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
              <div className="w-6 h-6 bg-white/90 rounded-full flex items-center justify-center">
                <Play className="w-3 h-3 text-gray-800 ml-0.5" />
              </div>
            </div>
          </div>
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
          
          <p className="text-foreground-muted text-sm leading-relaxed line-clamp-3">
            {segment.summary}
          </p>
        </div>
      </div>
    </Card>
  );
};

export default SummarySegment;