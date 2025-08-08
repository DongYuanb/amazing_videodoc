import React, { useEffect } from 'react';
import Navigation from '@/components/Navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, User } from 'lucide-react';

interface ExtensionItem {
  id: string;
  name: string;
  description: string;
  author: string;
  downloads: string;
}

const mockExtensions: ExtensionItem[] = [
  { id: 'html', name: 'HTML', description: 'HTML 支持。', author: 'Isaac Clayton', downloads: '2.0M' },
  { id: 'catppuccin', name: 'Catppuccin', description: '柔和配色主题。', author: 'Catppuccin', downloads: '435k' },
  { id: 'toml', name: 'TOML', description: 'TOML 支持。', author: 'Max Brunsfeld, Ammar Arif', downloads: '346k' },
  { id: 'php', name: 'PHP', description: 'PHP 支持。', author: 'Piotr Osiewicz', downloads: '240k' },
  { id: 'git-firefly', name: 'Git Firefly', description: 'Git 语法高亮。', author: 'd1y, Peter Tripp', downloads: '234k' },
  { id: 'java', name: 'Java', description: 'Java 支持。', author: 'Valentine Briese 等', downloads: '234k' },
  { id: 'dockerfile', name: 'Dockerfile', description: 'Dockerfile 支持。', author: 'd1y, joshmeads', downloads: '230k' },
  { id: 'sql', name: 'SQL', description: 'SQL 语言支持。', author: '社区', downloads: '214k' },
];

const Extensions: React.FC = () => {
  useEffect(() => {
    document.title = '扩展生态 - VideoSummary';
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.setAttribute('content', '扩展生态：发现并浏览可用扩展，主题与语言支持。');

    // canonical
    let canonical = document.querySelector("link[rel='canonical']") as HTMLLinkElement | null;
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', window.location.href);
  }, []);

  return (
    <div className="min-h-screen site-bg">
      <Navigation />
      <main className="container py-16">
        <header className="text-center max-w-3xl mx-auto mb-12">
          <h1 className="text-4xl font-semibold text-foreground mb-3">扩展生态不断成长</h1>
          <p className="text-lg text-foreground-muted leading-relaxed">
            从数百个扩展中进行选择，扩展语言支持、提供不同主题，以及更多能力。
          </p>
          <div className="mt-6">
            <Button variant="outline" size="lg">创建一个扩展</Button>
          </div>
        </header>

        <section aria-label="扩展列表" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {mockExtensions.map((ext) => (
            <Card key={ext.id} className="card-striped shadow-elegant hover:shadow-hover transition-shadow p-4">
              <article>
                <div className="flex items-start justify-between mb-2">
                  <h2 className="text-base font-medium text-foreground line-clamp-1">{ext.name}</h2>
                  <div className="flex items-center gap-1 text-xs text-foreground-muted">
                    <Download className="w-3 h-3" />
                    <span>{ext.downloads}</span>
                  </div>
                </div>
                <p className="text-sm text-foreground-muted mb-3 line-clamp-2">{ext.description}</p>
                <div className="flex items-center gap-2 text-xs text-foreground-muted">
                  <User className="w-3 h-3" />
                  <span className="truncate">{ext.author}</span>
                </div>
              </article>
            </Card>
          ))}
        </section>
      </main>
    </div>
  );
};

export default Extensions;
