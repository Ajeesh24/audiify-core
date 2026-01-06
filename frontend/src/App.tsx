import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Headphones, Sparkles, FileText, Link2, Volume2, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AudioPlayer from '@/components/AudioPlayer';
import WaveformVisual from '@/components/WaveformVisual';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { AuthForm } from '@/components/AuthForm';
import { UserDashboard } from '@/components/UserDashboard';
import { audifyApi, setAuthTokenGetter, type ArticleProcessRequest, type ProcessArticleResponse, type ArticleContent, type AudioResponse, type JobStatusResponse } from '@/services/api';

function AuthenticatedApp() {
  const { user, loading, isAuthenticated, getAccessToken, signOut, isConfigured, isDevelopment } = useAuth();
  const [url, setUrl] = useState('');
  const [mode, setMode] = useState<'full' | 'summary'>('full');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState('');
  const [progress, setProgress] = useState(0);
  const [audioData, setAudioData] = useState<AudioResponse | null>(null);
  const [articleContent, setArticleContent] = useState<ArticleContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDashboard, setShowDashboard] = useState(false);

  // Set up auth token getter for API requests
  useEffect(() => {
    if (isConfigured) {
      setAuthTokenGetter(getAccessToken);
    }
  }, [getAccessToken, isConfigured]);

  const processArticle = async () => {
    if (!url.trim()) return;

    setIsProcessing(true);
    setError(null);
    setAudioData(null);
    setArticleContent(null);
    setProgress(0);

    try {
      // Step 1: Validate URL
      setProcessingStep('Validating URL...');
      const validation = await audifyApi.validateUrl(url);

      if (!validation.valid) {
        setError('Invalid or inaccessible URL. Please check the URL and try again.');
        return;
      }

      // Step 2: Process article with progress tracking
      setProcessingStep('Starting article processing...');

      const request: ArticleProcessRequest = {
        url,
        mode,
      };

      const response: ProcessArticleResponse = await audifyApi.processArticle(
        request,
        (status: JobStatusResponse) => {
          setProgress(status.progress);
          setProcessingStep(status.step || 'Processing...');
        }
      );

      if (!response.success) {
        setError(response.error || 'Failed to process article');
        return;
      }

      if (response.article && response.audio) {
        setArticleContent(response.article);
        setAudioData(response.audio);
        setProcessingStep('Complete!');
        setProgress(100);
      } else {
        setError('Incomplete response from server');
      }

    } catch (err: any) {
      console.error('Processing error:', err);

      // Handle different types of errors
      if (err.message?.includes('Authentication required')) {
        setError('Please sign in to process articles.');
        // Could trigger sign out here if token is expired
      } else if (err.message?.includes('Rate limit')) {
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
      setTimeout(() => {
        setProcessingStep('');
        setProgress(0);
      }, 2000);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isProcessing) {
      processArticle();
    }
  };

  const handleSignOut = () => {
    setShowDashboard(false);
    setUrl('');
    setAudioData(null);
    setArticleContent(null);
    setError(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show development mode message when Cognito isn't configured
  if (!isConfigured && isDevelopment) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center p-4">
        {/* Ambient background effects */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10 w-full max-w-2xl text-center">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl shadow-lg shadow-purple-500/25">
                <Headphones className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-violet-300 bg-clip-text text-transparent">
                Audifyy
              </h1>
            </div>
          </motion.div>

          {/* Development Mode Message */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-slate-900/50 border border-slate-800/50 backdrop-blur-xl rounded-2xl p-8 shadow-2xl"
          >
            <div className="text-center space-y-4">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-yellow-500/20 rounded-full mb-4">
                <Sparkles className="w-8 h-8 text-yellow-400" />
              </div>

              <h2 className="text-2xl font-bold text-white mb-2">
                Development Mode
              </h2>

              <p className="text-slate-400 text-lg mb-6">
                Cognito authentication is not configured. This is expected during local development.
              </p>

              <div className="bg-slate-800/50 rounded-xl p-6 text-left space-y-3">
                <h3 className="font-semibold text-white mb-3">To enable authentication:</h3>
                <div className="space-y-2 text-sm text-slate-300">
                  <p>1. <span className="font-medium text-white">Deploy the infrastructure:</span></p>
                  <code className="block bg-slate-700/50 px-3 py-2 rounded text-xs font-mono text-green-400">
                    git push origin main  # Triggers deployment
                  </code>

                  <p>2. <span className="font-medium text-white">Set up GitHub Secrets:</span></p>
                  <ul className="list-disc list-inside space-y-1 text-xs text-slate-400 ml-4">
                    <li>OPENAI_API_KEY</li>
                    <li>AWS_GITHUB_TRUST_ROLE</li>
                    <li>AWS_DEPLOYMENT_ROLE</li>
                  </ul>

                  <p>3. <span className="font-medium text-white">After deployment:</span> Authentication will work automatically!</p>
                </div>
              </div>

              <p className="text-slate-500 text-sm">
                For now, you can preview the UI design but authentication features are disabled.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center p-4">
        {/* Ambient background effects */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10 w-full max-w-md">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl shadow-lg shadow-purple-500/25">
                <Headphones className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-violet-300 bg-clip-text text-transparent">
                Audifyy
              </h1>
            </div>
            <p className="text-slate-400 text-lg">
              Transform articles into audio with AI
            </p>
          </motion.div>

          <AuthForm onSuccess={() => {}} />
        </div>
      </div>
    );
  }

  if (showDashboard) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-4">
        {/* Ambient background effects */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10 container mx-auto py-8 max-w-6xl">
          {/* Header with back button */}
          <div className="flex items-center justify-between mb-8">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3"
            >
              <div className="p-2 bg-gradient-to-br from-purple-500 to-violet-600 rounded-xl shadow-lg">
                <Headphones className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-white via-purple-200 to-violet-300 bg-clip-text text-transparent">
                Audifyy
              </h1>
            </motion.div>

            <Button
              onClick={() => setShowDashboard(false)}
              className="bg-slate-800/50 hover:bg-slate-700/50 text-white border border-slate-600/50"
            >
              Convert New Article
            </Button>
          </div>

          <UserDashboard onSignOut={handleSignOut} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
      {/* Ambient background effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 container mx-auto px-4 py-8 max-w-4xl">
        {/* Header with user info */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-8"
        >
          <div className="inline-flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-purple-500 to-violet-600 rounded-2xl shadow-lg shadow-purple-500/25">
              <Headphones className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-violet-300 bg-clip-text text-transparent">
                Audifyy
              </h1>
              <p className="text-slate-400 text-sm">
                Welcome back, {user?.name || user?.email?.split('@')[0]}!
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <Button
              onClick={() => setShowDashboard(true)}
              variant="outline"
              className="bg-slate-800/50 hover:bg-slate-700/50 text-white border-slate-600/50"
            >
              <User className="w-4 h-4 mr-2" />
              My Articles
            </Button>
            <Button
              onClick={signOut}
              variant="outline"
              className="bg-slate-800/50 hover:bg-slate-700/50 text-white border-slate-600/50"
            >
              Sign Out
            </Button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <p className="text-slate-400 text-lg">
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

                {/* Progress Bar */}
                {isProcessing && progress > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm text-slate-400">
                      <span>Progress</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                      <motion.div
                        className="bg-gradient-to-r from-purple-600 to-violet-600 h-2 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                  </div>
                )}

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
                audio={audioData}
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
          Powered by AI • Secure authentication • Natural voice synthesis
        </motion.p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}