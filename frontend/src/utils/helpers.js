export const getErrorMessage = (error) => {
  if (typeof error === 'string') return error;
  if (error?.detail) {
    if (Array.isArray(error.detail)) {
      return error.detail.map(e => e.msg || e.message || 'Validation error').join(', ');
    }
    return error.detail;
  }
  if (error?.message) return error.message;
  if (error?.msg) return error.msg;
  return 'An error occurred';
};

export const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

export const formatDate = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleDateString();
};

export const playNotificationSound = (enabled = true) => {
  if (enabled) {
    const audio = new Audio('/notification.mp3');
    audio.play().catch(e => console.log('Could not play sound:', e));
  }
};

export const getStatusColor = (status) => {
  switch (status) {
    case 'healthy':
      return '#10b981';
    case 'degraded':
      return '#f59e0b';
    case 'unhealthy':
      return '#ef4444';
    default:
      return '#6b7280';
  }
};

export const saveToLocalStorage = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error('Error saving to localStorage:', error);
  }
};

export const getFromLocalStorage = (key, defaultValue = null) => {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.error('Error reading from localStorage:', error);
    return defaultValue;
  }
};

export const playSound = async (audioData, format = 'mp3') => {
  try {
    let audioUrl;
    
    // Handle different audio data formats
    if (typeof audioData === 'string' && audioData.startsWith('data:')) {
      // Already a data URL
      audioUrl = audioData;
    } else if (typeof audioData === 'string') {
      // Base64 string - convert to data URL
      // Clean the base64 string (remove any whitespace/newlines)
      const cleanBase64 = audioData.replace(/\s/g, '');
      audioUrl = `data:audio/${format};base64,${cleanBase64}`;
    } else if (audioData instanceof Blob) {
      // Blob - create object URL
      audioUrl = URL.createObjectURL(audioData);
    } else if (audioData instanceof ArrayBuffer) {
      // ArrayBuffer - convert to blob first
      const blob = new Blob([audioData], { type: `audio/${format}` });
      audioUrl = URL.createObjectURL(blob);
    } else {
      throw new Error('Unsupported audio data format');
    }
    
    // Create audio element
    const audio = new Audio();
    
    // Set up promise for playback completion
    const playPromise = new Promise((resolve, reject) => {
      audio.onended = () => {
        // Clean up object URLs to prevent memory leaks
        if (audioUrl.startsWith('blob:')) {
          URL.revokeObjectURL(audioUrl);
        }
        resolve();
      };
      
      audio.onerror = (error) => {
        // Clean up object URLs on error
        if (audioUrl.startsWith('blob:')) {
          URL.revokeObjectURL(audioUrl);
        }
        console.error('Audio playback error:', error);
        reject(new Error(`Failed to play audio: ${error.type || 'Unknown error'}`));
      };
      
      // Handle the case where audio might be blocked by browser
      audio.oncanplaythrough = () => {
        audio.play().catch(reject);
      };
    });
    
    // Set source and load
    audio.src = audioUrl;
    audio.load();
    
    return playPromise;
  } catch (error) {
    console.error('Error in playSound:', error);
    throw error;
  }
};

export const createSilentAudioWav = (durationMs = 100, sampleRate = 44100) => {
  const numSamples = Math.floor((durationMs / 1000) * sampleRate);
  const numChannels = 1;
  const bytesPerSample = 2; // 16-bit audio
  
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = numSamples * blockAlign;
  const fileSize = 44 + dataSize; // 44 bytes for WAV header
  
  const buffer = new ArrayBuffer(fileSize);
  const view = new DataView(buffer);
  
  // Write WAV header
  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  
  // RIFF header
  writeString(0, 'RIFF');
  view.setUint32(4, fileSize - 8, true); // File size - 8
  writeString(8, 'WAVE');
  
  // fmt chunk
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // Audio format (1 = PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true); // Bits per sample
  
  // data chunk
  writeString(36, 'data');
  view.setUint32(40, dataSize, true);
  
  // Write silence (all zeros)
  // No need to write anything as ArrayBuffer is already initialized with zeros
  
  // Convert to base64
  const blob = new Blob([buffer], { type: 'audio/wav' });
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.readAsDataURL(blob);
  });
};