import React from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Play, Clock, FileAudio, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

interface DailyBrief {
  id: string;
  category: 'general' | 'aiml' | 'devops';
  title: string;
  date: string;
  duration?: number; // seconds - optional for empty state
  storyCount?: number; // optional for empty state
  stories?: Array<{
    title: string;
    summary: string;
    source: string;
    duration: number;
  }>;
  status: 'empty' | 'generating' | 'ready' | 'error';
  audioUrl?: string;
  coverArt?: string;
}

interface DailyBriefCardProps {
  brief: DailyBrief;
  isAuthenticated: boolean;
  onPlay: (briefId: string) => void;
  onPreview: (briefId: string) => void;
  onAuthRequired: (trigger: { type: 'play_brief'; briefId: string }) => void;
}

const categoryConfig = {
  general: {
    icon: '🌐',
    name: 'General Tech',
    description: 'Business, startups, consumer tech',
    gradient: 'from-blue-500 via-blue-600 to-indigo-700',
    accentColor: 'text-blue-400'
  },
  aiml: {
    icon: '🤖',
    name: 'AI/ML',
    description: 'Research, models, applications',
    gradient: 'from-orange-500 via-orange-600 to-red-600',
    accentColor: 'text-orange-400'
  },
  devops: {
    icon: '💻',
    name: 'DevOps',
    description: 'Cloud, infrastructure, tools',
    gradient: 'from-green-500 via-green-600 to-emerald-700',
    accentColor: 'text-green-400'
  }
};

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export default function DailyBriefCard({
  brief,
  isAuthenticated,
  onPlay,
  onPreview,
  onAuthRequired
}: DailyBriefCardProps) {
  const config = categoryConfig[brief.category];

  const handlePlayClick = () => {
    if (brief.status !== 'ready') return;

    if (isAuthenticated) {
      onPlay(brief.id);
    } else {
      onAuthRequired({ type: 'play_brief', briefId: brief.id });
    }
  };

  const getStatusInfo = () => {
    switch (brief.status) {
      case 'empty':
        return {
          badge: 'Coming Today',
          badgeColor: 'bg-slate-600/80 text-slate-300',
          subtitle: 'Daily brief at 7 AM UTC',
          playButton: 'Coming Soon'
        };
      case 'generating':
        return {
          badge: 'Generating',
          badgeColor: 'bg-orange-500/80 text-white',
          subtitle: 'Creating your daily briefing...',
          playButton: 'Generating...'
        };
      case 'ready':
        return {
          badge: 'Ready',
          badgeColor: 'bg-green-500/80 text-white',
          subtitle: `${formatDuration(brief.duration || 0)} • ${brief.storyCount || 0} stories`,
          playButton: isAuthenticated ? 'Play Brief' : 'Sign in to Play'
        };
      case 'error':
        return {
          badge: 'Error',
          badgeColor: 'bg-red-500/80 text-white',
          subtitle: 'Failed to generate today',
          playButton: 'Retry Later'
        };
    }
  };

  const statusInfo = getStatusInfo();
  const canPlay = brief.status === 'ready';

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className="group cursor-pointer"
    >
      <Card className="
        bg-slate-900/60 border-slate-800/40 hover:bg-slate-800/60
        transition-all duration-300 overflow-hidden
        backdrop-blur-sm hover:border-slate-700/60
      ">
        <CardContent className="p-0">
          {/* Cover Art - Spotify style */}
          <div className="relative aspect-square bg-gradient-to-br bg-slate-800">
            {/* Gradient background matching category */}
            <div className={`absolute inset-0 bg-gradient-to-br ${config.gradient} opacity-80`} />

            {/* Category icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-6xl filter drop-shadow-lg">
                {config.icon}
              </div>
            </div>

            {/* Status indicator */}
            <div className="absolute top-3 right-3">
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusInfo.badgeColor}`}>
                {statusInfo.badge}
              </span>
            </div>

            {/* Play button overlay - Spotify style */}
            <motion.div
              initial={{ opacity: 0 }}
              whileHover={{ opacity: 1 }}
              className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            >
              <Button
                onClick={handlePlayClick}
                size="lg"
                disabled={!canPlay}
                className={`
                  rounded-full w-14 h-14 shadow-xl
                  ${canPlay
                    ? 'bg-green-500 hover:bg-green-400 hover:scale-110 text-black'
                    : 'bg-slate-600 cursor-not-allowed text-slate-400'
                  }
                  transition-all duration-200
                `}
              >
                {brief.status === 'generating' ? (
                  <Sparkles className="w-6 h-6 animate-spin" />
                ) : (
                  <Play className="w-6 h-6 fill-current ml-0.5" />
                )}
              </Button>
            </motion.div>

            {/* Loading animation for generating state */}
            {brief.status === 'generating' && (
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

          {/* Content - Spotify style */}
          <div className="p-4 space-y-2">
            <h3 className="font-semibold text-white text-base group-hover:text-green-400 transition-colors line-clamp-1">
              {config.name} Brief
            </h3>

            <p className="text-sm text-slate-400 line-clamp-1">
              {statusInfo.subtitle}
            </p>

            <p className="text-xs text-slate-500 line-clamp-1">
              {config.description}
            </p>

            {/* Latest topics for ready state */}
            {brief.status === 'ready' && brief.stories && brief.stories.length > 0 && (
              <div className="pt-2 border-t border-slate-800/50">
                <p className="text-xs text-slate-500 mb-1">Latest:</p>
                {brief.stories.slice(0, 1).map((story, index) => (
                  <p key={index} className="text-xs text-slate-400 truncate">
                    • {story.title}
                  </p>
                ))}
                {brief.stories.length > 1 && (
                  <p className="text-xs text-slate-500">
                    +{brief.stories.length - 1} more
                  </p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}