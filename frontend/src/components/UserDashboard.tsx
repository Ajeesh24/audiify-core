import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock, User, LogOut, Play, Download, ExternalLink } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import audifyApi from '../services/api';

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
    storage: 's3' | 'local';
  } | null;
}

interface UserDashboardProps {
  onSignOut: () => void;
}

export const UserDashboard: React.FC<UserDashboardProps> = ({ onSignOut }) => {
  const { user, signOut } = useAuth();
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastKey, setLastKey] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const loadArticles = async (reset = false) => {
    try {
      setLoading(true);
      const response = await audifyApi.getMyArticles(reset ? null : lastKey);

      if (reset) {
        setArticles(response.articles);
      } else {
        setArticles(prev => [...prev, ...response.articles]);
      }

      setLastKey(response.pagination.last_key);
      setHasMore(response.pagination.has_more);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load articles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArticles(true);
  }, []);

  const handleSignOut = async () => {
    try {
      await signOut();
      onSignOut();
    } catch (err) {
      console.error('Sign out failed:', err);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const playAudio = (audioId: string) => {
    const audioUrl = audifyApi.getAudioStreamUrl(audioId);
    const audio = new Audio(audioUrl);
    audio.play().catch(err => {
      console.error('Failed to play audio:', err);
      setError('Failed to play audio. Please try again.');
    });
  };

  if (loading && articles.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your articles...</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-4xl mx-auto"
    >
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
              <User className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Welcome back, {user?.name || user?.email?.split('@')[0]}!
              </h1>
              <p className="text-gray-600">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Articles List */}
      <div className="bg-white rounded-2xl shadow-lg">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Your Articles</h2>
          <p className="text-gray-600">
            {articles.length} article{articles.length !== 1 ? 's' : ''} converted to audio
          </p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border-l-4 border-red-500 text-red-700">
            {error}
          </div>
        )}

        <div className="divide-y divide-gray-200">
          {articles.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-gray-400 mb-4">
                <Clock size={48} className="mx-auto" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No articles yet
              </h3>
              <p className="text-gray-600">
                Start by converting your first article to audio!
              </p>
            </div>
          ) : (
            articles.map((article) => (
              <motion.div
                key={article.job_id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-6 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      {article.title || 'Untitled Article'}
                    </h3>

                    <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                      <span>{formatDate(article.created_at)}</span>
                      <span>•</span>
                      <span>{article.word_count.toLocaleString()} words</span>
                      <span>•</span>
                      <span>{article.estimated_reading_time} min read</span>
                      <span>•</span>
                      <span className="capitalize">{article.mode}</span>
                      {article.audio && (
                        <>
                          <span>•</span>
                          <span>{formatFileSize(article.audio.size)}</span>
                        </>
                      )}
                    </div>

                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-700 text-sm flex items-center space-x-1"
                    >
                      <span className="truncate max-w-md">{article.url}</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>

                  {article.audio && (
                    <div className="flex items-center space-x-2 ml-4">
                      <button
                        onClick={() => playAudio(article.audio!.audio_id)}
                        className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <Play size={16} />
                        <span>Play</span>
                      </button>
                      <a
                        href={audifyApi.getAudioStreamUrl(article.audio.audio_id)}
                        download
                        className="flex items-center space-x-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <Download size={16} />
                        <span>Download</span>
                      </a>
                    </div>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </div>

        {hasMore && (
          <div className="p-6 border-t border-gray-200">
            <button
              onClick={() => loadArticles(false)}
              disabled={loading}
              className="w-full py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                  <span>Loading...</span>
                </div>
              ) : (
                'Load More Articles'
              )}
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
};