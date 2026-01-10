import React from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Play, Clock, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

interface CompactAudioCardProps {
  id: string;
  title: string;
  subtitle?: string;
  duration?: number;
  date?: string;
  status?: 'empty' | 'generating' | 'ready' | 'error';
  gradient?: string;
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
  gradient = 'from-slate-600 to-slate-700',
  icon = '🎵',
  type,
  isAuthenticated,
  onPlay,
  onAuthRequired
}: CompactAudioCardProps) {
  const config = typeConfig[type];

  const handlePlayClick = () => {
    if (status !== 'ready') return;

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
          playable: false
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
          {/* Compact Cover Art */}
          <div className="relative aspect-square bg-gradient-to-br bg-slate-800">
            {/* Gradient background */}
            <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-80`} />

            {/* Icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-3xl filter drop-shadow-lg">
                {icon}
              </div>
            </div>

            {/* Status badge */}
            <div className="absolute top-2 right-2">
              <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${statusInfo.badgeColor}`}>
                {statusInfo.badge}
              </span>
            </div>

            {/* Play button overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              whileHover={{ opacity: 1 }}
              className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            >
              <Button
                onClick={handlePlayClick}
                size="sm"
                disabled={!statusInfo.playable}
                className={`
                  rounded-full w-10 h-10 shadow-lg
                  ${statusInfo.playable
                    ? 'bg-green-500 hover:bg-green-400 hover:scale-110 text-black'
                    : 'bg-slate-600 cursor-not-allowed text-slate-400'
                  }
                  transition-all duration-200
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