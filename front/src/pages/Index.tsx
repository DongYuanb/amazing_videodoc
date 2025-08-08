import React, { useState } from 'react';
import Navigation from '@/components/Navigation';
import VideoUpload from '@/components/VideoUpload';
import VideoSummary from '@/components/VideoSummary';

interface VideoData {
  file: File;
  url: string;
  taskId: string;
}

const Index = () => {
  const [videoData, setVideoData] = useState<VideoData | null>(null);

  const handleVideoUploaded = (data: VideoData) => {
    setVideoData(data);
  };

  const handleBack = () => {
    setVideoData(null);
  };

  return (
    <div className="min-h-screen site-bg">
      <div className="wave-layer"></div>
      <Navigation />

      <main className="py-12 px-6">
        {!videoData ? (
          <VideoUpload onVideoUploaded={handleVideoUploaded} />
        ) : (
          <VideoSummary videoData={videoData} onBack={handleBack} />
        )}
      </main>
    </div>
  );
};

export default Index;
