import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Headphones, Sparkles, FileText, Link2, Volume2, Play, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import HorizontalSection from '@/components/HorizontalSection';
import StickyFooterPlayer from '@/components/StickyFooterPlayer';
import CreateAudioModal from '@/components/CreateAudioModal';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { AudioProvider, useAudioContext } from '@/contexts/AudioContext';
import { AuthForm } from '@/components/AuthForm';
import { audifyApi, setAuthTokenGetter, type ArticleProcessRequest, type ProcessArticleResponse, type ArticleContent, type AudioResponse } from '@/services/api';

function AuthenticatedApp() {
  const { user, loading, isAuthenticated, getAccessToken, signOut, isConfigured, isDevelopment } = useAuth();
  const audioContext = useAudioContext();
  const [url, setUrl] = useState('');
  const [mode, setMode] = useState<'full' | 'summary'>('full');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Recent articles state
  const [recentArticles, setRecentArticles] = useState<any[]>([]);
  const [loadingArticles, setLoadingArticles] = useState(true);

  // Create Audio Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [modalProcessing, setModalProcessing] = useState(false);

  // System theme detection
  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return true; // Default to dark mode
  });

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e: MediaQueryListEvent) => setIsDarkMode(e.matches);

      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, []);

  // Set up auth token getter for API requests
  useEffect(() => {
    if (isConfigured) {
      setAuthTokenGetter(getAccessToken);
    }
  }, [getAccessToken, isConfigured]);

  // Fetch recent articles
  const fetchRecentArticles = async () => {
    try {
      setLoadingArticles(true);
      const response = await audifyApi.getMyArticles();
      // Sort articles by created_at in descending order (newest first)
      const sortedArticles = response.articles.sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setRecentArticles(sortedArticles);
    } catch (err) {
      console.error('Failed to fetch articles:', err);
      setRecentArticles([]);
    } finally {
      setLoadingArticles(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && isConfigured) {
      fetchRecentArticles();
    }
  }, [isAuthenticated, isConfigured, refreshTrigger]);

  // Convert recent articles to compact card format
  const convertToCompactCards = (articles: any[]) => {
    return articles.map((article) => {
      let status: 'empty' | 'generating' | 'ready' | 'error';

      // Determine status based on article state
      if (article.status === 'processing') {
        status = 'generating';
      } else if (article.status === 'failed') {
        status = 'error';
      } else if (article.audio) {
        status = 'ready';
      } else {
        status = 'error';
      }

      return {
        id: article.job_id,
        title: article.title || 'Untitled Article',
        subtitle: new Date(article.created_at).toLocaleDateString(),
        duration: article.audio?.duration || (article.estimated_reading_time ? article.estimated_reading_time * 60 : undefined),
        status,
        icon: 'article',
        type: 'personal' as const,
        date: article.created_at,
        articleData: article // Store original data for playback
      };
    });
  };

  // Mock data for horizontal sections
  const techBriefItems = [
    {
      id: 'tech-today',
      title: 'Today\'s Tech Brief',
      subtitle: 'Latest tech news',
      status: 'empty' as const,
      icon: 'tech',
      type: 'brief' as const,
      date: new Date().toISOString()
    },
    {
      id: 'tech-yesterday',
      title: 'Yesterday\'s Brief',
      subtitle: 'Tech roundup',
      status: 'ready' as const,
      duration: 420,
      icon: 'tech',
      type: 'brief' as const,
      date: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 'tech-jan8',
      title: 'Jan 8 Brief',
      subtitle: 'CES highlights',
      status: 'ready' as const,
      duration: 380,
      icon: 'tech',
      type: 'brief' as const,
      date: '2026-01-08'
    }
  ];

  const aimlBriefItems = [
    {
      id: 'aiml-today',
      title: 'Today\'s AI Brief',
      subtitle: 'AI & ML updates',
      status: 'empty' as const,
      icon: 'ai',
      type: 'brief' as const,
      date: new Date().toISOString()
    },
    {
      id: 'aiml-yesterday',
      title: 'Yesterday\'s AI',
      subtitle: 'Model releases',
      status: 'ready' as const,
      duration: 310,
      icon: 'ai',
      type: 'brief' as const,
      date: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 'aiml-jan8',
      title: 'Jan 8 AI Brief',
      subtitle: 'OpenAI updates',
      status: 'ready' as const,
      duration: 290,
      icon: 'ai',
      type: 'brief' as const,
      date: '2026-01-08'
    }
  ];

  const devopsBriefItems = [
    {
      id: 'devops-today',
      title: 'Today\'s DevOps',
      subtitle: 'Platform updates',
      status: 'empty' as const,
      icon: 'devops',
      type: 'brief' as const,
      date: new Date().toISOString()
    },
    {
      id: 'devops-yesterday',
      title: 'Yesterday\'s Platform',
      subtitle: 'Cloud updates',
      status: 'ready' as const,
      duration: 240,
      icon: 'devops',
      type: 'brief' as const,
      date: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 'devops-jan8',
      title: 'Jan 8 DevOps',
      subtitle: 'Kubernetes news',
      status: 'ready' as const,
      duration: 200,
      icon: 'devops',
      type: 'brief' as const,
      date: '2026-01-08'
    }
  ];

  const yourAudioItems = [
    {
      id: 'create-new',
      title: 'Create New Audio',
      subtitle: 'From article URL',
      status: 'empty' as const,
      icon: 'create',
      type: 'personal' as const
    },
    ...convertToCompactCards(recentArticles)
  ];

  const trendingArticleItems = [
    {
      id: 'trending-1',
      title: 'Future of AI in 2026',
      subtitle: 'TechCrunch',
      status: 'ready' as const,
      duration: 600,
      icon: 'trending',
      type: 'article' as const,
      date: new Date().toISOString()
    },
    {
      id: 'trending-2',
      title: 'Meta\'s New VR Headset',
      subtitle: 'The Verge',
      status: 'ready' as const,
      duration: 450,
      icon: 'trending',
      type: 'article' as const,
      date: new Date().toISOString()
    },
    {
      id: 'trending-3',
      title: 'Electric Car Revolution',
      subtitle: 'Wired',
      status: 'generating' as const,
      icon: 'trending',
      type: 'article' as const,
      date: new Date().toISOString()
    }
  ];

  // Handler functions for audio cards
  const handleAudioPlay = async (audioId: string) => {
    // Handle different types of audio
    if (audioId === 'create-new') {
      // Open the create audio modal
      setShowCreateModal(true);
      return;
    }

    // Check if this is a recent article
    const recentArticle = recentArticles.find(article => article.job_id === audioId);
    if (recentArticle && recentArticle.audio) {
      try {
        // If this audio is already loaded and playing, just toggle play/pause
        if (audioContext.currentAudio?.audio_id === recentArticle.audio.audio_id) {
          if (audioContext.isPlaying) {
            audioContext.pause();
          } else {
            await audioContext.play();
          }
          return;
        }

        console.log('🎵 Loading existing audio for:', recentArticle.title);

        // Create AudioResponse object
        const audioResponse: AudioResponse = {
          audio_id: recentArticle.audio.audio_id,
          url: recentArticle.audio.url || undefined,
          size: recentArticle.audio.size,
          storage: recentArticle.audio.storage,
          s3_key: undefined,
          duration: undefined,
          expires_at: undefined
        };

        // Get the actual audio URL if needed
        let audioUrl = audioResponse.url;
        if (!audioUrl || (!audioUrl.startsWith('https://') || audioUrl.includes('execute-api'))) {
          console.log('🔐 Fetching presigned URL for audio ID:', audioResponse.audio_id);
          audioUrl = await audifyApi.getAudioPresignedUrl(audioResponse.audio_id);
        }

        // Set up the audio context first (shows player immediately) - use progressive=false for existing audio
        audioContext.setCurrentAudio(audioResponse, recentArticle.title, false);

        // Load and play the audio
        if (audioContext.audioRef.current && audioUrl) {
          const audio = audioContext.audioRef.current;

          // Stop any current playback
          audio.pause();
          audio.currentTime = 0;

          // Simple event handlers - no duplicates
          const onLoadedData = () => {
            console.log('✅ Audio loaded, attempting to play');
            // Try to play immediately when loaded
            audio.play().then(() => {
              console.log('▶️ Audio started playing successfully');
            }).catch(error => {
              console.log('🎵 Autoplay prevented, user can click play button');
              // Don't set error state, just log it
            });
          };

          const onLoadedMetadata = () => {
            audioContext.setDuration(audio.duration);
          };

          const onTimeUpdate = () => {
            audioContext.setCurrentTime(audio.currentTime);
          };

          const onPlay = () => {
            audioContext.setIsPlaying(true);
          };

          const onPause = () => {
            audioContext.setIsPlaying(false);
          };

          const onEnded = () => {
            audioContext.setIsPlaying(false);
          };

          // Remove any existing listeners
          audio.removeEventListener('loadeddata', onLoadedData);
          audio.removeEventListener('loadedmetadata', onLoadedMetadata);
          audio.removeEventListener('timeupdate', onTimeUpdate);
          audio.removeEventListener('play', onPlay);
          audio.removeEventListener('pause', onPause);
          audio.removeEventListener('ended', onEnded);

          // Add event listeners
          audio.addEventListener('loadeddata', onLoadedData);
          audio.addEventListener('loadedmetadata', onLoadedMetadata);
          audio.addEventListener('timeupdate', onTimeUpdate);
          audio.addEventListener('play', onPlay);
          audio.addEventListener('pause', onPause);
          audio.addEventListener('ended', onEnded);

          // Load the audio (this is just loading an existing S3 file)
          console.log('📁 Loading audio from S3...');
          audio.src = audioUrl;
          audio.load();
        }

        return;
      } catch (error) {
        console.error('❌ Failed to load audio:', error);
      }
    }

    // TODO: Implement audio playback for briefings and other articles
    console.log('Playing audio:', audioId);
  };

  const handleAuthRequired = (trigger: { type: string; id: string }) => {
    // This shouldn't happen since we're already authenticated, but handle it
    console.log('Auth required for:', trigger);
  };

  // Handle modal submit for creating new audio
  const handleCreateAudioSubmit = async (url: string, mode: 'full' | 'summary') => {
    try {
      setModalProcessing(true);
      setError(null);

      // Create processing request
      const request: ArticleProcessRequest = {
        url,
        mode
      };

      console.log('🚀 Starting article processing from modal:', request);

      // Start processing
      const response = await audifyApi.processArticle(request);
      console.log('✅ Article processing started:', response);
      console.log('🔍 Response structure - audio:', response.audio, 'article:', response.article);

      // Handle the actual API response structure
      if (!response.success || !response.article) {
        throw new Error('Failed to process article');
      }

      // Use a simple timestamp-based ID for now
      const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Update state with processing job
      setCurrentJobId(jobId);
      setArticleContent(response.article);

      // Create audio item - use the same structure as ProgressiveAudioPlayer expects
      const audioItem = {
        job_id: jobId,
        title: response.article.title || 'New Audio Article',
        url: response.article.url || url,
        status: 'completed', // Mark as completed since we have audio
        created_at: new Date().toISOString(),
        content: response.article,
        audio: response.audio, // This should have the audio_id and other properties
        mode
      };

      // Add to recent articles at the beginning
      setRecentArticles(prev => [audioItem, ...prev]);

      // Close modal immediately
      setModalProcessing(false);
      setShowCreateModal(false);

      // Start playing audio using progressive streaming for new articles
      if (response.audio) {
        console.log('🎵 Starting progressive audio playback with:', response.audio);
        console.log('🎵 Audio structure:', {
          audio_id: response.audio.audio_id,
          url: response.audio.url,
          s3_key: response.audio.s3_key
        });

        // Use progressive flag for new audio from modal
        try {
          // Set the audio context with progressive=true for new audio
          audioContext.setCurrentAudio(response.audio, response.article.title || 'New Audio', true);
          console.log('🎵 Progressive audio context set, attempting to play...');
          audioContext.play();
          console.log('🎵 Progressive play command sent to audio context');
        } catch (playError) {
          console.error('❌ Failed to start progressive audio playback:', playError);
        }
      } else {
        console.log('⚠️ No audio object in response');
      }

      // Clear current job
      setCurrentJobId(null);

    } catch (error) {
      console.error('❌ Failed to start processing:', error);
      setError('Failed to start processing. Please try again.');
      setModalProcessing(false);
    }
  };

  // Poll job status and handle audio availability
  const pollJobStatus = (jobId: string) => {
    const checkStatus = async () => {
      try {
        const status = await audifyApi.getJobStatus(jobId);
        console.log('📊 Job status:', status);

        if (status.status === 'completed' && status.audio) {
          // Audio is ready! Close modal and start playing
          setModalProcessing(false);
          setShowCreateModal(false);

          // Update the article in recent articles list
          setRecentArticles(prev =>
            prev.map(article =>
              article.job_id === jobId
                ? { ...article, audio: status.audio, status: 'completed' }
                : article
            )
          );

          // Start playing in footer
          console.log('🎵 Starting audio playback in footer');
          const articleTitle = recentArticles.find(a => a.job_id === jobId)?.title || 'New Audio';
          audioContext.setCurrentAudio(status.audio, articleTitle);
          audioContext.play();

          // Clear current job
          setCurrentJobId(null);

        } else if (status.status === 'failed') {
          // Failed
          setModalProcessing(false);
          setError('Failed to generate audio. Please try again.');
          setCurrentJobId(null);

          // Update article status
          setRecentArticles(prev =>
            prev.map(article =>
              article.job_id === jobId
                ? { ...article, status: 'failed' }
                : article
            )
          );

        } else {
          // Still processing - check if first chunk is available
          if (status.audio && !audioContext.currentAudio) {
            // First chunk available! Close modal and start playing
            setModalProcessing(false);
            setShowCreateModal(false);

            // Update the article with partial audio
            setRecentArticles(prev =>
              prev.map(article =>
                article.job_id === jobId
                  ? { ...article, audio: status.audio, status: 'ready' }
                  : article
              )
            );

            // Start progressive playback in footer
            console.log('🎵 Starting progressive audio playback in footer');
            const articleTitle = recentArticles.find(a => a.job_id === jobId)?.title || 'New Audio';
            audioContext.setCurrentAudio(status.audio, articleTitle);
            audioContext.play();
          }

          // Continue polling
          setTimeout(checkStatus, 2000);
        }
      } catch (error) {
        console.error('❌ Error checking job status:', error);
        // Continue polling despite errors
        setTimeout(checkStatus, 5000);
      }
    };

    checkStatus();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show development mode message when Cognito isn't configured
  if (!isConfigured && isDevelopment) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center p-4">
        {/* Ambient background effects */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10 w-full max-w-2xl text-center">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl shadow-lg shadow-purple-500/25">
                <Headphones className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-violet-300 bg-clip-text text-transparent">
                Audifyy
              </h1>
            </div>
          </motion.div>

          {/* Development Mode Message */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-slate-900/50 border border-slate-800/50 backdrop-blur-xl rounded-2xl p-8 shadow-2xl"
          >
            <div className="text-center space-y-4">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-yellow-500/20 rounded-full mb-4">
                <Sparkles className="w-8 h-8 text-yellow-400" />
              </div>

              <h2 className="text-2xl font-bold text-white mb-2">
                Development Mode
              </h2>

              <p className="text-slate-400 text-lg mb-6">
                Cognito authentication is not configured. This is expected during local development.
              </p>

              <div className="bg-slate-800/50 rounded-xl p-6 text-left space-y-3">
                <h3 className="font-semibold text-white mb-3">To enable authentication:</h3>
                <div className="space-y-2 text-sm text-slate-300">
                  <p>1. <span className="font-medium text-white">Deploy the infrastructure:</span></p>
                  <code className="block bg-slate-700/50 px-3 py-2 rounded text-xs font-mono text-green-400">
                    git push origin main  # Triggers deployment
                  </code>

                  <p>2. <span className="font-medium text-white">Set up GitHub Secrets:</span></p>
                  <ul className="list-disc list-inside space-y-1 text-xs text-slate-400 ml-4">
                    <li>OPENAI_API_KEY</li>
                    <li>AWS_GITHUB_TRUST_ROLE</li>
                    <li>AWS_DEPLOYMENT_ROLE</li>
                  </ul>

                  <p>3. <span className="font-medium text-white">After deployment:</span> Authentication will work automatically!</p>
                </div>
              </div>

              <p className="text-slate-500 text-sm">
                For now, you can preview the UI design but authentication features are disabled.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center p-4">
        {/* Ambient background effects */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10 w-full max-w-md">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl shadow-lg shadow-purple-500/25">
                <Headphones className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-violet-300 bg-clip-text text-transparent">
                Audifyy
              </h1>
            </div>
            <p className="text-slate-400 text-lg">
              Transform articles into audio with AI
            </p>
          </motion.div>

          <AuthForm onSuccess={() => {}} />
        </div>
      </div>
    );
  }

  // Dynamic background based on system theme
  const getThemeBackground = () => {
    if (isDarkMode) {
      return 'min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950';
    } else {
      return 'min-h-screen bg-gradient-to-br from-slate-50 via-purple-50 to-slate-100';
    }
  };

  // Dynamic ambient effects based on theme
  const getAmbientEffects = () => {
    if (isDarkMode) {
      return (
        <>
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
        </>
      );
    } else {
      return (
        <>
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-300/20 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-300/20 rounded-full blur-3xl" />
        </>
      );
    }
  };

  return (
    <div className={`${getThemeBackground()} safe-area-all`}>
      {/* Ambient background effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        {getAmbientEffects()}
      </div>

      <div className="relative z-10 container mx-auto px-4 py-6 sm:py-8 max-w-4xl container-responsive">
        {/* Header with user info */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative mb-6 sm:mb-8"
        >
          <div className="flex items-center gap-3 sm:gap-4">
            {/* Modern Logo Design */}
            <div className="relative">
              <div className="p-3 sm:p-4 bg-gradient-to-br from-purple-500 via-violet-500 to-indigo-600 rounded-2xl sm:rounded-3xl shadow-lg shadow-purple-500/25 relative overflow-hidden">
                {/* Background Pattern */}
                <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent"></div>
                <div className="absolute top-0 right-0 w-8 h-8 bg-white/10 rounded-full -mr-4 -mt-4"></div>
                <div className="absolute bottom-0 left-0 w-6 h-6 bg-white/5 rounded-full -ml-3 -mb-3"></div>

                {/* Icon Stack */}
                <div className="relative flex items-center justify-center">
                  <Headphones className="w-6 h-6 sm:w-8 sm:h-8 text-white relative z-10" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Play className="w-3 h-3 sm:w-4 sm:h-4 text-purple-200 opacity-50 translate-x-0.5 translate-y-0.5" />
                  </div>
                </div>
              </div>

              {/* Animated Pulse Ring */}
              <div className="absolute inset-0 rounded-2xl sm:rounded-3xl border-2 border-purple-400/30 animate-pulse"></div>
              <div className="absolute inset-0 rounded-2xl sm:rounded-3xl bg-gradient-to-br from-purple-500/20 to-violet-500/20 blur-xl -z-10"></div>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h1 className={`text-2xl sm:text-3xl md:text-4xl font-bold bg-gradient-to-r ${
                  isDarkMode
                    ? 'from-white via-purple-200 to-violet-300'
                    : 'from-slate-800 via-purple-600 to-violet-700'
                } bg-clip-text text-transparent`}>
                  Audifyy
                </h1>
                <div className="hidden sm:flex items-center gap-1">
                  <Zap className="w-4 h-4 text-yellow-400 animate-pulse" />
                  <span className={`text-xs font-medium px-2 py-1 bg-purple-500/20 rounded-full ${
                    isDarkMode ? 'text-purple-300' : 'text-purple-700'
                  }`}>
                    AI-Powered
                  </span>
                </div>
              </div>
              <p className={`text-xs sm:text-sm flex items-center gap-2 ${
                isDarkMode ? 'text-slate-400' : 'text-slate-600'
              }`}>
                <span>Welcome back, {user?.name || user?.email?.split('@')[0]}!</span>
                <span className={`hidden sm:inline ${
                  isDarkMode ? 'text-slate-600' : 'text-slate-400'
                }`}>•</span>
                <span className={`hidden sm:inline text-xs ${
                  isDarkMode ? 'text-purple-300' : 'text-purple-600'
                }`}>Premium Experience</span>
              </p>
            </div>
          </div>

          {/* Sign Out - Absolutely positioned top right */}
          <div className="absolute top-0 right-0">
            <Button
              onClick={signOut}
              variant="outline"
              size="sm"
              className="bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 hover:text-white border-slate-600/40 hover:border-slate-500/60 text-xs px-3 py-1.5 touch-manipulation transition-all duration-200 backdrop-blur-sm"
            >
              Sign Out
            </Button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <p className={`text-lg leading-relaxed ${
            isDarkMode ? 'text-slate-400' : 'text-slate-600'
          }`}>
            Your daily dose of tech audio content
          </p>
        </motion.div>

        {/* Tech Brief Section */}
        <HorizontalSection
          title="Tech Brief"
          subtitle="Latest technology news and updates"
          items={techBriefItems}
          isAuthenticated={isAuthenticated}
          onPlay={handleAudioPlay}
          onAuthRequired={handleAuthRequired}
        />

        {/* AI/ML Brief Section */}
        <HorizontalSection
          title="AI/ML Brief"
          subtitle="Artificial intelligence and machine learning"
          items={aimlBriefItems}
          isAuthenticated={isAuthenticated}
          onPlay={handleAudioPlay}
          onAuthRequired={handleAuthRequired}
        />

        {/* DevOps/Platform Brief Section */}
        <HorizontalSection
          title="DevOps/Platform Brief"
          subtitle="Infrastructure, cloud, and development tools"
          items={devopsBriefItems}
          isAuthenticated={isAuthenticated}
          onPlay={handleAudioPlay}
          onAuthRequired={handleAuthRequired}
        />

        {/* Your Own Audios Section */}
        <HorizontalSection
          title="Your Own Audios"
          subtitle="Create and listen to your personal audio content"
          items={yourAudioItems}
          isAuthenticated={isAuthenticated}
          onPlay={handleAudioPlay}
          onAuthRequired={handleAuthRequired}
          showNavigationButtons={false}
        />

        {/* Trending Articles Section */}
        <HorizontalSection
          title="Trending Articles"
          subtitle="Popular articles converted to audio"
          items={trendingArticleItems}
          isAuthenticated={isAuthenticated}
          onPlay={handleAudioPlay}
          onAuthRequired={handleAuthRequired}
        />

        {/* Footer */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className={`text-center text-xs sm:text-sm mt-8 sm:mt-12 mb-20 leading-relaxed ${
            isDarkMode ? 'text-slate-600' : 'text-slate-400'
          }`}>
          Powered by AI • Secure authentication • Natural voice synthesis
        </motion.p>
      </div>

      {/* Hidden Audio Element for Shared Playback */}
      <audio
        ref={audioContext.audioRef}
        preload="metadata"
        style={{ display: 'none' }}
      />

      {/* Sticky Footer Audio Player */}
      <AnimatePresence>
        {audioContext.currentAudio && audioContext.currentTitle && (
          <StickyFooterPlayer
            audio={audioContext.currentAudio}
            title={audioContext.currentTitle}
            isPlaying={audioContext.isPlaying}
            currentTime={audioContext.currentTime}
            duration={audioContext.duration}
            volume={audioContext.volume}
            isMuted={audioContext.isMuted}
            playbackSpeed={audioContext.playbackSpeed}
            onPlay={audioContext.play}
            onPause={audioContext.pause}
            onSeek={audioContext.seek}
            onVolumeChange={audioContext.setVolume}
            onMuteToggle={audioContext.toggleMute}
            onSpeedChange={audioContext.setPlaybackSpeed}
            onSkipBack={audioContext.skipBack}
            onSkipForward={audioContext.skipForward}
          />
        )}
      </AnimatePresence>

      {/* Create Audio Modal */}
      <CreateAudioModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateAudioSubmit}
        isProcessing={modalProcessing}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AudioProvider>
        <AuthenticatedApp />
      </AudioProvider>
    </AuthProvider>
  );
}