import React, { useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import CompactAudioCard from './CompactAudioCard';

interface AudioItem {
  id: string;
  title: string;
  subtitle?: string;
  duration?: number;
  date?: string;
  status?: 'empty' | 'generating' | 'ready' | 'error';
  gradient?: string;
  icon?: string;
  type: 'brief' | 'article' | 'personal';
}

interface HorizontalSectionProps {
  title: string;
  subtitle?: string;
  items: AudioItem[];
  isAuthenticated: boolean;
  onPlay: (id: string) => void;
  onAuthRequired?: (trigger: { type: string; id: string }) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  loading?: boolean;
  showNavigationButtons?: boolean;
  isDarkMode?: boolean;
}

export default function HorizontalSection({
  title,
  subtitle,
  items,
  isAuthenticated,
  onPlay,
  onAuthRequired,
  onLoadMore,
  hasMore = false,
  loading = false,
  showNavigationButtons = true,
  isDarkMode = true
}: HorizontalSectionProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scrollLeft = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: -200, behavior: 'smooth' });
    }
  };

  const scrollRight = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: 200, behavior: 'smooth' });
    }
  };

  // Infinite scroll detection
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || !onLoadMore || !hasMore || loading) return;

    const handleScroll = () => {
      const { scrollLeft, scrollWidth, clientWidth } = container;
      // Trigger load more when user scrolls to within 300px of the end
      const nearEnd = scrollLeft + clientWidth >= scrollWidth - 300;

      if (nearEnd && !loading && hasMore) {
        console.log('Near end of scroll, loading more...');
        onLoadMore();
      }
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [onLoadMore, hasMore, loading]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-8"
    >
      {/* Section Header */}
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="group cursor-pointer">
          <h2 className={`text-xl sm:text-2xl font-bold group-hover:text-green-400 transition-colors duration-200 ${
            isDarkMode ? 'text-white' : 'text-slate-900'
          }`}>
            {title}
          </h2>
          {subtitle && (
            <p className={`text-sm hover:text-slate-300 transition-colors duration-200 ${
              isDarkMode ? 'text-slate-400' : 'text-slate-600'
            }`}>
              {subtitle}
            </p>
          )}
        </div>

        {/* Navigation Buttons - Hidden on mobile, visible on larger screens */}
        {showNavigationButtons && items.length > 0 && (
          <div className="hidden md:flex items-center gap-2">
            <Button
              onClick={scrollLeft}
              variant="ghost"
              size="sm"
              className={`rounded-full w-8 h-8 p-0 ${
                isDarkMode
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              onClick={scrollRight}
              variant="ghost"
              size="sm"
              className={`rounded-full w-8 h-8 p-0 ${
                isDarkMode
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>

      {/* Horizontal Scrolling Container */}
      <div className="relative">
        <div
          ref={scrollContainerRef}
          className="flex gap-4 overflow-x-auto scrollbar-hide pb-2 px-1"
          style={{
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            WebkitScrollbar: { display: 'none' }
          }}
        >
          {items.map((item) => (
            <CompactAudioCard
              key={item.id}
              id={item.id}
              title={item.title}
              subtitle={item.subtitle}
              duration={item.duration}
              date={item.date}
              status={item.status}
              icon={item.icon}
              type={item.type}
              isAuthenticated={isAuthenticated}
              onPlay={onPlay}
              onAuthRequired={onAuthRequired}
              isDarkMode={isDarkMode}
            />
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className={`flex-shrink-0 w-32 h-48 rounded-lg flex items-center justify-center ${
              isDarkMode ? 'bg-slate-800/40' : 'bg-slate-200/40'
            }`}>
              <Loader2 className={`w-6 h-6 animate-spin ${
                isDarkMode ? 'text-slate-400' : 'text-slate-500'
              }`} />
            </div>
          )}

          {/* Add some padding to the end */}
          <div className="flex-shrink-0 w-4" />
        </div>

        {/* Gradient overlays for scroll indication */}
        <div className="absolute left-0 top-0 bottom-2 w-8 bg-gradient-to-r from-slate-950 via-slate-950/50 to-transparent pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        <div className="absolute right-0 top-0 bottom-2 w-8 bg-gradient-to-l from-slate-950 via-slate-950/50 to-transparent pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      </div>

      {/* Custom scrollbar styles */}
      <style jsx>{`
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </motion.div>
  );
}