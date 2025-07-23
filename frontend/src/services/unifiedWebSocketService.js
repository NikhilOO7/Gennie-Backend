// src/services/unifiedWebSocketService.js
// Complete unified service supporting both chat and voice streaming with proper connection state handling

import audioStreamingUtils from '../utils/audioStreamingUtils';

class OptimizedVoiceService {
    constructor() {
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.initialized = false;
    }
    
    async initialize() {
        if (!this.initialized) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.initialized = true;
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
    this.isFullyReady = false; // New flag to track when WebSocket is ready to receive messages
    this.currentChatId = null;
    this.connectionType = null; // 'chat' or 'voice'
    
    // Event handling
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
  }

  // Method to check connection status (for compatibility)
  isConnected() {
    return this._isConnected && this.isFullyReady && this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  // Alternative getter for isConnected property
  get connected() {
    return this._isConnected && this.isFullyReady && this.ws && this.ws.readyState === WebSocket.OPEN;
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
      console.error('No access token found');
      this.emit('error', { error: 'No access token found' });
      return Promise.reject(new Error('No access token found'));
    }

    // Chat WebSocket URL
    const wsUrl = `ws://localhost:8000/ws/chat/${chatId}?token=${token}`;
    
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
      console.error('No access token found');
      this.emit('error', { error: 'No access token found' });
      return Promise.reject(new Error('No access token found'));
    }

    // Voice stream WebSocket URL
    const wsUrl = `ws://localhost:8000/ws/voice/stream?token=${token}`;
    
    console.log('Connecting to Voice WebSocket:', wsUrl);
    
    return this.connectToWebSocket(wsUrl, config);
  }

  // Generic WebSocket connection method
  connectToWebSocket(wsUrl, config = {}) {
    // Clear any existing timeouts
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    if (this.readyTimeout) {
      clearTimeout(this.readyTimeout);
      this.readyTimeout = null;
    }

    this.connectPromise = new Promise((resolve, reject) => {
      try {
        // Close existing connection if any
        if (this.ws) {
          this.ws.close(1000, 'Reconnecting');
        }
        
        // Reset state
        this._isConnected = false;
        this.isFullyReady = false;
        this.messageQueue = [];
        
        this.ws = new WebSocket(wsUrl);
        this.ws.binaryType = 'arraybuffer';
        
        // Set a connection timeout
        this.connectionTimeout = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            console.error('WebSocket connection timeout');
            this.ws.close();
            reject(new Error('Connection timeout'));
          }
        }, 10000);
        
        this.setupEventHandlers(resolve, reject, config);
      } catch (error) {
        console.error('WebSocket connection error:', error);
        reject(error);
      }
    });
    
    return this.connectPromise;
  }

  setupEventHandlers(resolve, reject, config = {}) {
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
      
      // Wait a moment for the WebSocket to be fully ready, then send initial messages
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
      }, 150); // Wait 150ms for WebSocket to stabilize
      
      this.connectPromise = null;
      resolve();
    };

    this.ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        this.handleBinaryMessage(event.data);
      } else {
        this.handleTextMessage(event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.log(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket disconnected:`, {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      
      // Clear timeouts
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      if (this.readyTimeout) {
        clearTimeout(this.readyTimeout);
        this.readyTimeout = null;
      }
      
      this._isConnected = false;
      this.isFullyReady = false;
      this.connectPromise = null;
      this.emit('disconnected', { code: event.code, reason: event.reason });
      
      // Only attempt reconnect if not a normal closure
      if (event.code !== 1000 && event.code !== 1001) {
        this.attemptReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket error:`, error);
      
      // Clear timeouts
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      if (this.readyTimeout) {
        clearTimeout(this.readyTimeout);
        this.readyTimeout = null;
      }
      
      this.connectPromise = null;
      this.emit('error', { error: 'WebSocket connection error' });
      
      // Reject the connection promise if we're still connecting
      if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
        reject(error);
      }
    };
  }

  markAsFullyReady() {
    if (!this.isFullyReady) {
      this.isFullyReady = true;
      console.log(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket is fully ready`);
      
      // Emit connected event
      setTimeout(() => {
        this.emit('connected');
      }, 0);
      
      // Process queued messages
      this.flushMessageQueue();
    }
  }

  handleTextMessage(data) {
    try {
      const message = JSON.parse(data);
      console.log(`${this.connectionType === 'voice' ? 'Voice' : 'Chat'} WebSocket message received:`, message);
      
      // Handle specific message types
      switch (message.type) {
        case 'session_started':
          console.log('Voice session started:', message.session_id);
          // Mark as fully ready when voice session starts
          this.markAsFullyReady();
          break;
        case 'ai_message_complete':
          console.log('AI message complete');
          break;
        case 'transcript_interim':
        case 'transcript_final':
          console.log('Transcript received:', message.transcript);
          break;
        default:
          break;
      }
      
      // Emit the specific event type
      this.emit(message.type, message);
      
      // Also emit a general message event
      this.emit('message', message);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      this.emit('error', { error: 'Failed to parse message' });
    }
  }

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
          this.audioChunks.delete(messageId);
        }
      } else {
        // Handle other binary message types
        this.emit('binaryMessage', arrayBuffer);
      }
    } catch (error) {
      console.error('Error handling binary message:', error);
    }
  }

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
        this.ws.send(JSON.stringify(data));
      }
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      this.messageQueue.push(data);
      return false;
    }
  }

  // Chat-specific methods
  sendChatMessage(content, metadata = {}) {
    return this.send({
      type: 'message',
      content,
      detect_emotion: true,
      metadata
    });
  }

  // Voice-specific methods
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

  startRecording() {
    return this.send({
      type: 'start_recording'
    });
  }

  stopRecording() {
    return this.send({
      type: 'stop_recording'
    });
  }

  // Reconnection logic
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
          this.connect(this.currentChatId);
        } else if (this.connectionType === 'voice') {
          this.connectVoiceStream();
        }
      }
    }, delay);
  }

  scheduleReconnect() {
    // Alias for compatibility
    this.attemptReconnect();
  }

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

  disconnect() {
    // Clear any pending timeouts
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    if (this.readyTimeout) {
      clearTimeout(this.readyTimeout);
      this.readyTimeout = null;
    }
    
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
  }

  // Event handling methods (supporting both event systems)
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
        return this.isFullyReady ? 'ready' : 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }

  // Get current connection type
  getConnectionType() {
    return this.connectionType;
  }

  // Check if specific connection type is active
  isChatConnection() {
    return this.connectionType === 'chat' && this.isConnected();
  }

  isVoiceConnection() {
    return this.connectionType === 'voice' && this.isConnected();
  }

  // Get queue status
  getQueuedMessageCount() {
    return this.messageQueue.length;
  }

  // Manual ready state control (for debugging)
  forceReady() {
    if (this.isConnected && !this.isFullyReady) {
      console.warn('Forcing WebSocket to ready state');
      this.markAsFullyReady();
    }
  }
}

// Export singleton instance
const unifiedWebSocketService = new UnifiedWebSocketService();
export default unifiedWebSocketService;