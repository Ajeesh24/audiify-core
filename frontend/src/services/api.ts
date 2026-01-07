import axios from 'axios';

// API client configuration
// Priority: Runtime config (env.js) > Build-time config > Development fallback
const getRuntimeApiUrl = () => {
  // Check if runtime environment config is available (from env.js)
  if (typeof window !== 'undefined' && (window as any).ENV?.VITE_API_URL) {
    return (window as any).ENV.VITE_API_URL;
  }
  // Fall back to build-time environment variable
  return import.meta.env.VITE_API_URL;
};

const getRuntimeStreamingUrl = () => {
  // Check if runtime streaming URL is available (from env.js)
  if (typeof window !== 'undefined' && (window as any).ENV?.VITE_STREAMING_API_URL) {
    return (window as any).ENV.VITE_STREAMING_API_URL;
  }
  // Fall back to build-time environment variable
  return import.meta.env.VITE_STREAMING_API_URL;
};

const API_BASE_URL = getRuntimeApiUrl() || 'http://localhost:8000/api';
const STREAMING_API_URL = getRuntimeStreamingUrl() || 'http://localhost:8000'; // Function URL (no /api prefix)

// Debug: Log the API URLs being used
console.log('API Configuration:', {
  runtimeApiUrl: (window as any).ENV?.VITE_API_URL,
  runtimeStreamingUrl: (window as any).ENV?.VITE_STREAMING_API_URL,
  buildTimeApiUrl: import.meta.env.VITE_API_URL,
  buildTimeStreamingUrl: import.meta.env.VITE_STREAMING_API_URL,
  finalApiUrl: API_BASE_URL,
  finalStreamingUrl: STREAMING_API_URL
});

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes timeout for TTS generation
  headers: {
    'Content-Type': 'application/json',
  },
});

// Global variable to store the auth token getter function
let getAuthToken: (() => Promise<string | null>) | null = null;

// Function to set the auth token getter
export const setAuthTokenGetter = (tokenGetter: () => Promise<string | null>) => {
  getAuthToken = tokenGetter;
};

// Request interceptor for logging and authentication
apiClient.interceptors.request.use(async (config) => {
  console.log(`Making API request: ${config.method?.toUpperCase()} ${config.url}`);

  // Add authentication header if token is available
  if (getAuthToken) {
    console.log('🔍 Token getter function is available, attempting to get token...');
    try {
      const token = await getAuthToken();
      console.log('🎫 Token retrieval result:', {
        hasToken: !!token,
        tokenLength: token?.length,
        tokenStart: token?.substring(0, 20) + '...'
      });

      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log('✅ Authorization header added to request');
      } else {
        console.warn('⚠️ No token available - request will be unauthorized');
      }
    } catch (error) {
      console.error('❌ Failed to get auth token:', error);
    }
  } else {
    console.warn('⚠️ No token getter function available');
  }

  console.log('📤 Final request headers:', {
    Authorization: config.headers.Authorization ? 'Bearer [TOKEN]' : 'NOT SET',
    'Content-Type': config.headers['Content-Type']
  });

  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - could redirect to login
      console.warn('Authentication required or token expired');
      throw new Error('Authentication required. Please sign in.');
    }
    if (error.response?.status === 403) {
      throw new Error('Access denied. You do not have permission to access this resource.');
    }
    if (error.response?.status === 429) {
      throw new Error('Rate limit exceeded. Please try again later.');
    }
    if (error.response?.status >= 500) {
      throw new Error('Server error. Please try again later.');
    }
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout. The article might be too long to process.');
    }
    throw error;
  }
);

// API Types
export interface ArticleProcessRequest {
  url: string;
  mode: 'full' | 'summary';
}

export interface ArticleContent {
  title?: string;
  content: string;
  summary?: string;
  word_count: number;
  estimated_reading_time: number;
}

export interface AudioResponse {
  audio_id: string;
  duration?: number;
  size?: number;
  url?: string;  // S3 URL or API endpoint
  s3_key?: string;
  storage?: 's3' | 'local';
  expires_at?: string;
}

export interface ProcessArticleResponse {
  success: boolean;
  article?: ArticleContent;
  audio?: AudioResponse;
  error?: string;
}

