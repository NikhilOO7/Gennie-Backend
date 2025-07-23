// src/services/unifiedWebSocketService.js
// Complete unified WebSocket service with ALL original functionality preserved + fixes

class OptimizedVoiceService {
    constructor() {
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.initialized = false;
    }
    
    async initialize() {
        if (!this.initialized) {
            try {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                if (this.audioContext.state === 'suspended') {
                    await this.audioContext.resume();
                }
                this.initialized = true;
                console.log('Audio context initialized successfully');
            } catch (error) {
                console.error('Failed to initialize audio context:', error);
                throw error;
            }
        }
    }
    
    // Pre-buffer audio chunks
    async bufferAudioChunk(audioData) {
        await this.initialize();
        try {
            const audioBuffer = await this.audioContext.decodeAudioData(audioData);
            this.audioQueue.push(audioBuffer);
            
            if (!this.isPlaying) {
                this.playNextChunk();
            }
        } catch (error) {
            console.error('Error buffering audio chunk:', error);
        }
    }
    
    async playNextChunk() {
        if (this.audioQueue.length === 0) {
            this.isPlaying = false;
            return;
        }
        
        this.isPlaying = true;
        const buffer = this.audioQueue.shift();
        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(this.audioContext.destination);
        source.onended = () => this.playNextChunk();
        source.start();
    }
    
    cleanup() {
        this.audioQueue = [];
        this.isPlaying = false;
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
        this.initialized = false;
    }
}

