import React from 'react';
import { Search, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Navigation: React.FC = () => {
  return (
    <nav className="w-full nav-glass border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14">
          <div className="flex items-center space-x-8">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 bg-primary rounded-sm flex items-center justify-center">
                <div className="w-3 h-3 border-2 border-white rounded-sm"></div>
              </div>
              <span className="text-lg font-medium text-foreground">
                VideoSummary
              </span>
            </div>
            

          </div>
          
          <div className="flex items-center space-x-4">
            <div className="hidden md:flex items-center space-x-2 text-xs text-foreground-muted">
              <Search className="w-4 h-4" />
              <span>Ctrl + Shift + P</span>
            </div>
            <button className="text-sm text-foreground-muted hover:text-foreground transition-colors">
              Log in
            </button>
            <Button size="sm" className="text-sm">
              <Download className="w-4 h-4 mr-1" />
              Download
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;