import React from 'react';
import { motion } from 'framer-motion';
import { Button } from './ui/button';
import { X, Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, ChevronDown } from 'lucide-react';

interface FullScreenAudioPlayerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
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

const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

export default function FullScreenAudioPlayer({
  isOpen,
  onClose,
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
}: FullScreenAudioPlayerProps) {
  if (!isOpen) return null;

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const newTime = percent * duration;
    onSeek(newTime);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-slate-950 z-[100] flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800/50">
        <Button
          onClick={onClose}
          variant="ghost"
          size="sm"
          className="text-slate-400 hover:text-white p-2"
        >
          <ChevronDown className="w-5 h-5" />
        </Button>
        <div className="text-center">
          <p className="text-slate-400 text-xs uppercase tracking-wider">Now Playing</p>
        </div>
        <div className="w-9" /> {/* Spacer for centering */}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col justify-center px-6 py-8">
        {/* Album Art */}
        <div className="w-64 h-64 mx-auto mb-8 rounded-2xl bg-gradient-to-br from-purple-500 to-violet-600 shadow-2xl shadow-purple-500/25 flex items-center justify-center">
          <div className="text-6xl font-bold text-white/90">A</div>
        </div>

        {/* Track Info */}
        <div className="text-center mb-8">
          <h1 className="text-white text-xl font-bold mb-2 leading-tight">
            {title}
          </h1>
          <p className="text-slate-400 text-sm">Audio Article</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div
            className="w-full h-2 bg-slate-800 rounded-full cursor-pointer relative"
            onClick={handleProgressClick}
          >
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-violet-400 rounded-full relative transition-all duration-150"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg -mr-2" />
            </div>
          </div>

          {/* Time Display */}
          <div className="flex justify-between items-center mt-2 text-xs text-slate-400">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Main Controls */}
        <div className="flex items-center justify-center gap-6 mb-8">
          {/* Skip Back */}
          <Button
            onClick={onSkipBack}
            variant="ghost"
            size="lg"
            className="text-slate-400 hover:text-white p-4"
          >
            <SkipBack className="w-8 h-8" />
          </Button>

          {/* Play/Pause - Large Purple Button */}
          <Button
            onClick={isPlaying ? onPause : onPlay}
            size="lg"
            className="bg-purple-500 hover:bg-purple-400 text-white rounded-full w-16 h-16 hover:scale-105 transition-all duration-200"
          >
            {isPlaying ? (
              <Pause className="w-8 h-8 fill-current" />
            ) : (
              <Play className="w-8 h-8 fill-current ml-1" />
            )}
          </Button>

          {/* Skip Forward */}
          <Button
            onClick={onSkipForward}
            variant="ghost"
            size="lg"
            className="text-slate-400 hover:text-white p-4"
          >
            <SkipForward className="w-8 h-8" />
          </Button>
        </div>

        {/* Secondary Controls */}
        <div className="flex items-center justify-between">
          {/* Speed Control */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">Speed:</span>
            <div className="flex gap-1">
              {speedOptions.map(speed => (
                <Button
                  key={speed}
                  onClick={() => onSpeedChange(speed)}
                  variant="ghost"
                  size="sm"
                  className={`px-3 py-1 text-xs rounded-full ${
                    speed === playbackSpeed
                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {speed}x
                </Button>
              ))}
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

      {/* Custom slider styles */}
      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #a855f7;
          cursor: pointer;
          border: 2px solid #ffffff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        .slider::-moz-range-thumb {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #a855f7;
          cursor: pointer;
          border: 2px solid #ffffff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
      `}</style>
    </motion.div>
  );
}