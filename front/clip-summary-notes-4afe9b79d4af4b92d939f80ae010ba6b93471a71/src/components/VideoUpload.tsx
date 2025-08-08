import React, { useState, useCallback } from 'react';
import { Upload, FileVideo, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

interface VideoUploadProps {
  onVideoUploaded: (videoData: { file: File; url: string }) => void;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ onVideoUploaded }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

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
    
    const files = Array.from(e.dataTransfer.files);
    const videoFile = files.find(file => file.type.startsWith('video/'));
    
    if (videoFile) {
      processVideo(videoFile);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith('video/')) {
      processVideo(file);
    }
  }, []);

  const processVideo = async (file: File) => {
    setSelectedFile(file);
    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + 10;
      });
    }, 200);

    // Create video URL
    const videoUrl = URL.createObjectURL(file);

    // Simulate processing delay
    setTimeout(() => {
      setUploadProgress(100);
      setTimeout(() => {
        setIsUploading(false);
        onVideoUploaded({ file, url: videoUrl });
      }, 500);
    }, 2000);
  };

  const removeFile = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setIsUploading(false);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <p className="text-sm font-medium text-foreground-muted uppercase tracking-wide mb-4">
          AI-POWERED VIDEO ANALYSIS
        </p>
        <h1 className="text-5xl font-semibold text-foreground mb-6 leading-tight">
          The editor for what's next
        </h1>
        <p className="text-xl text-foreground-muted max-w-2xl mx-auto leading-relaxed">
          Upload your video and get AI-generated summaries designed for 
          high-performance collaboration with humans and AI.
        </p>
      </div>

      <div className="flex justify-center gap-4 mb-16">
        <Button size="lg" className="bg-primary text-primary-foreground hover:bg-primary-hover">
          <Upload className="w-4 h-4 mr-2" />
          Upload now
        </Button>
        <Button variant="outline" size="lg">
          Clone source
        </Button>
      </div>

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
              Drop your video here
            </h3>
            <p className="text-sm text-foreground-muted mb-6">
              Supports MP4, MOV, AVI files up to 500MB
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
                  {uploadProgress < 90 ? 'Uploading...' : 'Processing video...'}
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