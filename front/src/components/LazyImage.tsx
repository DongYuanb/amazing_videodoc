import React from 'react';

interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string;
  placeholderSrc?: string; // 自定义占位图
}

const DEFAULT_PLACEHOLDER =
  'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOTYiIGhlaWdodD0iNTYiIHZpZXdCb3g9IjAgMCA5NiA1NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9Ijk2IiBoZWlnaHQ9IjU2IiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik00OCAyOEwyNCA0MEwyNCA0MEwyNCAzNkwyNCAzNkwyNCAzMkwyNCAzMkwyNCAyOEwyNCAyOEwyNCAyNEwyNCAyNEwyNCAyMEwyNCAyMEwyNCAzNkw0OCA0OEw3MiAzNkw3MiAzNkw3MiAzMkw3MiAzMkw3MiAyOEw3MiAyOEw3MiAyNEw3MiAyNEw3MiAyMEw3MiAyMEw0OCAyOFoiIGZpbGw9IiM5Q0E5QkEiLz4KPC9zdmc+Cg==';

const LazyImage: React.FC<LazyImageProps> = ({ src, alt, placeholderSrc, className = '', onError, ...rest }) => {
  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = React.useState(false);
  const [loaded, setLoaded] = React.useState(false);
  const [currentSrc, setCurrentSrc] = React.useState<string>(placeholderSrc || DEFAULT_PLACEHOLDER);

  React.useEffect(() => {
    // 如果不支持 IntersectionObserver，则直接加载
    if (typeof window === 'undefined') return;
    if (!('IntersectionObserver' in window)) {
      setIsVisible(true);
      setCurrentSrc(src);
      return;
    }

    const node = wrapperRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            setCurrentSrc(src);
            observer.disconnect();
          }
        });
      },
      { rootMargin: '200px 0px' }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [src]);

  return (
    <div ref={wrapperRef} className={className}>
      {/* 使用 loading="lazy" + decoding="async"，并在可见时才设置真实 src */}
      <img
        src={currentSrc}
        alt={alt}
        loading="lazy"
        decoding="async"
        fetchPriority="low"
        onLoad={() => setLoaded(true)}
        onError={(e) => {
          if (onError) onError(e);
          // 回退到占位图
          if (e.currentTarget.src !== (placeholderSrc || DEFAULT_PLACEHOLDER)) {
            e.currentTarget.src = placeholderSrc || DEFAULT_PLACEHOLDER;
          }
        }}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transition: 'opacity 200ms ease',
          opacity: loaded && isVisible ? 1 : 0.2,
          backgroundColor: 'var(--color-muted, #f3f4f6)'
        }}
        {...rest}
      />
    </div>
  );
};

export default LazyImage;

