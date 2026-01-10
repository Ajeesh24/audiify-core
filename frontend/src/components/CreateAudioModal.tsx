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
}

export default function CreateAudioModal({
  isOpen,
  onClose,
  onSubmit,
  isProcessing = false
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
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={handleClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.3 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl max-w-2xl w-full mx-4 overflow-hidden">
              {/* Header */}
              <div className="px-6 py-4 border-b border-slate-700/50 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-white">Convert Article to Audio</h2>
                  <p className="text-slate-400 text-sm mt-1">Transform any article into audio</p>
                </div>
                {!isProcessing && (
                  <Button
                    onClick={handleClose}
                    variant="ghost"
                    size="sm"
                    className="text-slate-400 hover:text-white p-2"
                  >
                    <X className="w-5 h-5" />
                  </Button>
                )}
              </div>

              {/* Content */}
              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* URL Input */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                    <Link2 className="w-4 h-4" />
                    Article URL
                  </label>
                  <Input
                    type="url"
                    placeholder="Paste article URL here..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isProcessing}
                    className="bg-slate-800/60 border-slate-600/50 text-white placeholder:text-slate-400 focus:border-purple-500 focus:ring-purple-500/20 h-12"
                    required
                  />
                </div>

                {/* Mode Selection */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-slate-300">Processing Mode</label>
                  <div className="flex gap-3">
                    <Button
                      type="button"
                      onClick={() => !isProcessing && setMode('full')}
                      disabled={isProcessing}
                      className={`flex-1 h-12 transition-all ${
                        mode === 'full'
                          ? 'bg-purple-500 hover:bg-purple-400 text-white'
                          : 'bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 border border-slate-600/50'
                      }`}
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      Full Article
                    </Button>
                    <Button
                      type="button"
                      onClick={() => !isProcessing && setMode('summary')}
                      disabled={isProcessing}
                      className={`flex-1 h-12 transition-all ${
                        mode === 'summary'
                          ? 'bg-purple-500 hover:bg-purple-400 text-white'
                          : 'bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 border border-slate-600/50'
                      }`}
                    >
                      <Sparkles className="w-4 h-4 mr-2" />
                      Summary Only
                    </Button>
                  </div>
                </div>

                {/* Submit Button */}
                <div className="pt-4">
                  <Button
                    type="submit"
                    disabled={!url.trim() || isProcessing}
                    className="w-full h-14 bg-gradient-to-r from-purple-500 to-violet-500 hover:from-purple-400 hover:to-violet-400 text-white font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed transition-all"
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

                {/* Processing Status */}
                {isProcessing && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                      <div>
                        <p className="text-sm font-medium text-purple-300">Processing your article...</p>
                        <p className="text-xs text-purple-400/80 mt-1">
                          We're converting your article to audio. This usually takes 1-2 minutes.
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