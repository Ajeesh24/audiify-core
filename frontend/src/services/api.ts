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

const API_BASE_URL = getRuntimeApiUrl() || 'http://localhost:8000/api';

// Debug: Log the API URL being used
console.log('API Configuration:', {
  runtimeUrl: (window as any).ENV?.VITE_API_URL,
  buildTimeUrl: import.meta.env.VITE_API_URL,
  finalApiUrl: API_BASE_URL
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