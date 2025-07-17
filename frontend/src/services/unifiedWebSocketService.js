// services/unifiedWebSocketService.js
import audioStreamingUtils from '../utils/audioStreamingUtils';

class UnifiedWebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.isConnected = false;
    this.currentChatId = null;
    this.audioChunks = new Map();
    this.messageQueue = [];
    this.connectPromise = null;
    this.connectionTimeout = null;
    
    // Configure backend URL based on environment
    this.backendHost = process.env.REACT_APP_BACKEND_URL || 'localhost:8000';
    // Remove any protocol from the backend host
    this.backendHost = this.backendHost.replace(/^https?:\/\//, '');
  }

  connect(chatId) {
    // Prevent multiple simultaneous connections
    if (this.connectPromise) {
      return this.connectPromise;
    }

    // Clear any existing timeout
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }

    this.currentChatId = chatId;
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      console.error('No access token found');
      this.emit('error', new Error('No authentication token'));
      return Promise.reject(new Error('No authentication token'));
    }
    
    // Use the backend host instead of window.location.host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${this.backendHost}/api/v1/ws/chat/${chatId}?token=${token}`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    
    this.connectPromise = new Promise((resolve, reject) => {
      try {
        // Close existing connection if any
        if (this.ws) {
          this.ws.close(1000, 'Reconnecting');
        }
        
        this.ws = new WebSocket(wsUrl);
        this.ws.binaryType = 'arraybuffer';
        
        // Set a connection timeout
        this.connectionTimeout = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            console.error('WebSocket connection timeout');
            this.ws.close();
            reject(new Error('Connection timeout'));
          }
        }, 5000);
        
        this.setupEventHandlers(resolve, reject);
      } catch (error) {
        console.error('WebSocket connection error:', error);
        reject(error);
      }
    });
    
    return this.connectPromise;
  }

  setupEventHandlers(resolve, reject) {
    this.ws.onopen = () => {
      console.log('WebSocket connected successfully');
      
      // Clear connection timeout
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      this.connectPromise = null;
      
      // Emit connected event after a small delay to ensure listeners are ready
      setTimeout(() => {
        this.emit('connected');
      }, 0);
      
      this.flushMessageQueue();
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
      console.log('WebSocket disconnected:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      
      // Clear connection timeout
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      
      this.isConnected = false;
      this.connectPromise = null;
      this.emit('disconnected');
      
      // Only attempt reconnect if not a normal closure and not during initial connection
      if (event.code !== 1000 && event.code !== 1001 && this.currentChatId) {
        this.attemptReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      
      // Clear connection timeout
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      
      this.connectPromise = null;
      this.emit('error', error);
      
      // Reject the connection promise if we're still connecting
      if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
        reject(error);
      }
    };
  }

  handleTextMessage(data) {
    try {
      const message = JSON.parse(data);
      console.log('WebSocket message received:', message);
      
      // Emit the specific event type
      this.emit(message.type, message);
      
      // Also emit a general message event
      this.emit('message', message);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  handleBinaryMessage(arrayBuffer) {
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
    }
  }

  send(message) {
    if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, queueing message');
      this.messageQueue.push(message);
      return;
    }
    
    try {
      if (message instanceof Blob || message instanceof ArrayBuffer) {
        this.ws.send(message);
      } else {
        this.ws.send(JSON.stringify(message));
      }
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      this.messageQueue.push(message);
    }
  }

  sendChatMessage(content, metadata = {}) {
    this.send({
      type: 'chat_message',
      content,
      detect_emotion: true,
      metadata
    });
  }

  sendAudioChunk(chunk, sessionId, chunkIndex) {
    if (!this.isConnected) {
      console.warn('Cannot send audio chunk: WebSocket not connected');
      return;
    }
    
    const header = {
      type: 'audio_chunk',
      session_id: sessionId,
      chunk_index: chunkIndex
    };
    
    const headerBytes = new TextEncoder().encode(JSON.stringify(header));
    const message = new Blob([headerBytes, new Uint8Array([0x00]), chunk]);
    
    this.send(message);
  }

  startVoiceStream(config = {}) {
    this.send({
      type: 'voice_stream_start',
      ...config,
    });
  }

  endVoiceStream() {
    this.send({
      type: 'voice_stream_end',
    });
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('reconnect_failed');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      if (!this.isConnected && this.currentChatId) {
        this.connect(this.currentChatId);
      }
    }, this.reconnectDelay * this.reconnectAttempts);
  }

  flushMessageQueue() {
    while (this.messageQueue.length > 0 && this.isConnected) {
      const message = this.messageQueue.shift();
      this.send(message);
    }
  }

  disconnect() {
    // Clear any pending timeouts
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
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
    
    this.isConnected = false;
    this.currentChatId = null;
    this.connectPromise = null;
    this.listeners.clear();
    this.audioChunks.clear();
    this.messageQueue = [];
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket listener for event ${event}:`, error);
        }
      });
    }
  }

  get readyState() {
    return this.ws ? this.ws.readyState : WebSocket.CLOSED;
  }

  get connected() {
    return this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

const unifiedWebSocketService = new UnifiedWebSocketService();
export default unifiedWebSocketService;