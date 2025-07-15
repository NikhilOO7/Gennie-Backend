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
    
    // Configure backend URL based on environment
    this.backendHost = process.env.REACT_APP_BACKEND_URL || 'localhost:8000';
    // Remove any protocol from the backend host
    this.backendHost = this.backendHost.replace(/^https?:\/\//, '');
  }

  connect(chatId) {
    this.currentChatId = chatId;
    const token = localStorage.getItem('access_token');
    
    // Use the backend host instead of window.location.host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${this.backendHost}/api/v1/ws/chat/${chatId}?token=${token}`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    
    this.ws = new WebSocket(wsUrl);
    this.ws.binaryType = 'arraybuffer';
    
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      this.emit('connected');
      this.flushMessageQueue();
    };

    this.ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        this.handleBinaryMessage(event.data);
      } else {
        this.handleTextMessage(event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.isConnected = false;
      this.emit('disconnected');
      
      // Only attempt reconnect if it wasn't a normal closure
      if (event.code !== 1000 && event.code !== 1001) {
        this.attemptReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
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
      const messageIdLength = view.getUint32(1, true);
      const messageIdBytes = new Uint8Array(arrayBuffer, 5, messageIdLength);
      const messageId = new TextDecoder().decode(messageIdBytes);
      
      const offset = 5 + messageIdLength;
      const chunkIndex = view.getUint32(offset, true);
      const totalChunks = view.getUint32(offset + 4, true);
      const audioData = new Uint8Array(arrayBuffer, offset + 8);
      
      if (!this.audioChunks.has(messageId)) {
        this.audioChunks.set(messageId, new Array(totalChunks));
      }
      
      this.audioChunks.get(messageId)[chunkIndex] = audioData;
      
      // Check if all chunks received
      const chunks = this.audioChunks.get(messageId);
      if (chunks.every(chunk => chunk !== undefined)) {
        // Combine chunks
        const combinedAudio = audioStreamingUtils.combineAudioChunks(chunks);
        
        // Emit complete audio event
        this.emit('audio_received', {
          messageId,
          audioData: combinedAudio,
        });
        
        // Clean up
        this.audioChunks.delete(messageId);
      }
    }
  }

  send(message) {
    if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, queuing message');
      this.messageQueue.push(message);
    }
  }

  sendBinary(data) {
    if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      console.warn('WebSocket not connected, cannot send binary data');
    }
  }

  sendAudioData(audioData) {
    if (audioData instanceof ArrayBuffer || audioData instanceof Uint8Array) {
      this.ws.send(audioData.buffer || audioData);
    }
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
    if (this.ws) {
      this.ws.close(1000, 'Normal closure');
      this.ws = null;
    }
    this.isConnected = false;
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
}

export default new UnifiedWebSocketService();