export interface JobStartResponse {
  job_id: string;
  status: string;
  estimated_time: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'processing' | 'completed' | 'error';
  progress: number;
  step?: string;
  result?: ProcessArticleResponse;
  error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface MyArticlesResponse {
  articles: Array<{
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
  }>;
  pagination: {
    limit: number;
    last_key: string | null;
    has_more: boolean;
    total_returned: number;
  };
}

// API Functions
export const audifyApi = {
  // Health check
  async healthCheck() {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Validate URL
  async validateUrl(url: string) {
    const response = await apiClient.post('/validate-url', { url });
    return response.data;
  },

  // Start async article processing (requires authentication)
  async startProcessing(request: ArticleProcessRequest): Promise<JobStartResponse> {
    const response = await apiClient.post('/process-article', request);
    return response.data;
  },

  // Get job status (requires authentication)
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await apiClient.get(`/job-status/${jobId}`);
    return response.data;
  },

  // Poll job status until completion
  async pollJobStatus(
    jobId: string,
    onProgress?: (status: JobStatusResponse) => void,
    pollInterval: number = 2000,
    maxAttempts: number = 180  // 6 minutes with 2-second intervals
  ): Promise<JobStatusResponse> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const status = await this.getJobStatus(jobId);

      // Call progress callback if provided
      if (onProgress) {
        onProgress(status);
      }

      // Check if job is complete
      if (status.status === 'completed' || status.status === 'error') {
        return status;
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error('Job polling timeout - processing took too long');
  },

  // Process article with streaming (new feature!)
  async processArticleStreaming(
    request: ArticleProcessRequest,
    onProgress?: (metadata: any) => void,
    onAudioChunk?: (chunk: Uint8Array, metadata: any) => void
  ): Promise<ProcessArticleResponse> {
    try {
      console.log('🚀 Starting streaming article processing:', request);

      // Helper to get auth headers
      const getAuthHeaders = async () => {
        if (getAuthToken) {
          const token = await getAuthToken();
          if (token) {
            return { 'Authorization': `Bearer ${token}` };
          }
        }
        return {};
      };

      // Use Function URL for streaming (better performance + native streaming support)
      // Handle trailing slash in STREAMING_API_URL to avoid double slashes
      const streamingBaseUrl = STREAMING_API_URL.endsWith('/')
        ? STREAMING_API_URL.slice(0, -1)
        : STREAMING_API_URL;

      const response = await fetch(`${streamingBaseUrl}/api/process-article-streaming`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...await getAuthHeaders(),  // RESTORE auth headers - needed for user_id
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      let articleMetadata: any = null;
      let audioMetadata: any = null;
      let audioChunks: Uint8Array[] = [];
      let buffer = '';
      let isComplete = false;

      console.log('📡 Starting to read streaming response...');

      try {
        while (!isComplete) {
          const { done, value } = await reader.read();

          if (done) {
            console.log('✅ Streaming completed');
            break;
          }

          // Decode chunk and add to buffer
          const chunk = new TextDecoder().decode(value);
          buffer += chunk;

          // Process complete lines
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            const trimmedLine = line.trim();

            if (trimmedLine.startsWith('data: ')) {
              try {
                const jsonStr = trimmedLine.substring(6);
                const data = JSON.parse(jsonStr);

                console.log('📨 Received streaming data:', data.type);

                if (data.type === 'metadata') {
                  articleMetadata = data;
                  console.log('📋 Article metadata received:', data.title);
                  onProgress?.(data);
                } else if (data.type === 'audio') {
                  audioMetadata = data.metadata;
                  console.log(`🎵 Audio chunk progress: ${data.metadata.progress}%`);
                  onProgress?.(data.metadata);
                } else if (data.type === 'complete') {
                  console.log('🎉 Audio generation completed');
                  isComplete = true;
                }
              } catch (e) {
                console.warn('⚠️ Failed to parse JSON line:', trimmedLine);
              }
            } else if (trimmedLine && !trimmedLine.startsWith('data:')) {
              // This might be binary audio data encoded as base64 or direct binary
              // For now, we'll skip since we're getting audio via metadata
              console.log('📦 Received non-JSON data (likely binary audio)');
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      // Build response from collected metadata
      if (audioMetadata && articleMetadata) {
        const audioResponse: AudioResponse = {
          audio_id: audioMetadata.audio_id,
          url: undefined,
          size: audioMetadata.size,
          storage: audioMetadata.storage,
          s3_key: audioMetadata.s3_key,
          duration: undefined,
          expires_at: undefined,
        };

        const articleContent: ArticleContent = {
          title: articleMetadata.title || 'Unknown Article',
          content: '', // Content not returned in streaming mode for performance
          summary: articleMetadata.mode === 'summary' ? 'AI-generated summary' : undefined,
          word_count: articleMetadata.word_count || 0,
          estimated_reading_time: articleMetadata.reading_time || 0,
        };

        console.log('✅ Successfully processed streaming response');

        return {
          success: true,
          article: articleContent,
          audio: audioResponse,
        };
      }

      throw new Error('Incomplete streaming response - missing metadata');

    } catch (error) {
      console.error('❌ Streaming processing error:', error);
      throw error;
    }
  },

  // Complete article processing (combines start + poll)
  async processArticle(
    request: ArticleProcessRequest,
    onProgress?: (status: JobStatusResponse) => void
  ): Promise<ProcessArticleResponse> {
    // Start the job
    const jobStart = await this.startProcessing(request);

    // Poll for completion
    const finalStatus = await this.pollJobStatus(jobStart.job_id, onProgress);

    // Return the final result
    if (finalStatus.status === 'error') {
      throw new Error(finalStatus.error || 'Processing failed');
    }

    if (finalStatus.result) {
      return finalStatus.result;
    }

    throw new Error('Processing completed but no result available');
  },

  // Get user's articles (requires authentication)
  async getMyArticles(lastKey?: string | null, limit: number = 20): Promise<MyArticlesResponse> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (lastKey) {
      params.append('last_key', lastKey);
    }

    const response = await apiClient.get(`/my-articles?${params.toString()}`);
    return response.data;
  },

  // Get audio stream URL (requires authentication)
  getAudioStreamUrl(audioId: string): string {
    return `${API_BASE_URL}/audio/${audioId}`;
  },

  // Get presigned URL for audio (returns JSON with URL)
  async getAudioPresignedUrl(audioId: string): Promise<string> {
    const response = await apiClient.get(`/audio/${audioId}/url`);
    return response.data.url;
  },

  // Get direct audio URL from job result (prefers S3 URL)
  getDirectAudioUrl(audio: AudioResponse): string {
    // If we have an S3 URL, use it directly
    if (audio.url && audio.url.startsWith('http')) {
      return audio.url;
    }

    // Fallback to streaming endpoint
    return this.getAudioStreamUrl(audio.audio_id);
  },

  // Get available voices
  async getVoices() {
    const response = await apiClient.get('/voices');
    return response.data;
  },

  // Estimate processing cost
  async estimateCost(textLength: number, mode: 'full' | 'summary') {
    const response = await apiClient.post('/estimate-cost', {
      text_length: textLength,
      mode,
    });
    return response.data;
  },
};

export default audifyApi;