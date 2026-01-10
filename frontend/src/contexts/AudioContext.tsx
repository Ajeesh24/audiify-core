import React, { createContext, useContext, useState, useRef, useCallback, useEffect } from 'react';
import { AudioResponse, audifyApi } from '@/services/api';

interface AudioContextType {
  // Audio state
  audioRef: React.RefObject<HTMLAudioElement>;
  currentAudio: AudioResponse | null;
  currentTitle: string | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  playbackSpeed: number;

  // Progressive audio state
  isProgressive: boolean;
  progressiveComplete: boolean;
  audioUrl: string | null;
  audioLoading: boolean;

  // Actions
  setCurrentAudio: (audio: AudioResponse | null, title?: string, progressive?: boolean) => void;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  setPlaybackSpeed: (speed: number) => void;
  skipBack: (seconds?: number) => void;
  skipForward: (seconds?: number) => void;

  // Internal state setters (for audio element callbacks)
  setIsPlaying: (playing: boolean) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
}

const AudioContext = createContext<AudioContextType | null>(null);

export const useAudioContext = () => {
  const context = useContext(AudioContext);
  if (!context) {
    throw new Error('useAudioContext must be used within AudioProvider');
  }
  return context;
};

interface AudioProviderProps {
  children: React.ReactNode;
}

