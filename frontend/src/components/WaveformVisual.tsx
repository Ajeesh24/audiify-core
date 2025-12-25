import React from 'react';
import { motion } from 'framer-motion';

interface WaveformVisualProps {
  isAnimating: boolean;
  className?: string;
}

export default function WaveformVisual({ isAnimating, className = '' }: WaveformVisualProps) {
  const bars = Array.from({ length: 20 }, (_, i) => i);

  return (
    <div className={`flex items-center justify-center space-x-1 ${className}`}>
      {bars.map((bar) => (
        <motion.div
          key={bar}
          className="bg-gradient-to-t from-purple-600 to-violet-400 rounded-full"
          style={{
            width: '3px',
            minHeight: '8px',
          }}
          animate={
            isAnimating
              ? {
                  height: [
                    Math.random() * 30 + 8,
                    Math.random() * 50 + 8,
                    Math.random() * 30 + 8,
                  ],
                }
              : { height: 8 }
          }
          transition={{
            duration: 0.8 + Math.random() * 0.4,
            repeat: isAnimating ? Infinity : 0,
            ease: 'easeInOut',
            delay: bar * 0.05,
          }}
        />
      ))}
    </div>
  );
}