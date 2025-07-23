// services/enhancedAudioService.js
class EnhancedAudioService {
  constructor() {
    this.websocket = null;
    this.isConnected = false;
    this.eventListeners = new Map();
    this.audioContext = null;
    this.mediaRecorder = null;
    this.audioStream = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    
    // Audio processing settings
    this.audioConfig = {
      sampleRate: 16000,
      channels: 1,
      bitDepth: 16,
      bufferSize: 4096,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    };
    
    // Quality metrics
    this.sessionStats = {
      totalMessages: 0,
      averageLatency: 0,
      audioQuality: 'high',
      connectionQuality: 'good'
    };
  }

  // Event handling
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);
  }

  off(event, callback) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  // WebSocket connection management
  async connect(sessionConfig = {}) {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No authentication token available');
      }

      const wsUrl = `ws://localhost:8000/ws/voice/stream?token=${token}`;
      this.websocket = new WebSocket(wsUrl);

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Connection timeout'));
        }, 10000);

        this.websocket.onopen = () => {
          clearTimeout(timeout);
          console.log('Enhanced voice WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          
          // Send initial configuration
          this.send({
            type: 'start_session',
            config: {
              ...this.audioConfig,
              ...sessionConfig
            }
          });

          this.emit('connected', { sessionConfig });
          resolve();
        };

        this.websocket.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.websocket.onclose = (event) => {
          clearTimeout(timeout);
          this.handleDisconnection(event);
        };

        this.websocket.onerror = (error) => {
          clearTimeout(timeout);
          console.error('Enhanced voice WebSocket error:', error);
          this.emit('error', { error });
          reject(error);
        };
      });
    } catch (error) {
      console.error('Failed to connect enhanced voice service:', error);
      this.emit('error', { error });
      throw error;
    }
  }

  disconnect() {
    if (this.websocket) {
      this.websocket.close(1000, 'Client disconnect');
    }
    this.cleanup();
  }

  handleMessage(event) {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'session_started':
          this.emit('session_started', data);
          break;
          
        case 'transcript_interim':
          this.emit('transcript_interim', {
            transcript: data.transcript,
            confidence: data.confidence,
            is_final: false
          });
          break;
          
        case 'transcript_final':
          this.emit('transcript_final', {
            transcript: data.transcript,
            confidence: data.confidence,
            is_final: true,
            emotion: data.emotion
          });
          break;
          
        case 'audio_chunk':
          this.emit('audio_chunk', {
            audioData: data.audio_data,
            format: data.format,
            chunk_id: data.chunk_id
          });
          break;
          
        case 'tts_complete':
          this.emit('tts_complete', {
            audioUrl: data.audio_url,
            duration: data.duration,
            message_id: data.message_id
          });
          break;
          
        case 'emotion_detected':
          this.emit('emotion_detected', {
            emotion: data.emotion,
            confidence: data.confidence,
            valence: data.valence,
            arousal: data.arousal
          });
          break;
          
        case 'session_stats':
          this.sessionStats = { ...this.sessionStats, ...data.stats };
          this.emit('session_stats', this.sessionStats);
          break;
          
        case 'error':
          this.emit('error', { error: data.error, code: data.code });
          break;
          
        default:
          console.log('Unknown message type:', data.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  handleDisconnection(event) {
    console.log('Enhanced voice WebSocket disconnected:', event.code, event.reason);
    this.isConnected = false;
    this.emit('disconnected', { code: event.code, reason: event.reason });
    
    // Attempt reconnection unless it was a clean close
    if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.attemptReconnection();
    }
  }

  async attemptReconnection() {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
    this.emit('reconnecting', { attempt: this.reconnectAttempts, delay });
    
    setTimeout(async () => {
      try {
        await this.connect();
      } catch (error) {
        console.error('Reconnection failed:', error);
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.emit('reconnection_failed', { error });
        }
      }
    }, delay);
  }

  send(data) {
    if (this.websocket && this.isConnected) {
      this.websocket.send(JSON.stringify(data));
      return true;
    } else {
      console.warn('Cannot send message: WebSocket not connected');
      return false;
    }
  }

  // Audio recording functionality
  async startRecording(options = {}) {
    try {
      // Request microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          ...this.audioConfig,
          echoCancellation: options.echoCancellation ?? this.audioConfig.echoCancellation,
          noiseSuppression: options.noiseSuppression ?? this.audioConfig.noiseSuppression,
          autoGainControl: options.autoGainControl ?? this.audioConfig.autoGainControl
        }
      });

      // Create audio context for analysis
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.audioConfig.sampleRate
      });

      // Set up media recorder
      const mimeType = this.getSupportedMimeType();
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType,
        audioBitsPerSecond: 128000
      });

      const audioChunks = [];
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
          
          // Send real-time audio data
          if (this.isConnected) {
            const reader = new FileReader();
            reader.onloadend = () => {
              const base64Data = reader.result.split(',')[1];
              this.send({
                type: 'audio_chunk',
                audio_data: base64Data,
                format: mimeType.split('/')[1],
                timestamp: Date.now()
              });
            };
            reader.readAsDataURL(event.data);
          }
        }
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: mimeType });
        this.emit('recording_complete', { audioBlob, format: mimeType });
      };

      // Start recording with small timeslices for real-time streaming
      this.mediaRecorder.start(100); // 100ms chunks
      
      this.emit('recording_started');
      return true;

    } catch (error) {
      console.error('Failed to start recording:', error);
      this.emit('error', { error });
      return false;
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
    }
    
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }
    
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    this.emit('recording_stopped');
  }

  getSupportedMimeType() {
    const mimeTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/mpeg',
      'audio/wav'
    ];
    
    for (const mimeType of mimeTypes) {
      if (MediaRecorder.isTypeSupported(mimeType)) {
        return mimeType;
      }
    }
    
    return 'audio/webm'; // Fallback
  }

  // Configuration updates
  updateConfig(newConfig) {
    this.audioConfig = { ...this.audioConfig, ...newConfig };
    
    if (this.isConnected) {
      this.send({
        type: 'update_config',
        config: this.audioConfig
      });
    }
  }

  // Get current session statistics
  getSessionStats() {
    return { ...this.sessionStats };
  }

  // Cleanup
  cleanup() {
    this.stopRecording();
    
    if (this.websocket) {
      this.websocket = null;
    }
    
    this.isConnected = false;
    this.eventListeners.clear();
  }

  // Quality assessment
  assessAudioQuality(audioLevel, latency) {
    let quality = 'high';
    
    if (latency > 2000 || audioLevel < 0.1) {
      quality = 'low';
    } else if (latency > 1000 || audioLevel < 0.3) {
      quality = 'medium';
    }
    
    this.sessionStats.audioQuality = quality;
    return quality;
  }

  // Connection quality assessment
  assessConnectionQuality(latency, packetLoss = 0) {
    let quality = 'good';
    
    if (latency > 500 || packetLoss > 0.05) {
      quality = 'poor';
    } else if (latency > 200 || packetLoss > 0.02) {
      quality = 'fair';
    }
    
    this.sessionStats.connectionQuality = quality;
    return quality;
  }
}

// Export singleton instance
const enhancedAudioService = new EnhancedAudioService();
export default enhancedAudioService;