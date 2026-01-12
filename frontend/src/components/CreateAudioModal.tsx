import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { X, Link2, FileText, Sparkles, Loader2 } from 'lucide-react';

interface CreateAudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (url: string, mode: 'full' | 'summary') => void;
  isProcessing?: boolean;
  isDarkMode?: boolean;
}

export default function CreateAudioModal({
  isOpen,
  onClose,
  onSubmit,
  isProcessing = false,
  isDarkMode = true
}: CreateAudioModalProps) {
  const [url, setUrl] = useState('');
  const [mode, setMode] = useState<'full' | 'summary'>('full');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim() && !isProcessing) {
      onSubmit(url.trim(), mode);
    }
  };

  const handleClose = () => {
    if (!isProcessing) {
      setUrl('');
      setMode('full');
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop - Theme Aware */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={`fixed inset-0 backdrop-blur-sm z-50 ${
              isDarkMode
                ? 'bg-black/60'
                : 'bg-white/30'
            }`}
            onClick={handleClose}
          />

          {/* Modal - OpenAI Academy Style */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.3 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className={`
              max-w-lg w-full mx-4 rounded-xl shadow-2xl overflow-hidden
              ${isDarkMode
                ? 'bg-slate-900/95 border border-slate-700/50'
                : 'bg-white/95 border border-slate-200'
              } backdrop-blur-xl
            `}>

              {/* Header - Clean and Modern */}
              <div className={`
                px-6 py-5 flex items-center justify-between
                ${isDarkMode
                  ? 'border-b border-slate-700/50'
                  : 'border-b border-slate-200'
                }
              `}>
                <div>
                  <h2 className={`
                    text-xl font-semibold font-['Inter']
                    ${isDarkMode ? 'text-white' : 'text-slate-900'}
                  `}>
                    Convert Article to Audio
                  </h2>
                  <p className={`
                    text-sm mt-1
                    ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}
                  `}>
                    Transform any article into high-quality audio
                  </p>
                </div>
                {!isProcessing && (
                  <Button
                    onClick={handleClose}
                    variant="ghost"
                    size="sm"
                    className={`
                      p-2 hover:bg-slate-100 rounded-lg transition-colors
                      ${isDarkMode
                        ? 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                        : 'text-slate-500 hover:text-slate-700'
                      }
                    `}
                  >
                    <X className="w-5 h-5" />
                  </Button>
                )}
              </div>

              {/* Content - OpenAI Academy Style */}
              <form onSubmit={handleSubmit} className="p-6 space-y-6">

                {/* URL Input - Clean Design */}
                <div className="space-y-3">
                  <label className={`
                    text-sm font-medium flex items-center gap-2
                    ${isDarkMode ? 'text-slate-200' : 'text-slate-700'}
                  `}>
                    <Link2 className="w-4 h-4" />
                    Article URL
                  </label>
                  <Input
                    type="url"
                    placeholder="https://example.com/article..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isProcessing}
                    className={`
                      h-12 rounded-lg transition-all
                      ${isDarkMode
                        ? 'bg-slate-800/60 border-slate-600/50 text-white placeholder:text-slate-400 focus:border-blue-500 focus:ring-blue-500/20'
                        : 'bg-slate-50 border-slate-300 text-slate-900 placeholder:text-slate-500 focus:border-blue-500 focus:ring-blue-500/20'
                      }
                    `}
                    required
                  />
                </div>

                {/* Mode Selection - Academy Style Cards */}
                <div className="space-y-3">
                  <label className={`
                    text-sm font-medium
                    ${isDarkMode ? 'text-slate-200' : 'text-slate-700'}
                  `}>
                    Processing Mode
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <Button
                      type="button"
                      onClick={() => !isProcessing && setMode('full')}
                      disabled={isProcessing}
                      className={`
                        h-16 flex-col gap-2 transition-all border rounded-lg
                        ${mode === 'full'
                          ? isDarkMode
                            ? 'bg-blue-500 hover:bg-blue-400 text-white border-blue-500'
                            : 'bg-blue-500 hover:bg-blue-400 text-white border-blue-500'
                          : isDarkMode
                            ? 'bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 border-slate-600/50'
                            : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-300'
                        }
                      `}
                    >
                      <FileText className="w-5 h-5" />
                      <span className="text-sm font-medium">Full Article</span>
                    </Button>

                    <Button
                      type="button"
                      onClick={() => !isProcessing && setMode('summary')}
                      disabled={isProcessing}
                      className={`
                        h-16 flex-col gap-2 transition-all border rounded-lg
                        ${mode === 'summary'
                          ? isDarkMode
                            ? 'bg-blue-500 hover:bg-blue-400 text-white border-blue-500'
                            : 'bg-blue-500 hover:bg-blue-400 text-white border-blue-500'
                          : isDarkMode
                            ? 'bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 border-slate-600/50'
                            : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-300'
                        }
                      `}
                    >
                      <Sparkles className="w-5 h-5" />
                      <span className="text-sm font-medium">Smart Summary</span>
                    </Button>
                  </div>
                </div>

                {/* Submit Button - OpenAI Academy Style */}
                <div className="pt-2">
                  <Button
                    type="submit"
                    disabled={!url.trim() || isProcessing}
                    className={`
                      w-full h-12 font-semibold text-base rounded-lg transition-all
                      ${isDarkMode
                        ? 'bg-blue-600 hover:bg-blue-500 text-white'
                        : 'bg-blue-600 hover:bg-blue-500 text-white'
                      }
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        Processing Article...
                      </>
                    ) : (
                      <>
                        <FileText className="w-5 h-5 mr-2" />
                        Generate Audio
                      </>
                    )}
                  </Button>
                </div>

                {/* Processing Status - Clean Design */}
                {isProcessing && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`
                      rounded-lg p-4 border
                      ${isDarkMode
                        ? 'bg-blue-500/10 border-blue-500/30'
                        : 'bg-blue-50 border-blue-200'
                      }
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`
                        w-6 h-6 border-2 border-t-transparent rounded-full animate-spin
                        ${isDarkMode ? 'border-blue-400' : 'border-blue-500'}
                      `} />
                      <div>
                        <p className={`
                          text-sm font-medium
                          ${isDarkMode ? 'text-blue-300' : 'text-blue-700'}
                        `}>
                          Processing your article...
                        </p>
                        <p className={`
                          text-xs mt-1
                          ${isDarkMode ? 'text-blue-400/80' : 'text-blue-600/80'}
                        `}>
                          Converting to high-quality audio. This usually takes 1-2 minutes.
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}