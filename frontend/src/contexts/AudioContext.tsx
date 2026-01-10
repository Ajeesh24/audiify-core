import React, { createContext, useContext, useState, useRef, useCallback } from 'react';
import { AudioResponse } from '@/services/api';

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

  // Actions
  setCurrentAudio: (audio: AudioResponse | null, title?: string) => void;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;

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

  const [currentAudio, setCurrentAudioState] = useState<AudioResponse | null>(null);
  const [currentTitle, setCurrentTitle] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  const setCurrentAudio = useCallback((audio: AudioResponse | null, title?: string) => {
    setCurrentAudioState(audio);
    setCurrentTitle(title || null);
    if (!audio) {
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(0);
    }
  }, []);

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

  const contextValue: AudioContextType = {
    audioRef,
    currentAudio,
    currentTitle,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    setCurrentAudio,
    play,
    pause,
    seek,
    setVolume,
    toggleMute,
    setIsPlaying,
    setCurrentTime,
    setDuration
  };

  return (
    <AudioContext.Provider value={contextValue}>
      {children}
    </AudioContext.Provider>
  );
};