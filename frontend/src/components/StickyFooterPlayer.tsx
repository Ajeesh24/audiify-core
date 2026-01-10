import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Play, Pause, Volume2, VolumeX, ChevronUp, ChevronDown, Headphones, SkipBack, SkipForward, Gauge } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { AudioResponse } from '@/services/api';
import FullScreenAudioPlayer from './FullScreenAudioPlayer';
import { useAudioContext } from '@/contexts/AudioContext';

interface StickyFooterPlayerProps {
  audio: AudioResponse | null;
  title?: string;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  playbackSpeed: number;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onMuteToggle: () => void;
  onSpeedChange: (speed: number) => void;
  onSkipBack: () => void;
  onSkipForward: () => void;
}

export default function StickyFooterPlayer({
  audio,
  title,
  isPlaying,
  currentTime,
  duration,
  volume,
  isMuted,
  playbackSpeed,
  onPlay,
  onPause,
  onSeek,
  onVolumeChange,
  onMuteToggle,
  onSpeedChange,
  onSkipBack,
  onSkipForward
}: StickyFooterPlayerProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const progressBarRef = useRef<HTMLDivElement>(null);

  // Get AudioContext for progressive information
  const audioContext = useAudioContext();

  // Function to handle skip controls - now properly functional
  const handleSkipBack = () => {
    onSkipBack();
  };

  const handleSkipForward = () => {
    onSkipForward();
  };

  const handleSpeedChange = (speed: number) => {
    onSpeedChange(speed);
    setShowSpeedMenu(false);
  };

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
  const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

  return (
    <motion.div
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      exit={{ y: 100 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="fixed bottom-0 left-0 right-0 z-50 backdrop-blur-xl border-t border-white/10 overflow-hidden"
    >
      {/* Liquid Glass Background */}
      <div className="absolute inset-0 bg-slate-900/30" />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-800/40 via-slate-900/20 to-slate-800/30" />
      <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 via-transparent to-violet-500/5" />

      {/* Glass reflection layer */}
      <div className="absolute inset-0 bg-gradient-to-t from-transparent via-white/5 to-white/10" />

      {/* Expanded Content - Now Playing Section */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="relative overflow-hidden border-b border-white/10"
          >
            {/* Enhanced liquid glass background for expanded section */}
            <div className="absolute inset-0 bg-slate-800/20" />
            <div className="absolute inset-0 bg-gradient-to-b from-purple-500/10 via-transparent to-violet-500/5" />

            <div className="relative z-10 px-6 py-8">
            <div className="max-w-sm mx-auto text-center">
              {/* Now Playing Header */}
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-6">Now Playing</p>

              {/* Large Album Art */}
              <div className="w-48 h-48 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-purple-500 to-violet-600 shadow-2xl shadow-purple-500/25 flex items-center justify-center">
                <Headphones className="w-16 h-16 text-white/90" />
              </div>

              {/* Track Info */}
              <div className="mb-8">
                <h3 className="text-white font-bold text-xl mb-2 leading-tight">{title}</h3>
                <p className="text-slate-400 text-sm">Audio Article</p>
              </div>

              {/* Progress Bar */}
              <div className="mb-8">
                <div
                  ref={progressBarRef}
                  className="w-full h-2 bg-slate-800 rounded-full cursor-pointer relative"
                  onClick={handleProgressClick}
                  onMouseMove={handleProgressDrag}
                  onMouseDown={() => setIsDragging(true)}
                  onMouseUp={() => setIsDragging(false)}
                >
                  <div
                    className={`h-full rounded-full relative transition-all duration-150 ${
                      audioContext.isProgressive
                        ? 'bg-gradient-to-r from-purple-500 via-violet-500 to-blue-500'
                        : 'bg-gradient-to-r from-purple-500 to-violet-400'
                    }`}
                    style={{ width: `${progress}%` }}
                  >
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg -mr-2" />
                  </div>
                </div>

                {/* Time Display */}
                <div className="flex justify-between items-center mt-2 text-xs text-slate-400">
                  <span>{formatTime(currentTime)}</span>
                  <span className="flex items-center gap-1">
                    {formatTime(duration)}
                    {audioContext.isProgressive && !audioContext.progressiveComplete && (
                      <>
                        <span className="text-purple-400">+</span>
                        <div className="flex items-center gap-0.5">
                          <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse"></div>
                          <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                          <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                        </div>
                      </>
                    )}
                  </span>
                </div>
              </div>

              {/* Main Controls */}
              <div className="flex items-center justify-center gap-6 mb-8">
                {/* Skip Back */}
                <Button
                  onClick={handleSkipBack}
                  variant="ghost"
                  size="lg"
                  className="text-slate-400 hover:text-white p-4"
                >
                  <SkipBack className="w-8 h-8" />
                </Button>

                {/* Large Play/Pause Button */}
                <Button
                  onClick={isPlaying ? onPause : onPlay}
                  size="lg"
                  className="bg-purple-500 hover:bg-purple-400 text-white rounded-full w-16 h-16 hover:scale-105 transition-all duration-200 flex items-center justify-center"
                >
                  {isPlaying ? (
                    <Pause className="w-7 h-7 text-white" fill="currentColor" />
                  ) : (
                    <Play className="w-7 h-7 text-white ml-0.5" fill="currentColor" />
                  )}
                </Button>

                {/* Skip Forward */}
                <Button
                  onClick={handleSkipForward}
                  variant="ghost"
                  size="lg"
                  className="text-slate-400 hover:text-white p-4"
                >
                  <SkipForward className="w-8 h-8" />
                </Button>
              </div>

              {/* Secondary Controls */}
              <div className="flex items-center justify-between">
                {/* Speed Control - Compact Dropdown Style */}
                <div className="flex items-center gap-3">
                  <span className="text-slate-400 text-sm">Speed:</span>
                  <div className="relative">
                    <Button
                      onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                      variant="ghost"
                      size="sm"
                      className="bg-slate-800/60 hover:bg-slate-700/80 text-white px-3 py-2 rounded-lg min-w-[60px] flex items-center gap-1"
                    >
                      <span className="text-sm font-medium">{playbackSpeed}x</span>
                      <ChevronDown className={`w-3 h-3 transition-transform ${showSpeedMenu ? 'rotate-180' : ''}`} />
                    </Button>

                    {/* Speed Dropdown Menu */}
                    <AnimatePresence>
                      {showSpeedMenu && (
                        <motion.div
                          initial={{ opacity: 0, y: -10, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: -10, scale: 0.95 }}
                          transition={{ duration: 0.2 }}
                          className="absolute bottom-12 left-0 bg-slate-800/95 backdrop-blur-sm border border-slate-700/50 rounded-lg p-1 min-w-[80px] shadow-xl z-10"
                        >
                          {speedOptions.map(speed => (
                            <button
                              key={speed}
                              onClick={() => handleSpeedChange(speed)}
                              className={`block w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                                speed === playbackSpeed
                                  ? 'bg-purple-500/20 text-purple-400 font-medium'
                                  : 'text-slate-300 hover:bg-slate-700/60 hover:text-white'
                              }`}
                            >
                              {speed}x
                            </button>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>

                {/* Volume Control */}
                <div className="flex items-center gap-3">
                  <Button
                    onClick={onMuteToggle}
                    variant="ghost"
                    size="sm"
                    className="text-slate-400 hover:text-white p-2"
                  >
                    {isMuted ? (
                      <VolumeX className="w-5 h-5" />
                    ) : (
                      <Volume2 className="w-5 h-5" />
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
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Footer Bar - Enhanced Liquid Glass */}
      <div className="relative px-4 py-3">
        {/* Additional glass layer for the main bar */}
        <div className="absolute inset-0 bg-white/5" />
        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 via-transparent to-violet-500/10" />

        <div className="relative z-10 flex items-center justify-between gap-3">
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
          <div className="relative z-10 mt-2">
            <div
              className="w-full h-1 bg-white/20 rounded-full cursor-pointer backdrop-blur-sm"
              onClick={handleProgressClick}
            >
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-violet-400 rounded-full transition-all duration-150 shadow-sm"
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