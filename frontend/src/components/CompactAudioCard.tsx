import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Play, Sparkles, Clock } from 'lucide-react';
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
  onAuthRequired
}: CompactAudioCardProps) {
  const config = typeConfig[type];

  // Generate modern flowing gradients based on content type and ID
  const getModernGradient = (type: string, id: string) => {
    // Create unique gradient based on content type and ID for variety
    const seed = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const variation = seed % 8; // Increased to 8 different variations per type

    switch (type) {
      case 'brief':
        if (icon === 'tech') {
          // Tech Brief - Enhanced blue/purple/cyan variations with more diversity
          const techGradients = [
            'from-blue-400 via-purple-500 to-pink-500',
            'from-cyan-300 via-blue-500 to-indigo-600',
            'from-purple-400 via-blue-500 to-cyan-400',
            'from-pink-400 via-purple-500 to-blue-500',
            'from-indigo-400 via-cyan-500 to-teal-500',
            'from-blue-500 via-violet-500 to-purple-600',
            'from-sky-400 via-blue-600 to-indigo-700',
            'from-teal-400 via-blue-500 to-violet-600'
          ];
          return techGradients[variation];
        }
        if (icon === 'ai') {
          // AI Brief - Enhanced purple/orange/magenta variations
          const aiGradients = [
            'from-purple-500 via-pink-500 to-orange-400',
            'from-indigo-500 via-purple-500 to-pink-400',
            'from-violet-400 via-purple-500 to-rose-400',
            'from-purple-600 via-violet-500 to-pink-500',
            'from-fuchsia-500 via-purple-600 to-orange-500',
            'from-magenta-400 via-violet-500 to-amber-400',
            'from-purple-700 via-fuchsia-500 to-pink-600',
            'from-indigo-600 via-purple-600 to-rose-500'
          ];
          return aiGradients[variation];
        }
        if (icon === 'devops') {
          // DevOps Brief - Enhanced teal/green/emerald variations
          const devopsGradients = [
            'from-teal-400 via-green-500 to-blue-500',
            'from-emerald-400 via-teal-500 to-cyan-500',
            'from-green-400 via-teal-500 to-blue-400',
            'from-cyan-400 via-teal-500 to-green-500',
            'from-mint-400 via-emerald-500 to-teal-600',
            'from-green-500 via-cyan-500 to-blue-600',
            'from-teal-500 via-green-600 to-emerald-700',
            'from-cyan-500 via-teal-600 to-green-700'
          ];
          return devopsGradients[variation];
        }
        break;

      case 'personal':
        if (id === 'create-new') {
          // Create New - Special vibrant gradient
          return 'from-purple-500 via-pink-500 to-orange-400';
        }
        // User articles - Enhanced warm purple/blue/pink variations
        const personalGradients = [
          'from-purple-400 via-violet-500 to-blue-400',
          'from-indigo-400 via-purple-500 to-pink-400',
          'from-violet-400 via-purple-500 to-cyan-400',
          'from-blue-400 via-purple-500 to-rose-400',
          'from-fuchsia-400 via-violet-600 to-blue-500',
          'from-purple-500 via-indigo-500 to-cyan-500',
          'from-violet-500 via-purple-600 to-pink-500',
          'from-indigo-500 via-violet-500 to-rose-500'
        ];
        return personalGradients[variation];

      case 'article':
        // Trending articles - Much more varied colorful gradients
        const trendingGradients = [
          'from-pink-400 via-rose-500 to-orange-400',
          'from-cyan-400 via-teal-500 to-green-400',
          'from-yellow-400 via-orange-500 to-red-400',
          'from-green-400 via-emerald-500 to-teal-400',
          'from-amber-400 via-orange-600 to-red-500',
          'from-lime-400 via-green-500 to-emerald-600',
          'from-red-400 via-pink-500 to-purple-600',
          'from-orange-400 via-amber-500 to-yellow-600'
        ];
        return trendingGradients[variation];
    }

    // Enhanced fallback gradients for maximum variety
    const fallbackGradients = [
      'from-purple-500 via-pink-500 to-blue-500',
      'from-cyan-400 via-blue-500 to-purple-600',
      'from-green-400 via-teal-500 to-blue-500',
      'from-orange-400 via-red-500 to-pink-600',
      'from-indigo-500 via-purple-500 to-fuchsia-500',
      'from-teal-500 via-green-500 to-lime-500',
      'from-rose-400 via-pink-500 to-violet-600',
      'from-amber-400 via-orange-500 to-red-600'
    ];
    return fallbackGradients[variation];
  };

  const modernGradient = getModernGradient(type, id);

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
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className="group cursor-pointer flex-shrink-0 w-36 sm:w-40"
    >
      <Card className="
        bg-slate-900/60 border-slate-800/40 hover:bg-slate-800/60
        transition-all duration-300 overflow-hidden
        backdrop-blur-sm hover:border-slate-700/60
      ">
        <CardContent className="p-0">
          {/* Modern Liquid Glass Cover Art */}
          <div className="relative aspect-square overflow-hidden">
            {/* Flowing Gradient Background */}
            <div className={`absolute inset-0 bg-gradient-to-br ${modernGradient}`} />

            {/* Abstract Pattern Overlay */}
            <div className="absolute inset-0 opacity-30">
              <div className={`absolute inset-0 bg-gradient-to-tr ${modernGradient} blur-xl scale-110 animate-pulse`} />
            </div>

            {/* Liquid Glass Layer */}
            <div className="absolute inset-0 bg-white/10 backdrop-blur-[2px]" />

            {/* Glass Reflection */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent" />

            {/* Subtle Noise Texture */}
            <div
              className="absolute inset-0 opacity-[0.03] mix-blend-overlay"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='1' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                backgroundSize: '128px 128px'
              }}
            />

            {/* Status badge with glass effect */}
            <div className="absolute top-2 right-2">
              <span className={`text-xs font-medium px-2 py-1 rounded-full backdrop-blur-md bg-black/40 border border-white/20 text-white shadow-lg ${
                status === 'ready' ? 'bg-green-500/20 border-green-400/50 text-green-100' :
                status === 'generating' ? 'bg-orange-500/20 border-orange-400/50 text-orange-100' :
                'bg-slate-500/20 border-slate-400/50 text-slate-100'
              }`}>
                {statusInfo.badge}
              </span>
            </div>

            {/* Play button overlay with glass effect */}
            <motion.div
              initial={{ opacity: 0 }}
              whileHover={{ opacity: 1 }}
              className="absolute inset-0 bg-black/10 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300"
            >
              <Button
                onClick={handlePlayClick}
                size="sm"
                disabled={!statusInfo.playable}
                className={`
                  rounded-full w-12 h-12 shadow-2xl backdrop-blur-md border border-white/30
                  ${statusInfo.playable
                    ? 'bg-white/20 hover:bg-white/30 hover:scale-110 text-white shadow-white/25'
                    : 'bg-black/20 cursor-not-allowed text-slate-400 border-slate-600/50'
                  }
                  transition-all duration-300
                `}
              >
                {status === 'generating' ? (
                  <Sparkles className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 fill-current ml-0.5" />
                )}
              </Button>
            </motion.div>

            {/* Loading animation for generating state */}
            {status === 'generating' && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-700/50">
                <motion.div
                  className="h-full bg-gradient-to-r from-orange-500 to-orange-400"
                  initial={{ width: '0%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                />
              </div>
            )}
          </div>

          {/* Compact Content */}
          <div className="p-3 space-y-1">
            <h4 className="font-semibold text-white text-sm group-hover:text-green-400 transition-colors line-clamp-2 leading-tight">
              {title}
            </h4>

            {subtitle && (
              <p className="text-xs text-slate-400 line-clamp-1">
                {subtitle}
              </p>
            )}

            {/* Duration or Date */}
            {status === 'ready' && duration ? (
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <Clock className="w-3 h-3" />
                <span>{formatDuration(duration)}</span>
              </div>
            ) : date ? (
              <p className="text-xs text-slate-500">
                {new Date(date).toLocaleDateString()}
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}