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
  }

  connect(chatId) {
    this.currentChatId = chatId;
    const token = localStorage.getItem('access_token');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/chat/${chatId}?token=${token}`;
    
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

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.isConnected = false;
      this.emit('disconnected');
      this.attemptReconnect();
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
      
      this.handleAudioChunk(messageId, chunkIndex, totalChunks, audioData);
    }
  }

  handleAudioChunk(messageId, chunkIndex, totalChunks, audioData) {
    if (!this.audioChunks.has(messageId)) {
      this.audioChunks.set(messageId, {
        chunks: new Array(totalChunks),
        received: 0,
      });
    }
    
    const audioInfo = this.audioChunks.get(messageId);
    audioInfo.chunks[chunkIndex] = audioData;
    audioInfo.received++;
    
    if (audioInfo.received === totalChunks) {
      this.reassembleAndPlayAudio(messageId);
    }
  }

  async reassembleAndPlayAudio(messageId) {
    const audioInfo = this.audioChunks.get(messageId);
    if (!audioInfo) return;
    
    const totalLength = audioInfo.chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const combinedAudio = new Uint8Array(totalLength);
    
    let offset = 0;
    for (const chunk of audioInfo.chunks) {
      combinedAudio.set(chunk, offset);
      offset += chunk.length;
    }
    
    const audioBlob = new Blob([combinedAudio], { type: 'audio/mp3' });
    this.emit('audioReceived', { messageId, audioBlob });
    
    this.audioChunks.delete(messageId);
  }

  send(message) {
    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      return true;
    } else {
      // Queue message for later sending
      this.messageQueue.push(message);
      return false;
    }
  }

  sendChatMessage(content) {
    return this.send({
      type: 'chat_message',
      content: content,
      timestamp: new Date().toISOString()
    });
  }

  sendAudioChunk(audioData) {
    if (!this.isConnected || !this.ws) return;
    
    if (audioData instanceof ArrayBuffer) {
      this.ws.send(audioData);
    } else if (audioData instanceof Uint8Array) {
      this.ws.send(audioData.buffer);
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
      this.ws.close();
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