class AudioService {
  constructor() {
    this.audioContext = null;
    this.audioCache = new Map();
    this.playbackQueue = [];
    this.currentAudio = null;
    this.isPlaying = false;
    this.audioElements = new Map();
  }
  
  initialize() {
    // Initialize audio context on first user interaction
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
  }
  
  async convertToWav(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = async () => {
        try {
          const arrayBuffer = reader.result;
          
          // Decode audio data
          const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
          
          // Convert to WAV
          const wavBuffer = this.audioBufferToWav(audioBuffer);
          const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
          
          resolve(wavBlob);
        } catch (error) {
          reject(error);
        }
      };
      
      reader.onerror = reject;
      reader.readAsArrayBuffer(blob);
    });
  }
  
  audioBufferToWav(audioBuffer) {
    const numChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const format = 1; // PCM
    const bitDepth = 16;
    
    const bytesPerSample = bitDepth / 8;
    const blockAlign = numChannels * bytesPerSample;
    
    const data = [];
    for (let i = 0; i < numChannels; i++) {
      data.push(audioBuffer.getChannelData(i));
    }
    
    const length = data[0].length;
    const arrayBuffer = new ArrayBuffer(44 + length * blockAlign);
    const view = new DataView(arrayBuffer);
    
    // WAV header
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * blockAlign, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true); // fmt chunk size
    view.setUint16(20, format, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitDepth, true);
    writeString(36, 'data');
    view.setUint32(40, length * blockAlign, true);
    
    // Interleave audio data
    let offset = 44;
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numChannels; channel++) {
        const sample = Math.max(-1, Math.min(1, data[channel][i]));
        const value = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        view.setInt16(offset, value, true);
        offset += 2;
      }
    }
    
    return arrayBuffer;
  }
  
  async playBase64Audio(base64Data, format = 'mp3') {
    try {
      // Convert base64 to blob
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: `audio/${format}` });
      
      // Create URL and play
      const url = URL.createObjectURL(blob);
      return this.playAudioUrl(url, true);
    } catch (error) {
      console.error('Error playing base64 audio:', error);
      throw error;
    }
  }
  
  async playAudioUrl(url, revokeAfterPlay = false) {
    return new Promise((resolve, reject) => {
      const audio = new Audio(url);
      const audioId = Date.now().toString();
      
      // Store reference
      this.audioElements.set(audioId, audio);
      
      audio.onended = () => {
        this.audioElements.delete(audioId);
        if (revokeAfterPlay) {
          URL.revokeObjectURL(url);
        }
        resolve();
      };
      
      audio.onerror = (error) => {
        this.audioElements.delete(audioId);
        if (revokeAfterPlay) {
          URL.revokeObjectURL(url);
        }
        reject(error);
      };
      
      audio.play().catch(reject);
    });
  }
  
  async playAudioBlob(blob) {
    const url = URL.createObjectURL(blob);
    return this.playAudioUrl(url, true);
  }
  
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
  }
  
  setVolume(volume) {
    const normalizedVolume = Math.max(0, Math.min(1, volume));
    this.audioElements.forEach(audio => {
      audio.volume = normalizedVolume;
    });
  }
  
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
      await this.playBase64Audio(data, format);
    } catch (error) {
      console.error('Queue playback error:', error);
    }
    
    // Process next item
    this.processQueue();
  }
  
  clearQueue() {
    this.playbackQueue = [];
  }
  
  async cacheAudio(key, audioData, format = 'mp3') {
    this.audioCache.set(key, { data: audioData, format });
  }
  
  async playCachedAudio(key) {
    const cached = this.audioCache.get(key);
    if (cached) {
      return this.playBase64Audio(cached.data, cached.format);
    }
    return null;
  }
  
  clearCache() {
    this.audioCache.clear();
  }
  
  // Audio analysis utilities
  async analyzeAudioBlob(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
    
    const data = audioBuffer.getChannelData(0);
    let sum = 0;
    let max = 0;
    
    for (let i = 0; i < data.length; i++) {
      const amplitude = Math.abs(data[i]);
      sum += amplitude;
      if (amplitude > max) max = amplitude;
    }
    
    return {
      duration: audioBuffer.duration,
      sampleRate: audioBuffer.sampleRate,
      channels: audioBuffer.numberOfChannels,
      averageAmplitude: sum / data.length,
      peakAmplitude: max,
    };
  }
  
  // Format conversion utilities
  async convertFormat(blob, targetFormat) {
    if (targetFormat === 'wav') {
      return this.convertToWav(blob);
    }
    
    // For other formats, we'd need additional libraries
    throw new Error(`Conversion to ${targetFormat} not implemented`);
  }
  
  // Audio chunking for streaming
  createAudioChunker(chunkSize = 4096, sampleRate = 16000) {
    const chunkDuration = chunkSize / sampleRate;
    
    return {
      chunkSize,
      sampleRate,
      chunkDuration,
      
      async* chunkAudioBlob(blob) {
        const arrayBuffer = await blob.arrayBuffer();
        const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
        const data = audioBuffer.getChannelData(0);
        
        for (let i = 0; i < data.length; i += chunkSize) {
          const chunk = data.slice(i, i + chunkSize);
          
          // Convert float32 to int16
          const int16Array = new Int16Array(chunk.length);
          for (let j = 0; j < chunk.length; j++) {
            const sample = Math.max(-1, Math.min(1, chunk[j]));
            int16Array[j] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
          }
          
          yield int16Array.buffer;
        }
      }
    };
  }
}

// Create singleton instance
const audioService = new AudioService();
export default audioService;