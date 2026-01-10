import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Play, Pause, Volume2, VolumeX, ChevronUp, ChevronDown, Headphones } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { AudioResponse } from '@/services/api';

interface StickyFooterPlayerProps {
  audio: AudioResponse | null;
  title?: string;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onMuteToggle: () => void;
  onExpand?: () => void;
}

export default function StickyFooterPlayer({
  audio,
  title,
  isPlaying,
  currentTime,
  duration,
  volume,
  isMuted,
  onPlay,
  onPause,
  onSeek,
  onVolumeChange,
  onMuteToggle,
  onExpand
}: StickyFooterPlayerProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const progressBarRef = useRef<HTMLDivElement>(null);

  if (!audio || !title) {
    return null;
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressBarRef.current || duration === 0) return;

    const rect = progressBarRef.current.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const newTime = percent * duration;
    onSeek(newTime);
  };

  const handleProgressDrag = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging || !progressBarRef.current || duration === 0) return;

    const rect = progressBarRef.current.getBoundingClientRect();
    const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const newTime = percent * duration;
    onSeek(newTime);
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <motion.div
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      exit={{ y: 100 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-lg border-t border-slate-700/50"
    >
      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden bg-slate-800/80 border-b border-slate-700/50 p-4"
          >
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                <div>
                  <h3 className="text-white font-semibold text-lg truncate">{title}</h3>
                  <p className="text-slate-400 text-sm">Audio Article</p>
                </div>

                <div className="text-center">
                  <p className="text-slate-400 text-sm mb-2">Now Playing</p>
                  <div className="flex items-center justify-center gap-4">
                    <Button
                      onClick={isPlaying ? onPause : onPlay}
                      size="lg"
                      className="bg-green-500 hover:bg-green-400 text-black rounded-full w-12 h-12 hover:scale-105 transition-all duration-200"
                    >
                      {isPlaying ? (
                        <Pause className="w-5 h-5 fill-current" />
                      ) : (
                        <Play className="w-5 h-5 fill-current ml-0.5" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3">
                  <Button
                    onClick={onMuteToggle}
                    variant="ghost"
                    size="sm"
                    className="text-slate-400 hover:text-white p-2"
                  >
                    {isMuted ? (
                      <VolumeX className="w-4 h-4" />
                    ) : (
                      <Volume2 className="w-4 h-4" />
                    )}
                  </Button>
                  <div className="w-20">
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={isMuted ? 0 : volume}
                      onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
                      className="w-full h-1 bg-slate-600 rounded-lg appearance-none slider"
                    />
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Footer Bar */}
      <div className="px-4 py-4 max-w-none bg-slate-900/95">
        <div className="flex items-center gap-4">
          {/* Track Info with Album Art */}
          <div className="flex items-center gap-3 flex-shrink-0 min-w-0 flex-1 max-w-xs">
            {/* Mini Album Art */}
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg flex-shrink-0">
              <Headphones className="w-6 h-6 text-white" />
            </div>

            <div className="min-w-0 flex-1">
              <h4 className="text-white font-medium text-sm truncate">{title}</h4>
              <p className="text-slate-400 text-xs">Audio Article</p>
            </div>
          </div>

          {/* Player Controls */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <Button
              onClick={isPlaying ? onPause : onPlay}
              variant="ghost"
              size="sm"
              className="text-white hover:text-green-400 hover:scale-110 transition-all duration-200 p-2"
            >
              {isPlaying ? (
                <Pause className="w-5 h-5 fill-current" />
              ) : (
                <Play className="w-5 h-5 fill-current ml-0.5" />
              )}
            </Button>
          </div>

          {/* Progress Bar */}
          <div className="flex-1 mx-4 min-w-0">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="flex-shrink-0 w-10 text-right">{formatTime(currentTime)}</span>
              <div
                ref={progressBarRef}
                className="flex-1 h-2 bg-slate-700 rounded-full cursor-pointer relative group"
                onClick={handleProgressClick}
                onMouseMove={handleProgressDrag}
                onMouseDown={() => setIsDragging(true)}
                onMouseUp={() => setIsDragging(false)}
                onMouseLeave={() => setIsDragging(false)}
              >
                <div
                  className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full relative transition-all duration-150"
                  style={{ width: `${progress}%` }}
                >
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 -mr-2"></div>
                </div>
              </div>
              <span className="flex-shrink-0 w-10">{formatTime(duration)}</span>
            </div>
          </div>

          {/* Volume & Expand */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button
              onClick={onMuteToggle}
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:text-white p-2 hidden sm:flex"
            >
              {isMuted ? (
                <VolumeX className="w-4 h-4" />
              ) : (
                <Volume2 className="w-4 h-4" />
              )}
            </Button>

            <Button
              onClick={() => setIsExpanded(!isExpanded)}
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:text-white p-2"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronUp className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Custom slider styles */}
      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #10b981;
          cursor: pointer;
          border: 2px solid #ffffff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        .slider::-moz-range-thumb {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #10b981;
          cursor: pointer;
          border: 2px solid #ffffff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
      `}</style>
    </motion.div>
  );
}