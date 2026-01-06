import React, { useRef, useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX } from 'lucide-react';
import { motion } from 'framer-motion';
import { audifyApi, AudioResponse } from '@/services/api';

interface AudioPlayerProps {
  audio: AudioResponse;
  content?: string;
  title?: string;
  mode?: 'full' | 'summary';
}

export default function AudioPlayer({ audio, content, title, mode }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string>('');

  // Get presigned URL on component mount
  useEffect(() => {
    const fetchAudioUrl = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const directUrl = audifyApi.getDirectAudioUrl(audio);
        console.log('🎵 AudioPlayer Debug:', {
          audio,
          directUrl,
          audioId: audio.audio_id,
          url: audio.url,
          storage: audio.storage
        });

        // If we have a direct S3 URL, use it
        if (directUrl.startsWith('https://') && !directUrl.includes('execute-api')) {
          console.log('🔗 Using direct S3 URL:', directUrl);
          setAudioUrl(directUrl);
          return;
        }

        // Otherwise, fetch presigned URL using the new API endpoint
        console.log('🔐 Fetching presigned URL for audio ID:', audio.audio_id);
        const presignedUrl = await audifyApi.getAudioPresignedUrl(audio.audio_id);

        console.log('✅ Got presigned URL:', presignedUrl?.substring(0, 80) + '...');
        setAudioUrl(presignedUrl);

      } catch (error) {
        console.error('❌ Failed to get audio URL:', error);
        setError('Failed to load audio. Please try again.');
      }
    };

    fetchAudioUrl();
  }, [audio]);

  useEffect(() => {
    const audioElement = audioRef.current;
    if (!audioElement || !audioUrl) return;

    const handleLoadedMetadata = () => {
      setDuration(audioElement.duration);
      setIsLoading(false);
      console.log('✅ Audio metadata loaded successfully');
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audioElement.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
    };

    const handleError = (e: Event) => {
      console.error('❌ Audio element error details:', {
        error: e,
        audioUrl: audioUrl,
        networkState: audioElement.networkState,
        readyState: audioElement.readyState,
        errorCode: audioElement.error?.code,
        errorMessage: audioElement.error?.message
      });
      setError('Failed to load audio');
      setIsLoading(false);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
      console.log('✅ Audio can play - ready for playback');
    };

    const handleLoadStart = () => {
      console.log('🔄 Audio load started for URL:', audioUrl);
    };

    const handleLoadError = () => {
      console.error('❌ Audio load error for URL:', audioUrl);
    };

    // Test the URL directly before setting it on audio element
    console.log('🧪 Testing presigned URL accessibility...');
    fetch(audioUrl, { method: 'HEAD' })
      .then(response => {
        console.log('🔗 Presigned URL test result:', {
          status: response.status,
          statusText: response.statusText,
          headers: {
            'content-type': response.headers.get('content-type'),
            'content-length': response.headers.get('content-length'),
            'access-control-allow-origin': response.headers.get('access-control-allow-origin')
          }
        });
      })
      .catch(error => {
        console.error('❌ Presigned URL test failed:', error);
      });

    audioElement.addEventListener('loadedmetadata', handleLoadedMetadata);
    audioElement.addEventListener('timeupdate', handleTimeUpdate);
    audioElement.addEventListener('ended', handleEnded);
    audioElement.addEventListener('error', handleError);
    audioElement.addEventListener('canplay', handleCanPlay);
    audioElement.addEventListener('loadstart', handleLoadStart);
    audioElement.addEventListener('abort', handleLoadError);
    audioElement.addEventListener('stalled', handleLoadError);

    return () => {
      audioElement.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audioElement.removeEventListener('timeupdate', handleTimeUpdate);
      audioElement.removeEventListener('ended', handleEnded);
      audioElement.removeEventListener('error', handleError);
      audioElement.removeEventListener('canplay', handleCanPlay);
      audioElement.removeEventListener('loadstart', handleLoadStart);
      audioElement.removeEventListener('abort', handleLoadError);
      audioElement.removeEventListener('stalled', handleLoadError);
    };
  }, [audioUrl]);

  // Update playback rate when speed changes
  useEffect(() => {
    const audioElement = audioRef.current;
    if (audioElement) {
      audioElement.playbackRate = playbackSpeed;
    }
  }, [playbackSpeed]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio || isLoading) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const skipBackward = () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, audio.currentTime - 10);
  };

  const skipForward = () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.min(audio.duration, audio.currentTime + 10);
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    const progressBar = progressRef.current;
    if (!audio || !progressBar || !duration) return;

    const rect = progressBar.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const newTime = percent * duration;
    audio.currentTime = newTime;
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isMuted) {
      audio.volume = volume;
      setIsMuted(false);
    } else {
      audio.volume = 0;
      setIsMuted(true);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    const newVolume = parseFloat(e.target.value);

    if (audio) {
      audio.volume = newVolume;
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
          {/* Audio element */}
          <audio ref={audioRef} src={audioUrl} preload="metadata" />

          {/* Title */}
          {title && (
            <div className="mb-3 sm:mb-4">
              <h3 className="text-base sm:text-lg font-semibold text-white leading-tight line-clamp-2 sm:line-clamp-1">
                {title}
              </h3>
              {mode && (
                <p className="text-xs sm:text-sm text-slate-400 capitalize mt-1">
                  {mode === 'summary' ? 'AI Summary' : 'Full Article'}
                </p>
              )}
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
                className="h-full bg-gradient-to-r from-purple-500 to-violet-500 rounded-full"
                style={{ width: `${progress}%` }}
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ type: "spring", stiffness: 400, damping: 40 }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400 mt-1 sm:mt-2">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-0 sm:justify-between">
            {/* Main controls */}
            <div className="flex items-center space-x-3 sm:space-x-4 order-1">
              <button
                onClick={skipBackward}
                disabled={isLoading}
                className="relative group w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-slate-800/50 hover:bg-slate-700/50 border border-slate-600/50 flex items-center justify-center touch-manipulation transition-all disabled:opacity-50"
              >
                <SkipBack className="w-4 h-4 sm:w-5 sm:h-5 text-slate-400 group-hover:text-white transition-colors" />
                <span className="absolute -bottom-1 text-xs text-slate-500 group-hover:text-slate-300 font-medium">10</span>
              </button>

              <Button
                variant="gradient"
                size="icon"
                onClick={togglePlay}
                disabled={isLoading}
                className="w-12 h-12 sm:w-14 sm:h-14 touch-manipulation"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : isPlaying ? (
                  <Pause className="w-6 h-6 sm:w-7 sm:h-7" />
                ) : (
                  <Play className="w-6 h-6 sm:w-7 sm:h-7 ml-0.5" />
                )}
              </Button>

              <button
                onClick={skipForward}
                disabled={isLoading}
                className="relative group w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-slate-800/50 hover:bg-slate-700/50 border border-slate-600/50 flex items-center justify-center touch-manipulation transition-all disabled:opacity-50"
              >
                <SkipForward className="w-4 h-4 sm:w-5 sm:h-5 text-slate-400 group-hover:text-white transition-colors" />
                <span className="absolute -bottom-1 text-xs text-slate-500 group-hover:text-slate-300 font-medium">10</span>
              </button>
            </div>

            {/* Volume and Speed controls - Stack on mobile */}
            <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-4 w-full sm:w-auto order-2">
              {/* Speed Control */}
              <div className="flex items-center space-x-2">
                <span className="text-slate-400 text-xs sm:text-sm whitespace-nowrap">Speed</span>
                <div className="relative">
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
              </div>

              {/* Volume controls */}
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