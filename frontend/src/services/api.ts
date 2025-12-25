import axios from 'axios';

// API client configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes timeout for TTS generation
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use((config) => {
  console.log(`Making API request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
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
}

export interface ProcessArticleResponse {
  success: boolean;
  article?: ArticleContent;
  audio?: AudioResponse;
  error?: string;
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

  // Process article
  async processArticle(request: ArticleProcessRequest): Promise<ProcessArticleResponse> {
    const response = await apiClient.post('/process-article', request);
    return response.data;
  },

  // Get audio stream URL
  getAudioStreamUrl(audioId: string): string {
    return `${API_BASE_URL}/audio/${audioId}`;
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