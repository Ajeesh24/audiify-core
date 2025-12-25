import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Headphones, Sparkles, FileText, Link2, Volume2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AudioPlayer from '@/components/AudioPlayer';
import WaveformVisual from '@/components/WaveformVisual';
import { audifyApi, type ArticleProcessRequest, type ProcessArticleResponse, type ArticleContent, type AudioResponse } from '@/services/api';

export default function App() {
  const [url, setUrl] = useState('');
  const [mode, setMode] = useState<'full' | 'summary'>('full');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState('');
  const [audioData, setAudioData] = useState<AudioResponse | null>(null);
  const [articleContent, setArticleContent] = useState<ArticleContent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const processArticle = async () => {
    if (!url.trim()) return;

    setIsProcessing(true);
    setError(null);
    setAudioData(null);
    setArticleContent(null);

    try {
      // Step 1: Validate URL
      setProcessingStep('Validating URL...');
      const validation = await audifyApi.validateUrl(url);

      if (!validation.valid) {
        setError('Invalid or inaccessible URL. Please check the URL and try again.');
        return;
      }

      // Step 2: Process article
      setProcessingStep(mode === 'summary' ? 'Extracting and summarizing article...' : 'Extracting article content...');

      const request: ArticleProcessRequest = {
        url,
        mode,
      };

      const response: ProcessArticleResponse = await audifyApi.processArticle(request);

      if (!response.success) {
        setError(response.error || 'Failed to process article');
        return;
      }

      if (response.article && response.audio) {
        setArticleContent(response.article);
        setAudioData(response.audio);
        setProcessingStep('');
      } else {
        setError('Incomplete response from server');
      }

    } catch (err: any) {
      console.error('Processing error:', err);

      // Handle different types of errors
      if (err.message?.includes('Rate limit')) {
        setError('Rate limit exceeded. Please try again in a few minutes.');
      } else if (err.message?.includes('timeout')) {
        setError('Request timeout. The article might be too long to process. Try a shorter article or summary mode.');
      } else if (err.message?.includes('paywall')) {
        setError('This article appears to be behind a paywall. Please try a different article.');
      } else {
        setError(err.message || 'An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsProcessing(false);
      setProcessingStep('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isProcessing) {
      processArticle();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
      {/* Ambient background effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 container mx-auto px-4 py-12 max-w-4xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl shadow-lg shadow-purple-500/25">
              <Headphones className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-white via-purple-200 to-violet-300 bg-clip-text text-transparent">
              Audifyy
            </h1>
          </div>
          <p className="text-slate-400 text-lg max-w-md mx-auto">
            Transform any article into crystal-clear audio. Listen on the go.
          </p>
        </motion.div>

        {/* Main Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="bg-slate-900/50 border-slate-800/50 backdrop-blur-xl shadow-2xl">
            <CardContent className="p-8">
              {/* URL Input */}
              <div className="space-y-6">
                <div className="relative">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
                    <Link2 className="w-5 h-5" />
                  </div>
                  <Input
                    type="url"
                    placeholder="Paste article URL here..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="pl-12 h-14 bg-slate-800/50 border-slate-700/50 text-white placeholder:text-slate-500 text-lg rounded-xl focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500"
                    disabled={isProcessing}
                  />
                </div>

                {/* Mode Selection */}
                <div className="flex justify-center">
                  <Tabs value={mode} onValueChange={(value) => setMode(value as 'full' | 'summary')} className="w-full max-w-md">
                    <TabsList className="w-full bg-slate-800/50 p-1 rounded-xl h-auto">
                      <TabsTrigger
                        value="full"
                        className="flex-1 py-3 data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-violet-600 data-[state=active]:text-white rounded-lg transition-all"
                        disabled={isProcessing}
                      >
                        <FileText className="w-4 h-4 mr-2" />
                        Full Article
                      </TabsTrigger>
                      <TabsTrigger
                        value="summary"
                        className="flex-1 py-3 data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-violet-600 data-[state=active]:text-white rounded-lg transition-all"
                        disabled={isProcessing}
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        Summary Only
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>

                {/* Generate Button */}
                <Button
                  onClick={processArticle}
                  disabled={!url.trim() || isProcessing}
                  className="w-full h-14 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 text-white text-lg font-medium rounded-xl shadow-lg shadow-purple-500/25 transition-all duration-300 disabled:opacity-50"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      {processingStep || 'Processing...'}
                    </>
                  ) : (
                    <>
                      <Volume2 className="w-5 h-5 mr-2" />
                      Generate Audio
                    </>
                  )}
                </Button>

                {/* Error Message */}
                <AnimatePresence>
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-center"
                    >
                      {error}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Audio Player Section */}
        <AnimatePresence>
          {audioData && articleContent && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: 0.2 }}
              className="mt-8"
            >
              <AudioPlayer
                audioId={audioData.audio_id}
                content={mode === 'summary' ? articleContent.summary : articleContent.content}
                title={articleContent.title}
                mode={mode}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Waveform Visual */}
        {isProcessing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-8"
          >
            <Card className="bg-slate-900/30 border-slate-800/30 backdrop-blur-xl">
              <CardContent className="p-8">
                <div className="text-center mb-4">
                  <p className="text-slate-300 font-medium">
                    {processingStep || 'Processing article...'}
                  </p>
                </div>
                <WaveformVisual isAnimating={true} className="h-16" />
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Footer */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center text-slate-600 text-sm mt-12"
        >
          Powered by AI • Clean content extraction • Natural voice synthesis
        </motion.p>
      </div>
    </div>
  );
}