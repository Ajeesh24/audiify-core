import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Play, Clock, ExternalLink, Calendar, Bookmark, Volume2 } from 'lucide-react';
import { audifyApi, AudioResponse } from '@/services/api';
import AudioPlayer from './AudioPlayer';

interface Article {
  job_id: string;
  created_at: string;
  updated_at: string;
  url: string;
  title: string;
  word_count: number;
  estimated_reading_time: number;
  mode: 'full' | 'summary';
  audio: {
    audio_id: string;
    size: number;
    storage: string;
    url?: string;
  } | null;
}

interface RecentArticlesProps {
  refreshTrigger?: number; // Prop to trigger refresh when new article is added
}

export default function RecentArticles({ refreshTrigger }: RecentArticlesProps) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [playingAudio, setPlayingAudio] = useState<{
    audioId: string;
    audio: AudioResponse;
    title: string;
  } | null>(null);

  const fetchArticles = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await audifyApi.getMyArticles();
      // Sort articles by created_at in descending order (newest first)
      const sortedArticles = response.articles.sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setArticles(sortedArticles);
    } catch (err) {
      console.error('Failed to fetch articles:', err);
      setError('Failed to load articles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArticles();
  }, [refreshTrigger]); // Refresh when new articles are added

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const handlePlayAudio = (article: Article) => {
    if (!article.audio) return;

    // Create AudioResponse object for the player
    const audioResponse: AudioResponse = {
      audio_id: article.audio.audio_id,
      url: article.audio.url || undefined,
      size: article.audio.size,
      storage: article.audio.storage as 's3' | 'local',
      s3_key: undefined,
      duration: undefined,
      expires_at: undefined
    };

    setPlayingAudio({
      audioId: article.audio.audio_id,
      audio: audioResponse,
      title: article.title
    });
  };

  const closeAudioPlayer = () => {
    setPlayingAudio(null);
  };

  if (loading && articles.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full mt-8"
      >
        <Card className="bg-slate-900/50 border-slate-800/50 backdrop-blur-xl shadow-2xl">
          <CardContent className="p-8">
            <div className="flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mr-3"></div>
              <p className="text-slate-300">Loading your articles...</p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="w-full mt-8"
      >
        <Card className="bg-slate-900/50 border-slate-800/50 backdrop-blur-xl shadow-2xl">
          <CardContent className="p-4 sm:p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-4 sm:mb-6">
              <div className="flex items-center space-x-2 sm:space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-r from-purple-500 to-violet-500 flex items-center justify-center">
                  <Bookmark className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-xl font-semibold text-white">Recent Articles</h2>
                  <p className="text-slate-400 text-xs sm:text-sm">
                    {articles.length} article{articles.length !== 1 ? 's' : ''} converted to audio
                  </p>
                </div>
              </div>
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mb-4 p-4 bg-red-900/20 border border-red-800/50 rounded-lg"
              >
                <p className="text-red-400">{error}</p>
              </motion.div>
            )}

            {/* Articles List */}
            <div className="space-y-3 sm:space-y-4">
              {articles.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-8 sm:py-12"
                >
                  <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
                    <Volume2 className="w-6 h-6 sm:w-8 sm:h-8 text-slate-500" />
                  </div>
                  <h3 className="text-base sm:text-lg font-medium text-slate-300 mb-2">
                    No articles yet
                  </h3>
                  <p className="text-sm sm:text-base text-slate-500">
                    Convert your first article above to get started!
                  </p>
                </motion.div>
              ) : (
                <AnimatePresence>
                  {articles.map((article, index) => (
                    <motion.div
                      key={article.job_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="p-3 sm:p-4 lg:p-5 rounded-xl bg-slate-800/30 border border-slate-700/50 hover:bg-slate-800/50 transition-all duration-300"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4">
                        <div className="flex-1 min-w-0 space-y-2 sm:space-y-3">
                          {/* Title */}
                          <h3 className="text-base sm:text-lg font-medium text-white leading-tight line-clamp-2">
                            {article.title || 'Untitled Article'}
                          </h3>

                          {/* Meta info - Stack on mobile, inline on larger screens */}
                          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-xs sm:text-sm text-slate-400">
                            <div className="flex items-center flex-wrap gap-2 sm:gap-4">
                              <div className="flex items-center space-x-1 whitespace-nowrap">
                                <Calendar className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" />
                                <span>{formatDate(article.created_at)}</span>
                              </div>
                              <span className="hidden sm:inline">•</span>
                              <div className="flex items-center space-x-1 whitespace-nowrap">
                                <Clock className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" />
                                <span>{article.estimated_reading_time} min</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 sm:gap-4">
                              <span className="hidden sm:inline">•</span>
                              <span className="capitalize px-2 py-1 rounded-full bg-purple-500/20 text-purple-300 text-xs whitespace-nowrap">
                                {article.mode}
                              </span>
                            </div>
                          </div>

                          {/* URL - Better mobile handling */}
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-purple-400 hover:text-purple-300 text-xs sm:text-sm flex items-start sm:items-center space-x-1 group break-all sm:break-normal line-clamp-1 sm:line-clamp-none"
                          >
                            <span className="truncate flex-1 min-w-0">{article.url}</span>
                            <ExternalLink className="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5 sm:mt-0" />
                          </a>
                        </div>

                        {/* Play Button - Full width on mobile, auto on desktop */}
                        {article.audio && (
                          <div className="w-full sm:w-auto">
                            <Button
                              onClick={() => handlePlayAudio(article)}
                              variant="gradient"
                              size="sm"
                              className="w-full sm:w-auto flex items-center justify-center space-x-2 py-2.5 sm:py-2 px-4 sm:px-3 text-sm font-medium min-w-[80px] touch-manipulation"
                            >
                              <Play className="w-4 h-4 flex-shrink-0" />
                              <span>Play</span>
                            </Button>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Audio Player Modal */}
      <AnimatePresence>
        {playingAudio && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={closeAudioPlayer}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-2xl relative"
            >
              {/* Close button */}
              <button
                onClick={closeAudioPlayer}
                className="absolute -top-10 right-0 text-white hover:text-gray-300 transition-colors"
              >
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              <AudioPlayer
                audio={playingAudio.audio}
                title={playingAudio.title}
                mode="full"
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}