class UnifiedWebSocketService {
  constructor() {
    // Connection state
    this.ws = null;
    this._isConnected = false; // Renamed to avoid conflict
    this.isFullyReady = false; // Flag to track when WebSocket is ready to receive messages
    this.currentChatId = null;
    this.connectionType = null; // 'chat' or 'voice'
    
    // Event handling - dual system for compatibility
    this.eventListeners = new Map();
    this.listeners = new Map(); // Alternative event system for compatibility
    
    // Reconnection logic
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.connectionTimeout = null;
    this.connectPromise = null;
    this.readyTimeout = null;
    
    // Message handling
    this.messageQueue = [];
    
    // Audio handling
    this.audioChunks = new Map();
    this.voiceService = new OptimizedVoiceService();
    
    // Backend configuration
    this.backendHost = process.env.REACT_APP_BACKEND_URL || 'localhost:8000';
    this.backendHost = this.backendHost.replace(/^https?:\/\//, '');
    
    // Health check functionality
    this.healthCheckInterval = null;
    this.lastHealthCheck = null;
  }

  // Connection status methods (preserving ALL original methods)
  isConnected() {
    return this._isConnected && this.isFullyReady && this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  // Alternative getter for isConnected property
  get connected() {
    return this._isConnected && this.isFullyReady && this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  // Utility methods
  getReadyState() {
    return this.ws ? this.ws.readyState : WebSocket.CLOSED;
  }

  get readyState() {
    return this.getReadyState();
  }

  getConnectionStatus() {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return this.isFullyReady ? 'connected' : 'opening';
      case WebSocket.CLOSING:
        return 'disconnecting';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }

  // Health check methods
  async checkBackendHealth() {
    try {
      const response = await fetch(`http://${this.backendHost}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000)
      });
      
      if (response.ok) {
        const data = await response.json();
        this.lastHealthCheck = { success: true, timestamp: Date.now(), data };
        console.log('Backend health check passed:', data);
        return true;
      } else {
        this.lastHealthCheck = { success: false, timestamp: Date.now(), status: response.status };
        console.warn('Backend health check failed:', response.status);
        return false;
      }
    } catch (error) {
      this.lastHealthCheck = { success: false, timestamp: Date.now(), error: error.message };
      console.error('Backend health check error:', error);
      return false;
    }
  }

  startHealthChecks() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
    
    this.checkBackendHealth();
    this.healthCheckInterval = setInterval(() => {
      this.checkBackendHealth();
    }, 30000);
  }

  stopHealthChecks() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  // Connect to chat WebSocket
  connect(chatId) {
    if (this.connectPromise && this.connectionType === 'chat' && this.currentChatId === chatId) {
      return this.connectPromise;
    }

    this.connectionType = 'chat';
    this.currentChatId = chatId;
    
    const token = localStorage.getItem('access_token');
    if (!token) {
      const error = new Error('No access token found');
      console.error('Authentication error:', error);
      this.emit('error', { error: error.message });
      return Promise.reject(error);
    }

    // Check backend health first
    this.checkBackendHealth().then(isHealthy => {
      if (!isHealthy) {
        console.warn('Backend health check failed, but attempting connection anyway...');
      }
    });

    // Chat WebSocket URL
    const wsUrl = `ws://${this.backendHost}/ws/chat/${chatId}?token=${token}`;
    
    console.log('Connecting to Chat WebSocket:', wsUrl);
    
    return this.connectToWebSocket(wsUrl);
  }

  // Connect to voice stream WebSocket
  connectVoiceStream(config = {}) {
    if (this.connectPromise && this.connectionType === 'voice') {
      return this.connectPromise;
    }

    this.connectionType = 'voice';
    
    const token = localStorage.getItem('access_token');
    if (!token) {
      const error = new Error('No access token found');
      console.error('Authentication error:', error);
      this.emit('error', { error: error.message });
      return Promise.reject(error);
    }

    // Check backend health first
    this.checkBackendHealth().then(isHealthy => {
      if (!isHealthy) {
        console.warn('Backend health check failed, but attempting voice connection anyway...');
      }
    });

    // Voice stream WebSocket URL
    const wsUrl = `ws://${this.backendHost}/ws/voice/stream?token=${token}`;
    
    console.log('Connecting to Voice WebSocket:', wsUrl);
    
    return this.connectToWebSocket(wsUrl, config);
  }

  // Generic WebSocket connection method
  connectToWebSocket(wsUrl, config = {}) {
    // Clear any existing timeouts
    this.clearTimeouts();

    this.connectPromise = new Promise((resolve, reject) => {
      try {
        // Close existing connection
        if (this.ws) {
          this.ws.close(1000, 'Reconnecting');
          this.ws = null;
        }

        // Reset state
        this._isConnected = false;
        this.isFullyReady = false;

        // Create new WebSocket connection
        this.ws = new WebSocket(wsUrl);

        // Connection timeout
        this.connectionTimeout = setTimeout(() => {
          console.error(`${this.connectionType} WebSocket connection timeout`);
          if (this.ws) {
            this.ws.close(1000, 'Connection timeout');
          }
          reject(new Error('Connection timeout'));
        }, 10000);

        this.ws.onopen = () => {
          console.log(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket connected successfully`);
          
          // Clear connection timeout
          if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
          }
          
          this._isConnected = true;
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;
          
          // Wait a moment for the WebSocket to be fully ready
          this.readyTimeout = setTimeout(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
              // Send voice session configuration if connecting to voice stream
              if (this.connectionType === 'voice') {
                try {
                  this.ws.send(JSON.stringify({
                    type: 'start_session',
                    language_code: config.language || 'en-US',
                    voice_name: config.voice || 'en-US-Neural2-F',
                    sample_rate: config.sampleRate || 16000,
                    interim_results: true,
                    enable_emotion_detection: config.emotionDetection || true,
                    enable_rag: config.enableRAG || true,
                    enhancement_level: config.enhancementLevel || 'standard'
                  }));
                  console.log('Voice session configuration sent');
                } catch (error) {
                  console.error('Error sending voice session config:', error);
                }
              } else {
                // For chat connections, mark ready immediately
                this.markAsFullyReady();
              }
            }
          }, 150);
          
          this.connectPromise = null;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            if (event.data instanceof ArrayBuffer) {
              this.handleBinaryMessage(event.data);
            } else {
              this.handleTextMessage(event.data);
            }
          } catch (error) {
            console.error('Error handling WebSocket message:', error);
            this.emit('error', { error: 'Message handling error', details: error.message });
          }
        };

        this.ws.onclose = (event) => {
          console.log(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket disconnected:`, {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          });
          
          this.clearTimeouts();
          this._isConnected = false;
          this.isFullyReady = false;
          this.connectPromise = null;
          
          this.emit('disconnected', { code: event.code, reason: event.reason });
          
          // Only attempt reconnect if not a normal closure and we haven't exceeded max attempts
          if (event.code !== 1000 && event.code !== 1001 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket error:`, error);
          
          this.clearTimeouts();
          this.connectPromise = null;
          
          // Emit proper error message - FIXED: ensure error is always a string
          this.emit('error', { 
            error: 'WebSocket connection error',
            details: error.message || 'Connection failed',
            type: this.connectionType
          });
          
          // Reject the connection promise if we're still connecting
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            reject(new Error('WebSocket connection failed'));
          }
        };

      } catch (error) {
        console.error('Error creating WebSocket:', error);
        reject(error);
      }
    });

    return this.connectPromise;
  }

  // Clear all timeouts
  clearTimeouts() {
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    if (this.readyTimeout) {
      clearTimeout(this.readyTimeout);
      this.readyTimeout = null;
    }
  }

  // Mark WebSocket as fully ready
  markAsFullyReady() {
    if (!this.isFullyReady) {
      this.isFullyReady = true;
      console.log(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket is fully ready`);
      
      // Emit connected event
      setTimeout(() => {
        this.emit('connected', { type: this.connectionType });
      }, 0);
      
      // Process queued messages
      this.flushMessageQueue();
      
      // Start health checks
      this.startHealthChecks();
    }
  }

  // Handle text messages - FIXED: proper error string handling
  handleTextMessage(data) {
    try {
      const message = JSON.parse(data);
      console.log(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket message received:`, message);
      
      // Handle specific message types
      switch (message.type) {
        case 'session_started':
        case 'voice_session_ready':
          console.log('Voice session started:', message.session_id);
          this.markAsFullyReady();
          break;
          
        case 'error':
          // FIXED: Properly handle error messages - ensure error is always a string
          const errorMessage = typeof message.error === 'string' ? message.error : 
                              (message.error?.message || JSON.stringify(message.error) || 'Unknown error');
          console.error('WebSocket error message received:', errorMessage);
          this.emit('error', { error: errorMessage, source: 'server' });
          break;
          
        case 'ai_message_complete':
          console.log('AI message complete');
          this.emit('message', message);
          break;
          
        case 'transcript':
        case 'transcript_interim':
        case 'transcript_final':
          console.log('Transcript received:', message.transcript || message.text);
          this.emit('transcript', message);
          break;
          
        case 'audio_chunk':
          this.handleAudioChunk(message);
          break;
          
        default:
          // Emit the specific event type
          this.emit(message.type, message);
          break;
      }
      
      // Also emit a general message event
      this.emit('message', message);
      
    } catch (error) {
      console.error('Error parsing WebSocket message:', error, 'Raw data:', data);
      this.emit('error', { error: 'Message parsing error', details: error.message });
    }
  }

  // Handle binary messages (audio data)
  handleBinaryMessage(arrayBuffer) {
    try {
      const view = new DataView(arrayBuffer);
      const messageType = view.getUint8(0);
      
      if (messageType === 0x01) { // Audio chunk
        const messageId = new TextDecoder().decode(new Uint8Array(arrayBuffer, 1, 36));
        const chunkIndex = view.getUint32(37, true);
        const totalChunks = view.getUint32(41, true);
        const audioData = arrayBuffer.slice(45);
        
        if (!this.audioChunks.has(messageId)) {
          this.audioChunks.set(messageId, new Map());
        }
        
        const chunks = this.audioChunks.get(messageId);
        chunks.set(chunkIndex, audioData);
        
        if (chunks.size === totalChunks) {
          const orderedChunks = [];
          for (let i = 0; i < totalChunks; i++) {
            orderedChunks.push(chunks.get(i));
          }
          
          const completeAudio = new Blob(orderedChunks, { type: 'audio/mp3' });
          this.emit('audioReceived', { messageId, audioBlob: completeAudio });
          
          // Clean up chunks
          this.audioChunks.delete(messageId);
        }
      } else {
        // Handle other binary message types
        this.emit('binaryMessage', arrayBuffer);
      }
    } catch (error) {
      console.error('Error handling binary message:', error);
      this.emit('error', { error: 'Binary message handling error', details: error.message });
    }
  }

  // Handle audio chunks
  handleAudioChunk(message) {
    try {
      if (message.audio_data) {
        // Convert base64 to binary and play
        const audioData = Uint8Array.from(atob(message.audio_data), c => c.charCodeAt(0));
        this.voiceService.bufferAudioChunk(audioData.buffer);
      }
      this.emit('audio_chunk', message);
    } catch (error) {
      console.error('Error handling audio chunk:', error);
      this.emit('error', { error: 'Audio chunk handling error', details: error.message });
    }
  }

  // Send message - preserving ALL original functionality
  send(data) {
    if (!this.isConnected() || !this.ws) {
      console.warn('WebSocket not fully ready, queueing message:', data);
      this.messageQueue.push(data);
      return false;
    }
    
    try {
      if (data instanceof Blob || data instanceof ArrayBuffer) {
        this.ws.send(data);
      } else {
        const messageStr = typeof data === 'string' ? data : JSON.stringify(data);
        this.ws.send(messageStr);
      }
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      this.messageQueue.push(data);
      this.emit('error', { error: 'Send message error', details: error.message });
      return false;
    }
  }

  // Chat-specific methods (preserving ALL original methods)
  sendChatMessage(content, metadata = {}) {
    return this.send({
      type: 'message',
      content,
      detect_emotion: true,
      metadata
    });
  }

  // Voice-specific methods (preserving ALL original methods)
  sendAudioChunk(chunk, sessionId, chunkIndex) {
    if (!this.isConnected()) {
      console.warn('Cannot send audio chunk: WebSocket not ready');
      return false;
    }
    
    const header = {
      type: 'audio_chunk',
      session_id: sessionId,
      chunk_index: chunkIndex
    };
    
    const headerBytes = new TextEncoder().encode(JSON.stringify(header));
    const message = new Blob([headerBytes, new Uint8Array([0x00]), chunk]);
    
    return this.send(message);
  }

  startVoiceStream(config = {}) {
    return this.send({
      type: 'voice_stream_start',
      ...config,
    });
  }

  endVoiceStream() {
    return this.send({
      type: 'voice_stream_end',
    });
  }

  startRecording(options = {}) {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      return;
    }
    this.audioChunksRef = [];
    navigator.mediaDevices.getUserMedia({
      audio: {
        ...this.audioConfig,
        ...options,
      }
    }).then(stream => {
      this.audioStream = stream;
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: this.getSupportedMimeType(),
        audioBitsPerSecond: 128000,
      });
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.send(event.data);
        }
      };
      this.mediaRecorder.start(100);
      this.emit('recording_started');
    }).catch(error => {
      this.emit('error', { error });
    });
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
      this.audioStream.getTracks().forEach(track => track.stop());
      this.emit('recording_stopped');
    }
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
    return 'audio/webm';
  }

  // Flush message queue
  flushMessageQueue() {
    if (!this.isConnected()) {
      console.log('Cannot flush message queue: WebSocket not ready');
      return;
    }

    console.log(`Flushing ${this.messageQueue.length} queued messages`);
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      try {
        if (message instanceof Blob || message instanceof ArrayBuffer) {
          this.ws.send(message);
        } else {
          this.ws.send(JSON.stringify(message));
        }
      } catch (error) {
        console.error('Error sending queued message:', error);
        // Put it back at the front of the queue
        this.messageQueue.unshift(message);
        break;
      }
    }
  }

  // Reconnection logic (preserving ALL original functionality)
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('reconnect_failed');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts), 30000);
    
    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);
    
    setTimeout(() => {
      if (!this.isConnected()) {
        if (this.connectionType === 'chat' && this.currentChatId) {
          this.connect(this.currentChatId).catch(error => {
            console.error('Reconnection failed:', error);
          });
        } else if (this.connectionType === 'voice') {
          this.connectVoiceStream().catch(error => {
            console.error('Reconnection failed:', error);
          });
        }
      }
    }, delay);
  }

  // Alias for compatibility
  scheduleReconnect() {
    this.attemptReconnect();
  }

  // Event handling methods (supporting both event systems) - preserving ALL original functionality
  on(event, callback) {
    // Primary event system
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);
    
    // Secondary event system for compatibility
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    // Primary event system
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
    
    // Secondary event system
    const altListeners = this.listeners.get(event);
    if (altListeners) {
      const index = altListeners.indexOf(callback);
      if (index > -1) {
        altListeners.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    // Primary event system
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
    
    // Secondary event system
    const altListeners = this.listeners.get(event);
    if (altListeners) {
      altListeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in alt event listener for ${event}:`, error);
        }
      });
    }
  }

  // Disconnect - preserving ALL original functionality
  disconnect() {
    console.log('Disconnecting WebSocket service');
    
    this.stopHealthChecks();
    this.clearTimeouts();
    
    if (this.ws) {
      // Remove all event handlers before closing
      this.ws.onopen = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close(1000, 'Normal closure');
      }
      this.ws = null;
    }
    
    this._isConnected = false;
    this.isFullyReady = false;
    this.currentChatId = null;
    this.connectionType = null;
    this.connectPromise = null;
    this.messageQueue = [];
    
    // Cleanup voice service
    this.voiceService.cleanup();
    
    // Clear event listeners
    this.eventListeners.clear();
    this.listeners.clear();
  }

  // Get connection status - enhanced version
  getStatus() {
    return {
      connected: this.isConnected(),
      type: this.connectionType,
      chatId: this.currentChatId,
      reconnectAttempts: this.reconnectAttempts,
      queuedMessages: this.messageQueue.length,
      lastHealthCheck: this.lastHealthCheck,
      readyState: this.ws ? this.ws.readyState : null,
      connectionStatus: this.getConnectionStatus()
    };
  }
}

// Create and export singleton instance
const unifiedWebSocketService = new UnifiedWebSocketService();

export default unifiedWebSocketService;