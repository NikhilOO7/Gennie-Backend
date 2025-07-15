// utils/audioStreamingUtils.js

class AudioStreamingUtils {
  constructor() {
    this.audioContext = null;
    this.workletNode = null;
    this.sourceNode = null;
    this.isStreaming = false;
    this.audioBufferQueue = [];
    this.isProcessing = false;
  }

  // Initialize audio context
  async initialize() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
        latencyHint: 'interactive'
      });
    }
    
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
    
    return this.audioContext;
  }

  // Add the missing createBufferManager method
  createBufferManager() {
    return {
      chunks: [],
      add: function(chunk) {
        this.chunks.push(chunk);
      },
      clear: function() {
        this.chunks = [];
      },
      getAll: function() {
        return this.chunks;
      },
      combine: function() {
        const totalLength = this.chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const combined = new Uint8Array(totalLength);
        let offset = 0;
        for (const chunk of this.chunks) {
          combined.set(chunk, offset);
          offset += chunk.length;
        }
        return combined;
      }
    };
  }

  // Existing initializeAudioContext method - rename to avoid confusion
  async initializeAudioContext() {
    return this.initialize();
  }

  // Convert audio blob to array buffer
  async blobToArrayBuffer(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = reject;
      reader.readAsArrayBuffer(blob);
    });
  }

  // Convert Float32Array to Int16Array for transmission
  float32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  }

  // Convert Int16Array to Float32Array for playback
  int16ToFloat32(int16Array) {
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
    }
    return float32Array;
  }

  // Resample audio data
  async resampleAudio(audioData, fromSampleRate, toSampleRate) {
    if (fromSampleRate === toSampleRate) {
      return audioData;
    }

    const ratio = toSampleRate / fromSampleRate;
    const newLength = Math.round(audioData.length * ratio);
    const result = new Float32Array(newLength);

    for (let i = 0; i < newLength; i++) {
      const index = i / ratio;
      const indexFloor = Math.floor(index);
      const indexCeil = Math.ceil(index);
      const interpolation = index - indexFloor;

      if (indexCeil >= audioData.length) {
        result[i] = audioData[audioData.length - 1];
      } else {
        result[i] = audioData[indexFloor] * (1 - interpolation) + 
                   audioData[indexCeil] * interpolation;
      }
    }

    return result;
  }

  // Process audio chunk for streaming
  async processAudioChunk(chunk, format = 'int16') {
    try {
      let audioData;
      
      if (chunk instanceof ArrayBuffer) {
        if (format === 'int16') {
          const int16Array = new Int16Array(chunk);
          audioData = this.int16ToFloat32(int16Array);
        } else if (format === 'float32') {
          audioData = new Float32Array(chunk);
        }
      } else if (chunk instanceof Float32Array) {
        audioData = chunk;
      } else if (chunk instanceof Int16Array) {
        audioData = this.int16ToFloat32(chunk);
      } else {
        throw new Error('Unsupported audio chunk format');
      }

      return audioData;
    } catch (error) {
      console.error('Error processing audio chunk:', error);
      throw error;
    }
  }

  // Create audio buffer from data
  createAudioBuffer(audioData, sampleRate) {
    const audioBuffer = this.audioContext.createBuffer(
      1, // mono
      audioData.length,
      sampleRate
    );
    
    audioBuffer.getChannelData(0).set(audioData);
    return audioBuffer;
  }

  // Play audio buffer
  async playAudioBuffer(audioBuffer) {
    return new Promise((resolve) => {
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      source.onended = resolve;
      source.start();
    });
  }

  // Stream audio data
  async streamAudioData(audioDataStream) {
    this.isStreaming = true;
    this.audioBufferQueue = [];

    try {
      for await (const chunk of audioDataStream) {
        if (!this.isStreaming) break;
        
        const audioData = await this.processAudioChunk(chunk);
        const audioBuffer = this.createAudioBuffer(audioData, 16000);
        
        this.audioBufferQueue.push(audioBuffer);
        
        if (!this.isProcessing) {
          this.processAudioQueue();
        }
      }
    } catch (error) {
      console.error('Error streaming audio:', error);
      throw error;
    }
  }

  // Process queued audio buffers
  async processAudioQueue() {
    if (this.isProcessing || this.audioBufferQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.audioBufferQueue.length > 0 && this.isStreaming) {
      const audioBuffer = this.audioBufferQueue.shift();
      await this.playAudioBuffer(audioBuffer);
    }

    this.isProcessing = false;
  }

  // Stop streaming
  stopStreaming() {
    this.isStreaming = false;
    this.audioBufferQueue = [];
    this.isProcessing = false;
  }

  // Get audio level from analyzer
  getAudioLevel(analyser) {
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);
    
    const average = dataArray.reduce((a, b) => a + b, 0) / bufferLength;
    return average / 255;
  }

  // Create media stream from audio chunks
  async createMediaStream(audioChunks, mimeType = 'audio/webm') {
    const audioBlob = new Blob(audioChunks, { type: mimeType });
    const audioUrl = URL.createObjectURL(audioBlob);
    
    const audio = new Audio(audioUrl);
    await audio.play();
    
    return {
      blob: audioBlob,
      url: audioUrl,
      cleanup: () => URL.revokeObjectURL(audioUrl)
    };
  }

  // Convert audio blob to WAV format
  async convertToWav(audioBlob) {
    const arrayBuffer = await this.blobToArrayBuffer(audioBlob);
    const audioContext = await this.initializeAudioContext();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    
    // Extract audio data
    const channelData = audioBuffer.getChannelData(0);
    const sampleRate = audioBuffer.sampleRate;
    
    // Convert to 16-bit PCM
    const length = channelData.length * 2;
    const buffer = new ArrayBuffer(44 + length);
    const view = new DataView(buffer);
    
    // WAV header
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length, true);
    
    // Convert float samples to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < channelData.length; i++) {
      const sample = Math.max(-1, Math.min(1, channelData[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      offset += 2;
    }
    
    return new Blob([buffer], { type: 'audio/wav' });
  }

  // Cleanup resources
  cleanup() {
    this.stopStreaming();
    
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

export default new AudioStreamingUtils();