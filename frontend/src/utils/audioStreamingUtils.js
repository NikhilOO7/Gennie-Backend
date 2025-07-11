class AudioStreamingUtils {
  constructor() {
    this.audioContext = null;
    this.sampleRate = 16000;
    this.chunkDuration = 100; // ms
    this.chunkSize = null;
  }
  
  initialize() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.chunkSize = Math.floor(this.sampleRate * this.chunkDuration / 1000);
    }
  }
  
  // Convert Float32Array to Int16Array
  floatTo16BitPCM(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    }
    return int16Array;
  }
  
  // Convert Int16Array to Float32Array
  int16ToFloat32(int16Array) {
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
    }
    return float32Array;
  }
  
  // Create audio chunks from MediaRecorder data
  async createChunksFromBlob(blob, chunkDuration = 100) {
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
    
    const channelData = audioBuffer.getChannelData(0);
    const sampleRate = audioBuffer.sampleRate;
    const chunkSize = Math.floor(sampleRate * chunkDuration / 1000);
    
    const chunks = [];
    for (let i = 0; i < channelData.length; i += chunkSize) {
      const chunk = channelData.slice(i, i + chunkSize);
      const int16Chunk = this.floatTo16BitPCM(chunk);
      chunks.push(int16Chunk.buffer);
    }
    
    return chunks;
  }
  
  // Reassemble chunks into audio buffer
  reassembleChunks(chunks) {
    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
    const combinedBuffer = new ArrayBuffer(totalLength);
    const combinedView = new Uint8Array(combinedBuffer);
    
    let offset = 0;
    for (const chunk of chunks) {
      const chunkView = new Uint8Array(chunk);
      combinedView.set(chunkView, offset);
      offset += chunk.byteLength;
    }
    
    return combinedBuffer;
  }
  
  // Create streaming audio processor
  createStreamProcessor(onChunk, options = {}) {
    const {
      bufferSize = 4096,
      inputChannels = 1,
      outputChannels = 1,
    } = options;
    
    this.initialize();
    
    const processor = this.audioContext.createScriptProcessor(
      bufferSize,
      inputChannels,
      outputChannels
    );
    
    processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      const int16Data = this.floatTo16BitPCM(inputData);
      
      if (onChunk) {
        onChunk(int16Data.buffer);
      }
    };
    
    return processor;
  }
  
  // Create media stream source for real-time processing
  async createStreamSource(stream) {
    this.initialize();
    return this.audioContext.createMediaStreamSource(stream);
  }
  
  // Buffer manager for smooth playback
  createBufferManager(targetBufferTime = 500) {
    const bufferQueue = [];
    let isPlaying = false;
    let nextPlayTime = 0;
    
    const addChunk = (audioData) => {
      bufferQueue.push(audioData);
      if (!isPlaying) {
        playNext();
      }
    };
    
    const playNext = async () => {
      if (bufferQueue.length === 0) {
        isPlaying = false;
        return;
      }
      
      isPlaying = true;
      const chunk = bufferQueue.shift();
      
      // Convert to audio buffer
      const int16Array = new Int16Array(chunk);
      const float32Array = this.int16ToFloat32(int16Array);
      
      const audioBuffer = this.audioContext.createBuffer(
        1,
        float32Array.length,
        this.sampleRate
      );
      audioBuffer.getChannelData(0).set(float32Array);
      
      // Play buffer
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      
      const currentTime = this.audioContext.currentTime;
      const startTime = Math.max(currentTime, nextPlayTime);
      source.start(startTime);
      
      nextPlayTime = startTime + audioBuffer.duration;
      
      // Schedule next chunk
      const timeUntilNext = (nextPlayTime - currentTime) * 1000;
      setTimeout(playNext, Math.max(0, timeUntilNext - 50));
    };
    
    return {
      addChunk,
      clear: () => {
        bufferQueue.length = 0;
        isPlaying = false;
        nextPlayTime = 0;
      },
      getBufferSize: () => bufferQueue.length,
    };
  }
  
  // Voice activity detection
  createVAD(options = {}) {
    const {
      threshold = 0.01,
      minSilenceDuration = 300,
      minSpeechDuration = 100,
    } = options;
    
    let speechStart = null;
    let silenceStart = null;
    let isSpeaking = false;
    
    const processSample = (audioData, sampleRate) => {
      const float32Array = audioData instanceof Float32Array 
        ? audioData 
        : this.int16ToFloat32(new Int16Array(audioData));
      
      // Calculate RMS
      let sum = 0;
      for (let i = 0; i < float32Array.length; i++) {
        sum += float32Array[i] * float32Array[i];
      }
      const rms = Math.sqrt(sum / float32Array.length);
      
      const currentTime = Date.now();
      
      if (rms > threshold) {
        // Voice detected
        if (!isSpeaking) {
          speechStart = currentTime;
          isSpeaking = true;
          silenceStart = null;
        }
      } else {
        // Silence detected
        if (isSpeaking) {
          if (!silenceStart) {
            silenceStart = currentTime;
          } else if (currentTime - silenceStart >= minSilenceDuration) {
            // End of speech
            const speechDuration = silenceStart - speechStart;
            if (speechDuration >= minSpeechDuration) {
              isSpeaking = false;
              return {
                type: 'speechEnd',
                duration: speechDuration,
              };
            }
          }
        }
      }
      
      return {
        type: isSpeaking ? 'speaking' : 'silence',
        level: rms,
      };
    };
    
    return { processSample };
  }
  
  // Audio level meter
  createLevelMeter(callback, smoothing = 0.8) {
    this.initialize();
    
    const analyser = this.audioContext.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = smoothing;
    
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    let animationId = null;
    
    const update = () => {
      analyser.getByteFrequencyData(dataArray);
      
      // Calculate average level
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
      }
      const average = sum / dataArray.length;
      const normalizedLevel = average / 255;
      
      callback(normalizedLevel);
      
      animationId = requestAnimationFrame(update);
    };
    
    const start = () => {
      update();
    };
    
    const stop = () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
      }
    };
    
    return {
      analyser,
      start,
      stop,
    };
  }
  
  // Utility to convert audio blob to WAV format
  async convertToWav(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
    
    const length = audioBuffer.length;
    const numberOfChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    
    // Create WAV file
    const wavBuffer = new ArrayBuffer(44 + length * 2 * numberOfChannels);
    const view = new DataView(wavBuffer);
    
    // WAV header
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * 2 * numberOfChannels, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * 2 * numberOfChannels, true);
    
    // Convert float samples to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const sample = audioBuffer.getChannelData(channel)[i];
        const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        view.setInt16(offset, int16, true);
        offset += 2;
      }
    }
    
    return new Blob([wavBuffer], { type: 'audio/wav' });
  }
}

// Create singleton instance
const audioStreamingUtils = new AudioStreamingUtils();
export default audioStreamingUtils;