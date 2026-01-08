import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX } from 'lucide-react';
import { motion } from 'framer-motion';
import { audifyApi, AudioResponse } from '@/services/api';

interface ProgressiveAudioPlayerProps {
  audio: AudioResponse;
  content?: string;
  title?: string;
  mode?: 'full' | 'summary';
  progressiveAudio?: {
    is_progressive: boolean;
    total_chunks: number;
    completed_chunks: number;
    expected_durations: number[];
  } | null;
}

interface AudioProgress {
  audio_id: string;
  url: string;
  file_size?: number;
  last_modified?: number;
  status: 'available' | 'growing' | 'complete';
  message: string;
}

export default function ProgressiveAudioPlayer({
  audio,
  content,
  title,
  mode,
  progressiveAudio
}: ProgressiveAudioPlayerProps) {
  // Audio element ref (single element for simplicity)
  const primaryAudioRef = useRef<HTMLAudioElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  // Player state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Progressive audio state
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [isProgressive, setIsProgressive] = useState(false);
  const [progressiveComplete, setProgressiveComplete] = useState(false);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Use ref to track lastFileSize to avoid dependency issues
  const lastFileSizeRef = useRef<number | null>(null);

  // Get the audio element (simplified - single element now)
  const getActiveAudioElement = useCallback(() => {
    return primaryAudioRef.current;
  }, []);

  // Initial audio URL fetch
  useEffect(() => {
    const fetchInitialAudioUrl = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const directUrl = audifyApi.getDirectAudioUrl(audio);
        console.log('🎵 Progressive AudioPlayer Debug:', {
          audio,
          directUrl,
          progressiveAudio
        });

        // Check if this is progressive audio
        const isProgressiveAudio = progressiveAudio?.is_progressive ?? false;
        setIsProgressive(isProgressiveAudio);

        // Get audio URL (same process as original)
        let audioUrlToUse = directUrl;

        if (!directUrl.startsWith('https://') || directUrl.includes('execute-api')) {
          console.log('🔐 Fetching presigned URL for progressive audio ID:', audio.audio_id);
          audioUrlToUse = await audifyApi.getAudioPresignedUrl(audio.audio_id);
        }

        console.log('✅ Initial progressive audio URL:', audioUrlToUse?.substring(0, 80) + '...');
        setAudioUrl(audioUrlToUse);

        // Start progressive monitoring if needed
        if (isProgressiveAudio && progressiveAudio!.completed_chunks < progressiveAudio!.total_chunks) {
          startProgressiveMonitoring();
        }

      } catch (error) {
        console.error('❌ Failed to get progressive audio URL:', error);
        setError('Failed to load progressive audio. Please try again.');
      }
    };

    fetchInitialAudioUrl();

    // Cleanup polling on unmount
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [audio, progressiveAudio]);

  // Start monitoring for progressive audio updates
  const startProgressiveMonitoring = useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    const interval = setInterval(async () => {
      try {
        // Check for audio progress
        const progress: AudioProgress = await audifyApi.getAudioProgress(audio.audio_id);
        console.log('📊 Progressive audio progress:', progress);

        // Check if file has grown
        if (progress.file_size && progress.file_size !== lastFileSizeRef.current) {
          console.log('📈 Audio file has grown:', {
            oldSize: lastFileSizeRef.current,
            newSize: progress.file_size,
            difference: progress.file_size - (lastFileSizeRef.current || 0)
          });

          const previousFileSize = lastFileSizeRef.current;
          lastFileSizeRef.current = progress.file_size;

          // Automatically update audio with extended content (no user action needed)
          if (previousFileSize !== null) { // Don't update on first detection
            console.log('🔄 Triggering automatic background audio update...');
            console.log('📍 About to call updateAudioWithExtendedContent function');
            await updateAudioWithExtendedContent(progress.url);
          }
        }

        // Update status
        if (progress.status === 'complete') {
          setProgressiveComplete(true);
          clearInterval(interval);
          setPollingInterval(null);
        }

      } catch (error) {
        console.warn('🚨 Progressive monitoring error:', error);
        // Continue monitoring even on errors
      }
    }, 2000); // Poll every 2 seconds

    setPollingInterval(interval);
  }, [audio.audio_id]);

  // Automatically update audio with extended content (simple cache-busting approach)
  const updateAudioWithExtendedContent = async (progressUrl: string) => {
    try {
      const audioElement = getActiveAudioElement();
      if (!audioElement) return;

      // Save current playback state
      const currentTime = audioElement.currentTime;
      const wasPlaying = !audioElement.paused;
      const originalDuration = audioElement.duration;

      console.log('🔄 Refreshing audio to get extended content...', {
        currentTime: currentTime.toFixed(2),
        wasPlaying,
        originalDuration: originalDuration?.toFixed(2)
      });

      // Pause briefly during refresh
      if (wasPlaying) {
        audioElement.pause();
      }

      // Use existing audioUrl with cache busting - same S3 file, now longer!
      const separator = audioUrl.includes('?') ? '&' : '?';
      const refreshedUrl = audioUrl + separator + 'refresh=' + Date.now();
      console.log('🔗 Refreshed URL:', refreshedUrl.substring(0, 100) + '...');
      audioElement.src = refreshedUrl;

      // Handle metadata load to restore state
      const handleLoadedMetadata = () => {
        console.log(`📈 Extended audio loaded - duration: ${audioElement.duration?.toFixed(2)}s (was ${originalDuration?.toFixed(2)}s)`);

        // Restore playback position
        audioElement.currentTime = currentTime;

        // Update duration state
        setDuration(audioElement.duration || 0);

        // Resume playing (brief pause complete)
        if (wasPlaying) {
          audioElement.play().catch(error => {
            console.warn('⚠️ Could not resume playback:', error);
          });
        }

        console.log('✅ Audio refreshed with extended content');
        audioElement.removeEventListener('loadedmetadata', handleLoadedMetadata);
        audioElement.removeEventListener('error', handleError);
      };

      const handleError = (error: Event) => {
        console.error('❌ Failed to refresh audio:', error);

        // Restore original playback if refresh fails
        if (wasPlaying) {
          audioElement.play().catch(err => {
            console.warn('⚠️ Could not restore playback:', err);
          });
        }

        audioElement.removeEventListener('loadedmetadata', handleLoadedMetadata);
        audioElement.removeEventListener('error', handleError);
      };

      // Set up event listeners and refresh
      audioElement.addEventListener('loadedmetadata', handleLoadedMetadata);
      audioElement.addEventListener('error', handleError);

      audioElement.load(); // Refresh same URL, discover extended content

    } catch (error) {
      console.error('❌ Failed to refresh audio with extended content:', error);
    }
  };

  // Audio element event handlers (for active audio)
  useEffect(() => {
    const audioElement = getActiveAudioElement();
    if (!audioElement || !audioUrl) return;

    const handleLoadedMetadata = () => {
      setDuration(audioElement.duration);
      setIsLoading(false);
      console.log('✅ Progressive audio metadata loaded');
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audioElement.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
    };

    const handleError = (e: Event) => {
      console.error('❌ Progressive audio error:', e);
      setError('Progressive audio playback error');
      setIsLoading(false);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
      console.log('✅ Progressive audio ready for playback');
    };

    audioElement.addEventListener('loadedmetadata', handleLoadedMetadata);
    audioElement.addEventListener('timeupdate', handleTimeUpdate);
    audioElement.addEventListener('ended', handleEnded);
    audioElement.addEventListener('error', handleError);
    audioElement.addEventListener('canplay', handleCanPlay);

    return () => {
      audioElement.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audioElement.removeEventListener('timeupdate', handleTimeUpdate);
      audioElement.removeEventListener('ended', handleEnded);
      audioElement.removeEventListener('error', handleError);
      audioElement.removeEventListener('canplay', handleCanPlay);
    };
  }, [audioUrl, getActiveAudioElement]);

  // Set initial audio source
  useEffect(() => {
    if (audioUrl && primaryAudioRef.current) {
      primaryAudioRef.current.src = audioUrl;
      primaryAudioRef.current.load();
    }
  }, [audioUrl]);

  // Update playback rate
  useEffect(() => {
    if (primaryAudioRef.current) {
      primaryAudioRef.current.playbackRate = playbackSpeed;
    }
  }, [playbackSpeed]);

  const togglePlay = () => {
    const audioElement = getActiveAudioElement();
    if (!audioElement || isLoading) return;

    if (isPlaying) {
      audioElement.pause();
    } else {
      audioElement.play();
    }
    setIsPlaying(!isPlaying);
  };

  const skipBackward = () => {
    const audioElement = getActiveAudioElement();
    if (!audioElement) return;
    audioElement.currentTime = Math.max(0, audioElement.currentTime - 10);
  };

  const skipForward = () => {
    const audioElement = getActiveAudioElement();
    if (!audioElement) return;
    audioElement.currentTime = Math.min(audioElement.duration || 0, audioElement.currentTime + 10);
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const audioElement = getActiveAudioElement();
    const progressBar = progressRef.current;
    if (!audioElement || !progressBar || !duration) return;

    const rect = progressBar.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const newTime = percent * duration;
    audioElement.currentTime = newTime;
  };

  const toggleMute = () => {
    const audioElement = getActiveAudioElement();
    if (!audioElement) return;

    if (isMuted) {
      audioElement.volume = volume;
      setIsMuted(false);
    } else {
      audioElement.volume = 0;
      setIsMuted(true);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audioElement = getActiveAudioElement();
    const newVolume = parseFloat(e.target.value);

    if (audioElement) {
      audioElement.volume = newVolume;
      setVolume(newVolume);
      setIsMuted(newVolume === 0);
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
  };

  const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 2];

  const formatTime = (time: number) => {
    if (!time || !isFinite(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  if (error) {
    return (
      <Card className="bg-slate-900/50 border-slate-800/50 backdrop-blur-xl">
        <CardContent className="p-6">
          <div className="text-center text-red-400">
            <Volume2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full"
    >
      <Card className="bg-slate-900/50 border-slate-800/50 backdrop-blur-xl shadow-2xl">
        <CardContent className="p-4 sm:p-6">
          {/* Audio element for progressive playback */}
          <audio ref={primaryAudioRef} preload="metadata" style={{ display: 'none' }} />

          {/* Title and Progressive Status */}
          {title && (
            <div className="mb-3 sm:mb-4">
              <h3 className="text-base sm:text-lg font-semibold text-white leading-tight line-clamp-2 sm:line-clamp-1">
                {title}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                {mode && (
                  <p className="text-xs sm:text-sm text-slate-400 capitalize">
                    {mode === 'summary' ? 'AI Summary' : 'Full Article'}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Progress bar */}
          <div className="mb-4 sm:mb-4">
            <div
              ref={progressRef}
              className="w-full h-2 bg-slate-700 rounded-full cursor-pointer touch-manipulation"
              onClick={handleProgressClick}
            >
              <motion.div
                className={`h-full rounded-full ${
                  isProgressive
                    ? 'bg-gradient-to-r from-purple-500 via-violet-500 to-blue-500'
                    : 'bg-gradient-to-r from-purple-500 to-violet-500'
                }`}
                style={{ width: `${progress}%` }}
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ type: "spring", stiffness: 400, damping: 40 }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400 mt-1 sm:mt-2">
              <span>{formatTime(currentTime)}</span>
              <span className="flex items-center gap-1">
                {formatTime(duration)}
                {isProgressive && !progressiveComplete && (
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

          {/* Controls (same as original) */}
          <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-0 sm:justify-between">
            <div className="flex items-center space-x-3 sm:space-x-4 order-1">
              <button
                onClick={skipBackward}
                disabled={isLoading}
                className="group w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-slate-800/80 hover:bg-slate-700/80 border border-slate-600/50 flex items-center justify-center touch-manipulation transition-all disabled:opacity-50 backdrop-blur-sm"
              >
                <SkipBack className="w-5 h-5 sm:w-6 sm:h-6 text-slate-300 group-hover:text-white transition-colors" />
              </button>

              <Button
                variant="gradient"
                size="icon"
                onClick={togglePlay}
                disabled={isLoading}
                className={`w-14 h-14 sm:w-16 sm:h-16 touch-manipulation shadow-lg ${
                  isProgressive ? 'shadow-purple-500/50' : 'shadow-purple-500/30'
                }`}
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : isPlaying ? (
                  <Pause className="w-7 h-7 sm:w-8 sm:h-8" />
                ) : (
                  <Play className="w-7 h-7 sm:w-8 sm:h-8 ml-0.5" />
                )}
              </Button>

              <button
                onClick={skipForward}
                disabled={isLoading}
                className="group w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-slate-800/80 hover:bg-slate-700/80 border border-slate-600/50 flex items-center justify-center touch-manipulation transition-all disabled:opacity-50 backdrop-blur-sm"
              >
                <SkipForward className="w-5 h-5 sm:w-6 sm:h-6 text-slate-300 group-hover:text-white transition-colors" />
              </button>
            </div>

            {/* Volume and Speed controls */}
            <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-4 w-full sm:w-auto order-2">
              <div className="flex items-center space-x-2">
                <span className="text-slate-400 text-xs sm:text-sm whitespace-nowrap">Speed</span>
                <select
                  value={playbackSpeed}
                  onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 sm:px-3 sm:py-1 text-xs sm:text-sm text-white appearance-none cursor-pointer focus:outline-none focus:border-purple-500 min-w-[60px] sm:min-w-[65px] touch-manipulation"
                >
                  {speedOptions.map((speed) => (
                    <option key={speed} value={speed} className="bg-slate-800">
                      {speed}x
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleMute}
                  className="text-slate-400 hover:text-white w-8 h-8 sm:w-auto sm:h-auto touch-manipulation"
                >
                  {isMuted ? (
                    <VolumeX className="w-4 h-4" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                </Button>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  className="w-16 sm:w-20 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer slider touch-manipulation"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Custom slider styles */}
      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #8b5cf6;
          cursor: pointer;
          border: 2px solid #fff;
          box-shadow: 0 2px 6px rgba(139, 92, 246, 0.3);
        }

        .slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #8b5cf6;
          cursor: pointer;
          border: 2px solid #fff;
          box-shadow: 0 2px 6px rgba(139, 92, 246, 0.3);
        }
      `}</style>
    </motion.div>
  );
}