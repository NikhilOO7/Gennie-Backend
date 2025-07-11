// services/enhancedAudioService.js
import audioStreamingUtils from '../utils/audioStreamingUtils';

class EnhancedAudioService {
  constructor() {
    this.audioContext = null;
    this.audioCache = new Map();
    this.playbackQueue = [];
    this.isPlaying = false;
    this.audioElements = new Map();
    this.bufferManager = null;
  }
  
  initialize() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioStreamingUtils.initialize();
    }
  }
  
  // Real-time streaming methods
  async startStreaming(onChunk) {
    this.initialize();
    this.bufferManager = audioStreamingUtils.createBufferManager();
    
    const stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 16000,
      } 
    });
    
    const source = await audioStreamingUtils.createStreamSource(stream);
    const processor = audioStreamingUtils.createStreamProcessor((chunk) => {
      onChunk(chunk);
    });
    
    source.connect(processor);
    processor.connect(this.audioContext.destination);
    
    return {
      stream,
      stop: () => {
        stream.getTracks().forEach(track => track.stop());
        processor.disconnect();
        source.disconnect();
      }
    };
  }
  
  // Enhanced audio playback with streaming support
  async playStreamedAudio(audioChunk) {
    if (!this.bufferManager) {
      this.bufferManager = audioStreamingUtils.createBufferManager();
    }
    this.bufferManager.addChunk(audioChunk);
  }
  
  // Convert and play audio with format detection
  async playAudio(audioData, format = 'mp3') {
    try {
      let audioUrl;
      
      if (typeof audioData === 'string' && audioData.startsWith('data:')) {
        // Data URL
        audioUrl = audioData;
      } else if (typeof audioData === 'string') {
        // Base64
        audioUrl = `data:audio/${format};base64,${audioData}`;
      } else if (audioData instanceof Blob) {
        // Blob
        audioUrl = URL.createObjectURL(audioData);
      } else if (audioData instanceof ArrayBuffer) {
        // ArrayBuffer
        const blob = new Blob([audioData], { type: `audio/${format}` });
        audioUrl = URL.createObjectURL(blob);
      }
      
      return this.playAudioUrl(audioUrl, true);
    } catch (error) {
      console.error('Error playing audio:', error);
      throw error;
    }
  }
  
  async playAudioUrl(url, revokeAfterPlay = false) {
    return new Promise((resolve, reject) => {
      const audio = new Audio(url);
      const audioId = Date.now().toString();
      
      this.audioElements.set(audioId, audio);
      
      audio.onended = () => {
        this.audioElements.delete(audioId);
        if (revokeAfterPlay && url.startsWith('blob:')) {
          URL.revokeObjectURL(url);
        }
        resolve();
      };
      
      audio.onerror = (error) => {
        this.audioElements.delete(audioId);
        if (revokeAfterPlay && url.startsWith('blob:')) {
          URL.revokeObjectURL(url);
        }
        reject(error);
      };
      
      audio.play().catch(reject);
    });
  }
  
  // Voice Activity Detection
  createVAD(options = {}) {
    return audioStreamingUtils.createVAD(options);
  }
  
  // Audio level monitoring
  createLevelMeter(callback, smoothing = 0.8) {
    this.initialize();
    return audioStreamingUtils.createLevelMeter(callback, smoothing);
  }
  
  // Format conversion
  async convertToWav(blob) {
    return audioStreamingUtils.convertToWav(blob);
  }
  
  // Queue management
  async queueAudio(audioData, format = 'mp3') {
    this.playbackQueue.push({ data: audioData, format });
    
    if (!this.isPlaying) {
      this.processQueue();
    }
  }
  
  async processQueue() {
    if (this.playbackQueue.length === 0) {
      this.isPlaying = false;
      return;
    }
    
    this.isPlaying = true;
    const { data, format } = this.playbackQueue.shift();
    
    try {
      await this.playAudio(data, format);
    } catch (error) {
      console.error('Queue playback error:', error);
    }
    
    this.processQueue();
  }
  
  // Control methods
  pauseAll() {
    this.audioElements.forEach(audio => {
      if (!audio.paused) {
        audio.pause();
      }
    });
  }
  
  stopAll() {
    this.audioElements.forEach((audio, id) => {
      audio.pause();
      audio.currentTime = 0;
      this.audioElements.delete(id);
    });
    
    if (this.bufferManager) {
      this.bufferManager.clear();
    }
  }
  
  setVolume(volume) {
    const normalizedVolume = Math.max(0, Math.min(1, volume));
    this.audioElements.forEach(audio => {
      audio.volume = normalizedVolume;
    });
  }
  
  // Cleanup
  cleanup() {
    this.stopAll();
    this.audioCache.clear();
    this.playbackQueue = [];
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

export default new EnhancedAudioService();