// services/api.js
import { API_BASE_URL } from '../utils/constants';
import { getErrorMessage } from '../utils/helpers';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(getErrorMessage(error));
      }
      
      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      return response;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Auth endpoints
  async login(credentials) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async register(userData) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async getCurrentUser() {
    return this.request('/users/me');
  }

  // Chat endpoints
  async getChats() {
    return this.request('/chat');
  }

  async deleteChat(chatId) {
    return this.request(`/chat/${chatId}`, {
      method: 'DELETE',
    });
  }

  async getChatMessages(chatId) {
    return this.request(`/chat/${chatId}/messages`);
  }

  async sendMessage(message, chatId, options = {}) {
    return this.request('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        chat_id: chatId,
        detect_emotion: true,
        enable_personalization: true,
        use_context: true,
        ...options
      }),
    });
  }

  // Voice endpoints
  async transcribeAudio(audioBlob, language = 'en-US') {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('language_code', language);
    
    return this.request('/voice/transcribe', {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders(),
        // Don't set Content-Type for FormData
      },
      body: formData,
    });
  }

  async synthesizeSpeech(text, options = {}) {
    try {
      const response = await this.request('/voice/synthesize', {
        method: 'POST',
        body: JSON.stringify({
          text,
          return_base64: true,
          voice_name: options.voice_name || null,
          language_code: options.language_code || 'en-US',
          audio_format: options.audio_format || 'mp3',
          speaking_rate: options.speaking_rate || 1.0,
          pitch: options.pitch || 0.0,
          ...options
        }),
      });
      
      return response;
    } catch (error) {
      console.error('TTS request failed:', error);
      // Try mock endpoint as fallback
      try {
        const mockResponse = await this.request('/voice/synthesize', {
          method: 'POST',
          headers: {
            ...this.getAuthHeaders(),
            'X-Use-Mock': 'true'  // Signal to use mock
          },
          body: JSON.stringify({
            text,
            return_base64: true,
            ...options
          }),
        });
        return mockResponse;
      } catch (mockError) {
        throw error; // Throw original error
      }
    }
  }

  // Additional endpoints
  async getHealthStatus() {
    return this.request('/health');
  }

  async getPersonalization() {
    return this.request('/ai/personalization');
  }

  async updatePersonalization(preferences) {
    return this.request('/ai/personalization', {
      method: 'PUT',
      body: JSON.stringify(preferences),
    });
  }

  async getRAGContext(messageId) {
    return this.request(`/ai/rag-context/${messageId}`);
  }

  async getUserStats() {
    return this.request('/users/me/stats');
  }

  async getVoices() {
    return this.request('/voice/voices');
  }

  async getUserTopics() {
    return this.request('/ai/topics');
  }

  async updateUserTopics(topics) {
    return this.request('/ai/topics', {
      method: 'PUT',
      body: JSON.stringify({ topics }),
    });
  }

  // Update createChat method
  async createChat(chatData) {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        title: chatData.title,
        description: chatData.description,
        chat_mode: chatData.mode || 'text',
        related_topic: chatData.topic || null
      }),
    });
  }

  async transcribeAudio(audioBlob, language = 'en-US') {
    const formData = new FormData();
    
    // Ensure the blob has a proper filename with extension
    const filename = audioBlob.type.includes('webm') ? 'recording.webm' : 'recording.wav';
    formData.append('audio', audioBlob, filename);
    formData.append('language_code', language);
    
    try {
      // Try the AI router endpoint which should exist
      const response = await fetch(`${this.baseURL}/ai/transcribe-audio`, {
        method: 'POST',
        headers: {
          ...this.getAuthHeaders(),
          // Don't set Content-Type for FormData - browser will set it with boundary
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Transcription failed');
      }

      const data = await response.json();
      
      // Ensure we have a transcript in the response
      if (!data.transcript) {
        throw new Error('No transcript in response');
      }
      
      return {
        transcript: data.transcript,
        confidence: data.confidence || 0,
        language: data.language || language,
        duration: data.duration || 0
      };
    } catch (error) {
      console.error('Transcription API error:', error);
      throw error;
    }
  }
}

export default new ApiService();