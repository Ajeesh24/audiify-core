import React, { useRef } from 'react';
import { Button } from './ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';
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
  showNavigationButtons?: boolean;
}

export default function HorizontalSection({
  title,
  subtitle,
  items,
  isAuthenticated,
  onPlay,
  onAuthRequired,
  showNavigationButtons = true
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
          <h2 className="text-xl sm:text-2xl font-bold text-white group-hover:text-green-400 transition-colors duration-200">
            {title}
          </h2>
          {subtitle && (
            <p className="text-sm text-slate-400 hover:text-slate-300 transition-colors duration-200">
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
              className="text-slate-400 hover:text-white hover:bg-slate-800/60 rounded-full w-8 h-8 p-0"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              onClick={scrollRight}
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:text-white hover:bg-slate-800/60 rounded-full w-8 h-8 p-0"
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
              gradient={item.gradient}
              icon={item.icon}
              type={item.type}
              isAuthenticated={isAuthenticated}
              onPlay={onPlay}
              onAuthRequired={onAuthRequired}
            />
          ))}

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