export const AudioProvider: React.FC<AudioProviderProps> = ({ children }) => {
  const audioRef = useRef<HTMLAudioElement>(null);

  // Basic audio state
  const [currentAudio, setCurrentAudioState] = useState<AudioResponse | null>(null);
  const [currentTitle, setCurrentTitle] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackSpeed, setPlaybackSpeedState] = useState(1);

  // Progressive audio state
  const [isProgressive, setIsProgressive] = useState(false);
  const [progressiveComplete, setProgressiveComplete] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const lastFileSizeRef = useRef<number | null>(null);

  const setCurrentAudio = useCallback((audio: AudioResponse | null, title?: string, progressive: boolean = false) => {
    setCurrentAudioState(audio);
    setCurrentTitle(title || null);
    setIsProgressive(progressive);
    setProgressiveComplete(!progressive); // If not progressive, it's complete
    setAudioUrl(null); // Reset URL, will be set by effect
    setAudioLoading(true);

    if (!audio) {
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(0);
      setAudioUrl(null);
      setIsProgressive(false);
      setProgressiveComplete(false);

      // Clean up polling
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
    }
  }, [pollingInterval]);

  const play = useCallback(async () => {
    if (audioRef.current && currentAudio) {
      try {
        // Set playing state immediately for responsive UI
        setIsPlaying(true);
        await audioRef.current.play();
        console.log('▶️ Audio play started successfully');
      } catch (error) {
        console.error('❌ Failed to play audio:', error);
        setIsPlaying(false);

        // Handle common autoplay errors
        if (error.name === 'NotAllowedError') {
          console.log('🎵 Autoplay blocked - user gesture required');
        }
      }
    }
  }, [currentAudio]);

  const pause = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      console.log('⏸️ Audio paused');
    }
  }, []);

  const seek = useCallback((time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  }, []);

  const setVolume = useCallback((newVolume: number) => {
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
      setVolumeState(newVolume);
      setIsMuted(newVolume === 0);
    }
  }, []);

  const toggleMute = useCallback(() => {
    if (audioRef.current) {
      const newMuted = !isMuted;
      audioRef.current.muted = newMuted;
      setIsMuted(newMuted);
    }
  }, [isMuted]);

  const setPlaybackSpeed = useCallback((speed: number) => {
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
      setPlaybackSpeedState(speed);
      console.log('🎚️ Playback speed set to:', speed + 'x');
    }
  }, []);

  const skipBack = useCallback((seconds: number = 15) => {
    if (audioRef.current) {
      const newTime = Math.max(0, audioRef.current.currentTime - seconds);
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
      console.log('⏮️ Skipped back', seconds, 'seconds');
    }
  }, []);

  const skipForward = useCallback((seconds: number = 15) => {
    if (audioRef.current && duration > 0) {
      const newTime = Math.min(duration, audioRef.current.currentTime + seconds);
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
      console.log('⏭️ Skipped forward', seconds, 'seconds');
    }
  }, [duration]);

  // Audio URL fetching effect
  useEffect(() => {
    const fetchAudioUrl = async () => {
      if (!currentAudio) return;

      try {
        setAudioLoading(true);

        // Get direct URL first
        const directUrl = audifyApi.getDirectAudioUrl(currentAudio);
        let audioUrlToUse = directUrl;

        // Get presigned URL if needed
        if (!directUrl.startsWith('https://') || directUrl.includes('execute-api')) {
          console.log('🔐 Fetching presigned URL for audio ID:', currentAudio.audio_id);
          audioUrlToUse = await audifyApi.getAudioPresignedUrl(currentAudio.audio_id);
        }

        console.log('✅ Audio URL ready:', audioUrlToUse?.substring(0, 80) + '...');
        setAudioUrl(audioUrlToUse);

        // Start progressive monitoring if this is a progressive audio
        if (isProgressive) {
          startProgressiveMonitoring();
        }

      } catch (error) {
        console.error('❌ Failed to get audio URL:', error);
        setAudioLoading(false);
      }
    };

    fetchAudioUrl();

    // Cleanup polling on audio change
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
    };
  }, [currentAudio, isProgressive]);

  // Progressive monitoring function (adapted from ProgressiveAudioPlayer)
  const startProgressiveMonitoring = useCallback(() => {
    if (!currentAudio) return;

    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    let lastRefreshChunk = 1;

    const interval = setInterval(async () => {
      try {
        const progress = await audifyApi.getAudioProgress(currentAudio.audio_id);
        console.log('📊 Progressive audio progress:', progress);

        const currentChunk = progress.chunks_completed || 1;
        const totalChunks = progress.total_chunks || 1;

        // Strategic refresh logic
        const shouldRefresh = (
          currentChunk > lastRefreshChunk &&
          (currentChunk >= Math.ceil(totalChunks * 0.5) ||
           currentChunk >= Math.ceil(totalChunks * 0.75) ||
           currentChunk >= totalChunks)
        );

        // Check if file has grown
        if (progress.file_size && progress.file_size !== lastFileSizeRef.current) {
          console.log('📈 Audio file has grown:', {
            oldSize: lastFileSizeRef.current,
            newSize: progress.file_size,
            chunks: `${progress.chunks_completed}/${progress.total_chunks}`,
            shouldRefresh
          });

          lastFileSizeRef.current = progress.file_size;

          // Refresh at strategic points
          if (shouldRefresh && progress.url && audioRef.current) {
            lastRefreshChunk = currentChunk;
            console.log(`🔄 Strategic refresh at chunk ${currentChunk}/${totalChunks}...`);
            await updateAudioWithExtendedContent(progress.url);
          }
        }

        // Check for completion
        const isComplete = progress.status === 'complete' ||
                          (progress.chunks_completed && progress.total_chunks &&
                           progress.chunks_completed >= progress.total_chunks);

        if (isComplete) {
          console.log('✅ Progressive audio generation complete');

          if (progress.url && audioRef.current) {
            await updateAudioWithExtendedContent(progress.url);
          }

          setProgressiveComplete(true);
          clearInterval(interval);
          setPollingInterval(null);
        }

      } catch (error) {
        console.warn('🚨 Progressive monitoring error:', error);
      }
    }, 2000);

    setPollingInterval(interval);
  }, [currentAudio, pollingInterval]);

  // Update audio with extended content (minimally disruptive)
  const updateAudioWithExtendedContent = useCallback(async (freshUrl: string) => {
    if (!audioRef.current || !freshUrl) return;

    try {
      const currentTime = audioRef.current.currentTime;
      const wasPlaying = !audioRef.current.paused;
      const originalDuration = audioRef.current.duration;

      console.log('🔄 Refreshing audio with extended content...');

      if (wasPlaying) {
        audioRef.current.pause();
      }

      // Update URL with cache busting
      const separator = freshUrl.includes('?') ? '&' : '?';
      const optimizedUrl = freshUrl + separator + 'refresh=' + Date.now();

      audioRef.current.src = optimizedUrl;
      audioRef.current.currentTime = currentTime;

      if (wasPlaying) {
        audioRef.current.play().catch(error => {
          console.warn('⚠️ Could not resume playback:', error);
        });
      }

      // Update duration in background
      const handleMetadataUpdate = () => {
        if (audioRef.current && audioRef.current.duration > originalDuration) {
          console.log(`📈 Duration extended: ${audioRef.current.duration?.toFixed(2)}s`);
          setDuration(audioRef.current.duration);
        }
        audioRef.current?.removeEventListener('loadedmetadata', handleMetadataUpdate);
      };

      audioRef.current.addEventListener('loadedmetadata', handleMetadataUpdate);

    } catch (error) {
      console.error('❌ Failed to refresh audio:', error);
    }
  }, []);

  // Set up audio element when URL changes
  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.load();
    }
  }, [audioUrl]);

  // Audio element event listeners
  useEffect(() => {
    const audioElement = audioRef.current;
    if (!audioElement) return;

    const handleLoadedMetadata = () => {
      setDuration(audioElement.duration);
      setAudioLoading(false);
      console.log('✅ Audio metadata loaded - duration:', audioElement.duration?.toFixed(2) + 's');
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audioElement.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
    };

    const handleCanPlay = () => {
      setAudioLoading(false);
    };

    const handleError = () => {
      console.error('❌ Audio playback error');
      setAudioLoading(false);
    };

    audioElement.addEventListener('loadedmetadata', handleLoadedMetadata);
    audioElement.addEventListener('timeupdate', handleTimeUpdate);
    audioElement.addEventListener('ended', handleEnded);
    audioElement.addEventListener('canplay', handleCanPlay);
    audioElement.addEventListener('error', handleError);

    return () => {
      audioElement.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audioElement.removeEventListener('timeupdate', handleTimeUpdate);
      audioElement.removeEventListener('ended', handleEnded);
      audioElement.removeEventListener('canplay', handleCanPlay);
      audioElement.removeEventListener('error', handleError);
    };
  }, [audioUrl]);

  const contextValue: AudioContextType = {
    audioRef,
    currentAudio,
    currentTitle,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    playbackSpeed,
    isProgressive,
    progressiveComplete,
    audioUrl,
    audioLoading,
    setCurrentAudio,
    play,
    pause,
    seek,
    setVolume,
    toggleMute,
    setPlaybackSpeed,
    skipBack,
    skipForward,
    setIsPlaying,
    setCurrentTime,
    setDuration
  };

  return (
    <AudioContext.Provider value={contextValue}>
      {/* Hidden audio element for progressive streaming */}
      <audio ref={audioRef} preload="metadata" style={{ display: 'none' }} />
      {children}
    </AudioContext.Provider>
  );
};