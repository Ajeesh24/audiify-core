import { Button } from './ui/button';
import { Play, Pause, Sparkles, Clock } from 'lucide-react';
import { motion } from 'framer-motion';

interface CompactAudioCardProps {
  id: string;
  title: string;
  subtitle?: string;
  duration?: number;
  date?: string;
  status?: 'empty' | 'generating' | 'ready' | 'error';
  icon?: string;
  type: 'brief' | 'article' | 'personal';
  isAuthenticated: boolean;
  onPlay: (id: string) => void;
  onAuthRequired?: (trigger: { type: string; id: string }) => void;
  isDarkMode?: boolean;
}

const typeConfig = {
  brief: {
    emptyText: 'Coming Today',
    readyText: 'Ready',
    generatingText: 'Generating',
    errorText: 'Error'
  },
  article: {
    emptyText: 'No Audio',
    readyText: 'Available',
    generatingText: 'Processing',
    errorText: 'Failed'
  },
  personal: {
    emptyText: 'Create Audio',
    readyText: 'Ready',
    generatingText: 'Processing',
    errorText: 'Failed'
  }
};


const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export default function CompactAudioCard({
  id,
  title,
  subtitle,
  duration,
  date,
  status = 'empty',
  icon = '🎵',
  type,
  isAuthenticated,
  onPlay,
  onAuthRequired,
  isDarkMode = true
}: CompactAudioCardProps) {
  const config = typeConfig[type];

  // OpenAI Academy style gradients - clean and modern
  const getOpenAIGradient = (type: string, id: string) => {
    // Create unique gradient based on content type and ID for variety
    const seed = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const variation = seed % 8;

    // OpenAI Academy inspired gradients - softer, more sophisticated
    const academyGradients = [
      // Pink/Blue (Stories style)
      'from-pink-300 via-pink-200 to-blue-300',
      // Teal (Non-Profit style)
      'from-teal-400 to-teal-300',
      // Purple (Education style)
      'from-purple-500 to-purple-400',
      // Coral/Blue (Small Business style)
      'from-orange-300 via-pink-200 to-blue-400',
      // Orange/Purple gradient
      'from-orange-400 via-pink-300 to-purple-400',
      // Green gradient
      'from-emerald-500 to-teal-400',
      // Yellow/Blue gradient
      'from-yellow-300 via-orange-200 to-blue-300',
      // Purple/Blue gradient
      'from-purple-400 via-indigo-300 to-blue-400'
    ];

    return academyGradients[variation];
  };

  const academyGradient = getOpenAIGradient(type, id);

  const handlePlayClick = () => {
    // Allow clicking on "Create New Audio" card (id: 'create-new') even if empty status
    if (status !== 'ready' && id !== 'create-new') return;

    if (isAuthenticated) {
      onPlay(id);
    } else {
      onAuthRequired?.({ type: 'play_audio', id });
    }
  };

  const getStatusInfo = () => {
    switch (status) {
      case 'empty':
        return {
          badge: config.emptyText,
          badgeColor: 'bg-slate-600/80 text-slate-300',
          playable: id === 'create-new' // Make "Create New Audio" card clickable
        };
      case 'generating':
        return {
          badge: config.generatingText,
          badgeColor: 'bg-orange-500/80 text-white',
          playable: false
        };
      case 'ready':
        return {
          badge: config.readyText,
          badgeColor: 'bg-green-500/80 text-white',
          playable: true
        };
      case 'error':
        return {
          badge: config.errorText,
          badgeColor: 'bg-red-500/80 text-white',
          playable: false
        };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className="group cursor-pointer flex-shrink-0 w-56 sm:w-64"
      onClick={handlePlayClick}
    >
      {/* OpenAI Academy Style Card */}
      <div className={`
        relative overflow-hidden rounded-xl transition-all duration-300
        ${isDarkMode
          ? 'bg-slate-800/50 shadow-lg shadow-slate-900/20'
          : 'bg-white shadow-lg shadow-slate-900/10'
        }
        hover:shadow-xl hover:shadow-slate-900/20 border border-white/10
      `}>

        {/* Main Gradient Area - OpenAI Academy Style */}
        <div className={`
          relative h-36 bg-gradient-to-br ${academyGradient}
          flex items-center justify-center group-hover:scale-105 transition-transform duration-300
        `}>

          {/* Status Badge - Minimal and Clean */}
          {status !== 'ready' && (
            <div className="absolute top-4 right-4">
              <span className={`
                px-3 py-1 text-xs font-medium rounded-full backdrop-blur-sm
                ${status === 'generating'
                  ? 'bg-white/90 text-slate-900'
                  : status === 'error'
                    ? 'bg-red-500/90 text-white'
                    : 'bg-white/80 text-slate-700'
                }
              `}>
                {statusInfo.badge}
              </span>
            </div>
          )}

          {/* Play Button - Appears on Hover */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileHover={{ opacity: 1, scale: 1 }}
            className="opacity-0 group-hover:opacity-100 transition-all duration-300"
          >
            <Button
              onClick={(e) => {
                e.stopPropagation();
                handlePlayClick();
              }}
              disabled={!statusInfo.playable}
              className={`
                w-14 h-14 rounded-full backdrop-blur-md transition-all duration-300
                ${statusInfo.playable
                  ? 'bg-white/90 hover:bg-white text-slate-900 hover:scale-110 shadow-lg'
                  : 'bg-slate-500/50 text-slate-300 cursor-not-allowed'
                }
              `}
            >
              {status === 'generating' ? (
                <Sparkles className="w-5 h-5 animate-spin" />
              ) : (
                <Play className="w-5 h-5 fill-current ml-0.5" />
              )}
            </Button>
          </motion.div>

          {/* Loading Progress Bar for Generating Status */}
          {status === 'generating' && (
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
              <motion.div
                className="h-full bg-white/60"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              />
            </div>
          )}
        </div>

        {/* Content Area - OpenAI Academy Typography */}
        <div className="p-4 space-y-2">
          {/* Title - Academy Style Typography */}
          <h3 className={`
            text-base font-semibold leading-snug line-clamp-2
            ${isDarkMode ? 'text-white' : 'text-slate-900'}
            font-['Inter']
          `}>
            {title}
          </h3>

          {/* Subtitle/Description - Optional */}
          {subtitle && (
            <p className={`
              text-sm line-clamp-1
              ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}
            `}>
              {subtitle}
            </p>
          )}

          {/* Metadata - Duration or Date */}
          <div className="flex items-center justify-between pt-2">
            {status === 'ready' && duration ? (
              <div className={`flex items-center gap-2 text-sm ${
                isDarkMode ? 'text-slate-500' : 'text-slate-500'
              }`}>
                <Clock className="w-4 h-4" />
                <span>{formatDuration(duration)}</span>
              </div>
            ) : date ? (
              <p className={`text-sm ${
                isDarkMode ? 'text-slate-500' : 'text-slate-500'
              }`}>
                {new Date(date).toLocaleDateString()}
              </p>
            ) : (
              <div />
            )}

            {/* Type Badge - Subtle */}
            <span className={`
              text-xs px-2 py-1 rounded-md font-medium uppercase tracking-wide
              ${type === 'brief'
                ? isDarkMode ? 'bg-blue-500/10 text-blue-400' : 'bg-blue-50 text-blue-600'
                : type === 'personal'
                  ? isDarkMode ? 'bg-purple-500/10 text-purple-400' : 'bg-purple-50 text-purple-600'
                  : isDarkMode ? 'bg-green-500/10 text-green-400' : 'bg-green-50 text-green-600'
              }
            `}>
              {type === 'brief' ? 'Brief' : type === 'personal' ? 'Personal' : 'Article'}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}