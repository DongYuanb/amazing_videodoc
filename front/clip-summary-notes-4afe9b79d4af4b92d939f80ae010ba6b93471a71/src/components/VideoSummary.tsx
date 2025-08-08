import React, { useState } from 'react';
import { Clock, Download, Play, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import SummarySegment from './SummarySegment';

interface VideoData {
  file: File;
  url: string;
}

interface Segment {
  id: string;
  timestamp: string;
  timeInSeconds: number;
  title: string;
  summary: string;
  keyframe: string;
}

interface VideoSummaryProps {
  videoData: VideoData;
  onBack: () => void;
}

// Mock data for demonstration
const mockSegments: Segment[] = [
  {
    id: '1',
    timestamp: '00:00',
    timeInSeconds: 0,
    title: 'Introduction & Overview',
    summary: 'The speaker introduces the main topic and provides an overview of what will be covered in the presentation. Key points include the agenda items and expected outcomes.',
    keyframe: 'https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=400&h=225&fit=crop'
  },
  {
    id: '2',
    timestamp: '02:45',
    timeInSeconds: 165,
    title: 'Core Concepts',
    summary: 'Deep dive into the fundamental concepts and principles. The discussion covers theoretical frameworks and practical applications with real-world examples.',
    keyframe: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=225&fit=crop'
  },
  {
    id: '3',
    timestamp: '05:30',
    timeInSeconds: 330,
    title: 'Implementation Strategy',
    summary: 'Detailed walkthrough of the implementation approach, including step-by-step methodology and best practices to ensure successful execution.',
    keyframe: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&h=225&fit=crop'
  },
  {
    id: '4',
    timestamp: '08:15',
    timeInSeconds: 495,
    title: 'Results & Analysis',
    summary: 'Presentation of key findings and data analysis. Charts and graphs demonstrate the effectiveness of the proposed solutions and their impact.',
    keyframe: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=225&fit=crop'
  },
  {
    id: '5',
    timestamp: '11:00',
    timeInSeconds: 660,
    title: 'Conclusion & Next Steps',
    summary: 'Summary of key takeaways and actionable next steps. Discussion of future opportunities and recommended follow-up actions.',
    keyframe: 'https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=400&h=225&fit=crop'
  }
];

const VideoSummary: React.FC<VideoSummaryProps> = ({ videoData, onBack }) => {
  const [currentTime, setCurrentTime] = useState(0);

  const handleSegmentClick = (timeInSeconds: number) => {
    setCurrentTime(timeInSeconds);
    // In a real implementation, this would seek the video to the specified time
  };

  const handleExport = () => {
    // In a real implementation, this would export the summary as PDF or other format
    console.log('Exporting summary...');
  };

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-12">
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
          className="bg-primary text-primary-foreground hover:bg-primary-hover"
        >
          <Download className="w-4 h-4 mr-2" />
          Export Summary
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Video Player */}
        <div className="lg:col-span-1">
          <Card className="p-3 card-striped shadow-elegant hover:shadow-hover transition-shadow">
            <div className="aspect-video bg-foreground rounded mb-3 flex items-center justify-center">
              <video
                src={videoData.url}
                controls
                className="w-full h-full rounded"
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-foreground-muted">
              <Clock className="w-3 h-3" />
              <span>Current: {formatDuration(Math.floor(currentTime))}</span>
            </div>
          </Card>
        </div>

        {/* Summary Notes */}
        <div className="lg:col-span-2">
          <div className="space-y-6">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-2 h-2 bg-primary rounded-full"></div>
              <h2 className="text-xl font-medium text-foreground">
                Summary Notes
              </h2>
            </div>
            
            <div className="space-y-4">
              {mockSegments.map((segment, index) => (
                <SummarySegment
                  key={segment.id}
                  segment={segment}
                  isActive={currentTime >= segment.timeInSeconds && 
                    (index === mockSegments.length - 1 || currentTime < mockSegments[index + 1].timeInSeconds)}
                  onClick={() => handleSegmentClick(segment.timeInSeconds)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoSummary;