import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Play, Pause, Volume2, VolumeX, ChevronUp, ChevronDown, Headphones, SkipBack, SkipForward, Gauge } from 'lucide-react';
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
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
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

  const handleSkipBack = () => {
    const newTime = Math.max(0, currentTime - 15);
    onSeek(newTime);
  };

  const handleSkipForward = () => {
    const newTime = Math.min(duration, currentTime + 15);
    onSeek(newTime);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    setShowSpeedMenu(false);
    // TODO: Connect to actual audio element playbackRate
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

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
                    {/* Skip Back */}
                    <Button
                      onClick={handleSkipBack}
                      variant="ghost"
                      size="sm"
                      className="text-slate-400 hover:text-white rounded-full w-10 h-10 p-0"
                    >
                      <SkipBack className="w-5 h-5" />
                    </Button>

                    {/* Main Play Button - Purple */}
                    <Button
                      onClick={isPlaying ? onPause : onPlay}
                      size="lg"
                      className="bg-purple-500 hover:bg-purple-400 text-white rounded-full w-14 h-14 hover:scale-105 transition-all duration-200"
                    >
                      {isPlaying ? (
                        <Pause className="w-6 h-6 fill-current" />
                      ) : (
                        <Play className="w-6 h-6 fill-current ml-0.5" />
                      )}
                    </Button>

                    {/* Skip Forward */}
                    <Button
                      onClick={handleSkipForward}
                      variant="ghost"
                      size="sm"
                      className="text-slate-400 hover:text-white rounded-full w-10 h-10 p-0"
                    >
                      <SkipForward className="w-5 h-5" />
                    </Button>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3">
                  {/* Speed Control */}
                  <div className="relative">
                    <Button
                      onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                      variant="ghost"
                      size="sm"
                      className="text-slate-400 hover:text-white p-2 text-xs"
                    >
                      {playbackSpeed}x
                    </Button>

                    {showSpeedMenu && (
                      <div className="absolute bottom-12 right-0 bg-slate-800 border border-slate-700 rounded-lg p-2 min-w-[80px]">
                        {speedOptions.map(speed => (
                          <button
                            key={speed}
                            onClick={() => handleSpeedChange(speed)}
                            className={`block w-full text-left px-2 py-1 text-sm rounded hover:bg-slate-700 ${
                              speed === playbackSpeed ? 'text-purple-400' : 'text-slate-300'
                            }`}
                          >
                            {speed}x
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

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

      {/* Main Footer Bar - Spotify Style Minimal */}
      <div className="px-4 py-3 bg-slate-900/95">
        <div className="flex items-center justify-between gap-3">
          {/* Left: Album Art + Track Info */}
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {/* Mini Album Art */}
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg flex-shrink-0">
              <Headphones className="w-5 h-5 text-white" />
            </div>

            {/* Track Info */}
            <div className="min-w-0 flex-1">
              <h4 className="text-white font-medium text-sm truncate leading-tight">{title}</h4>
              <p className="text-slate-400 text-xs truncate">Audio Article</p>
            </div>
          </div>

          {/* Right: Play Button + Expand */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Play/Pause Button - Spotify Style */}
            <Button
              onClick={isPlaying ? onPause : onPlay}
              variant="ghost"
              size="sm"
              className="text-white hover:scale-105 transition-all duration-200 p-2"
            >
              {isPlaying ? (
                <Pause className="w-6 h-6 fill-current" />
              ) : (
                <Play className="w-6 h-6 fill-current ml-0.5" />
              )}
            </Button>

            {/* Expand Button */}
            <Button
              onClick={() => setIsExpanded(!isExpanded)}
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:text-white p-1"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronUp className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Minimal Progress Bar - Only when expanded is false */}
        {!isExpanded && (
          <div className="mt-2">
            <div
              className="w-full h-1 bg-slate-700 rounded-full cursor-pointer"
              onClick={handleProgressClick}
            >
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-violet-400 rounded-full transition-all duration-150"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
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