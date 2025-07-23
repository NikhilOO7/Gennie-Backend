// components/voice/EnhancedVoiceInterface.js
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Settings, Activity, Waves } from 'lucide-react';
import VoiceVisualizer from './VoiceVisualizer';
import VoiceControls from './VoiceControls';
import VoiceSettings from './VoiceSettings';
import AudioPlayer from './AudioPlayer';
import enhancedAudioService from '../../services/enhancedAudioService';
import './EnhancedVoiceInterface.css';

const EnhancedVoiceInterface = ({ 
  onTranscript, 
  onAudioResponse, 
  isConnected,
  className = "" 
}) => {
  // State management
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [voiceSettings, setVoiceSettings] = useState({
    voice: 'en-US-Neural2-F',
    speed: 1.0,
    pitch: 0.0,
    language: 'en-US',
    enableEnhancement: true,
    emotionDetection: true
  });
  const [connectionQuality, setConnectionQuality] = useState('disconnected');
  const [sessionStats, setSessionStats] = useState({
    totalMessages: 0,
    averageLatency: 0,
    audioQuality: 'high'
  });
  const [showSettings, setShowSettings] = useState(false);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isWebSocketReady, setIsWebSocketReady] = useState(false);

  // Refs
  const websocketRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);
  const animationFrameRef = useRef(null);
  const audioChunksRef = useRef([]);
  const reconnectTimeoutRef = useRef(null);
  const messageQueueRef = useRef([]);
  const readyStateRef = useRef(false);

  // Enhanced audio processing settings
  const audioConfig = useMemo(() => ({
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16,
    bufferSize: 4096,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  }), []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'session_started':
        console.log('Voice session started:', data.session_id);
        setConnectionQuality('good');
        setIsWebSocketReady(true);
        readyStateRef.current = true;
        // Process any queued messages
        flushMessageQueue();
        break;

      case 'transcription':
      case 'transcript_interim':
      case 'transcript_final':
        const transcript = data.transcript || data.text;
        if (transcript) {
          setCurrentTranscript(transcript);
          if (onTranscript) {
            onTranscript({
              text: transcript,
              confidence: data.confidence || 0.9,
              isFinal: data.is_final || data.isFinal || false,
              processingTime: data.processing_time_ms || 0,
              words: data.words || []
            });
          }
        }
        break;

      case 'ai_response_chunk':
        if (data.audio_data) {
          playAudioChunk(data.audio_data, data.audio_format || 'mp3');
        }
        break;

      case 'ai_response_complete':
        setIsProcessing(false);
        updateSessionStats();
        break;

      case 'session_stats':
        setSessionStats(data.stats);
        break;

      case 'error':
        console.error('Voice session error:', data.error);
        setIsProcessing(false);
        setConnectionQuality('poor');
        break;

      case 'keepalive':
        setConnectionQuality('good');
        break;

      case 'echo':
        console.log('WebSocket echo received:', data);
        break;

      default:
        console.log('Unknown message type:', data.type, data);
    }
  }, [onTranscript]);

  // Queue messages when WebSocket isn't ready
  const queueMessage = useCallback((message) => {
    messageQueueRef.current.push(message);
  }, []);

  // Flush queued messages when WebSocket is ready
  const flushMessageQueue = useCallback(() => {
    if (websocketRef.current?.readyState === WebSocket.OPEN && readyStateRef.current) {
      while (messageQueueRef.current.length > 0) {
        const message = messageQueueRef.current.shift();
        try {
          websocketRef.current.send(JSON.stringify(message));
        } catch (error) {
          console.error('Error sending queued message:', error);
        }
      }
    }
  }, []);

  // Safe message sending
  const sendMessage = useCallback((message) => {
    if (websocketRef.current?.readyState === WebSocket.OPEN && readyStateRef.current) {
      try {
        websocketRef.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Error sending message:', error);
        queueMessage(message);
        return false;
      }
    } else {
      queueMessage(message);
      return false;
    }
  }, [queueMessage]);

  // Schedule reconnection
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    reconnectTimeoutRef.current = setTimeout(() => {
      if (websocketRef.current?.readyState !== WebSocket.OPEN) {
        console.log('Attempting to reconnect...');
        connectWithFallback();
      }
    }, 3000);
  }, []);

  // Initialize enhanced WebSocket connection
  const initializeWebSocket = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No authentication token');
      }

      // Try enhanced voice WebSocket first
      const wsUrl = `ws://localhost:8000/ws/voice/stream?token=${token}`;
      
      console.log('Attempting to connect to voice WebSocket:', wsUrl);
      
      websocketRef.current = new WebSocket(wsUrl);
      setIsWebSocketReady(false);
      readyStateRef.current = false;

      return new Promise((resolve, reject) => {
        const connectionTimeout = setTimeout(() => {
          console.error('WebSocket connection timeout');
          setConnectionQuality('disconnected');
          reject(new Error('Connection timeout'));
        }, 10000);

        websocketRef.current.onopen = () => {
          clearTimeout(connectionTimeout);
          console.log('Voice WebSocket connected successfully');
          setConnectionQuality('good');
          
          // Wait a brief moment before marking as ready and sending configuration
          setTimeout(() => {
            if (websocketRef.current?.readyState === WebSocket.OPEN) {
              // Send session configuration
              const configMessage = {
                type: 'start_session',
                language_code: voiceSettings.language,
                voice_name: voiceSettings.voice,
                sample_rate: audioConfig.sampleRate,
                interim_results: true,
                enable_emotion_detection: voiceSettings.emotionDetection,
                enable_rag: true,
                enhancement_level: voiceSettings.enableEnhancement ? 'high' : 'standard'
              };
              
              try {
                websocketRef.current.send(JSON.stringify(configMessage));
                console.log('Session configuration sent');
              } catch (error) {
                console.error('Error sending session config:', error);
                // Don't reject, let the session_started handler set ready state
              }
            }
          }, 100); // Small delay to ensure WebSocket is fully ready
          
          resolve();
        };

        websocketRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        websocketRef.current.onclose = (event) => {
          clearTimeout(connectionTimeout);
          console.log('Voice WebSocket closed:', event.code, event.reason);
          setConnectionQuality('disconnected');
          setIsWebSocketReady(false);
          readyStateRef.current = false;
          
          // Only attempt reconnection if it wasn't a normal closure
          if (event.code !== 1000) {
            scheduleReconnect();
          }
        };

        websocketRef.current.onerror = (error) => {
          clearTimeout(connectionTimeout);
          console.error('Voice WebSocket error:', error);
          setConnectionQuality('poor');
          setIsWebSocketReady(false);
          readyStateRef.current = false;
          
          // Check if WebSocket is in CONNECTING state (readyState 0) or CLOSED state (readyState 3)
          if (websocketRef.current?.readyState === WebSocket.CONNECTING || 
              websocketRef.current?.readyState === WebSocket.CLOSED) {
            console.log('WebSocket failed to connect, will attempt fallback');
            reject(new Error('WebSocket connection failed'));
          }
        };
      });

    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      setConnectionQuality('disconnected');
      setIsWebSocketReady(false);
      readyStateRef.current = false;
      throw error;
    }
  }, [voiceSettings, audioConfig, handleWebSocketMessage, scheduleReconnect]);

  // Add a fallback connection method
  const initializeFallbackWebSocket = useCallback(async (chatId = 'voice-session') => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No authentication token');
      }

      // Fallback to basic chat WebSocket
      const wsUrl = `ws://localhost:8000/ws/chat/${chatId}?token=${token}`;
      
      console.log('Attempting fallback WebSocket connection:', wsUrl);
      
      websocketRef.current = new WebSocket(wsUrl);
      setIsWebSocketReady(false);
      readyStateRef.current = false;

      return new Promise((resolve, reject) => {
        const connectionTimeout = setTimeout(() => {
          console.error('Fallback WebSocket connection timeout');
          setConnectionQuality('disconnected');
          reject(new Error('Fallback connection timeout'));
        }, 5000);

        websocketRef.current.onopen = () => {
          clearTimeout(connectionTimeout);
          console.log('Fallback WebSocket connected successfully');
          setConnectionQuality('good');
          
          // Wait a moment then mark as ready and send test message
          setTimeout(() => {
            if (websocketRef.current?.readyState === WebSocket.OPEN) {
              try {
                websocketRef.current.send(JSON.stringify({
                  type: 'voice_session_init',
                  message: 'Enhanced voice interface connected via fallback'
                }));
                setIsWebSocketReady(true);
                readyStateRef.current = true;
                flushMessageQueue();
              } catch (error) {
                console.error('Error sending fallback init message:', error);
              }
            }
          }, 100);
          
          resolve();
        };

        websocketRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('Fallback WebSocket message:', data);
            handleWebSocketMessage(data);
          } catch (error) {
            console.error('Error parsing fallback WebSocket message:', error);
          }
        };

        websocketRef.current.onclose = (event) => {
          clearTimeout(connectionTimeout);
          console.log('Fallback WebSocket closed:', event.code, event.reason);
          setConnectionQuality('disconnected');
          setIsWebSocketReady(false);
          readyStateRef.current = false;
        };

        websocketRef.current.onerror = (error) => {
          clearTimeout(connectionTimeout);
          console.error('Fallback WebSocket error:', error);
          setConnectionQuality('disconnected');
          setIsWebSocketReady(false);
          readyStateRef.current = false;
          reject(error);
        };
      });

    } catch (error) {
      console.error('Failed to initialize fallback WebSocket:', error);
      setConnectionQuality('disconnected');
      setIsWebSocketReady(false);
      readyStateRef.current = false;
      throw error;
    }
  }, [handleWebSocketMessage, flushMessageQueue]);

  // Update the main initialization to try fallback
  const connectWithFallback = useCallback(async () => {
    try {
      // Try enhanced voice WebSocket first
      await initializeWebSocket();
    } catch (error) {
      console.log('Enhanced voice WebSocket failed, trying fallback...');
      try {
        await initializeFallbackWebSocket();
        console.log('Fallback WebSocket connected successfully');
      } catch (fallbackError) {
        console.error('Both WebSocket connections failed:', fallbackError);
        setConnectionQuality('disconnected');
        setIsWebSocketReady(false);
        readyStateRef.current = false;
      }
    }
  }, [initializeWebSocket, initializeFallbackWebSocket]);

  // Initialize audio context and media stream
  const initializeAudio = useCallback(async () => {
    try {
      // Request microphone access with enhanced constraints
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: audioConfig.sampleRate,
          channelCount: audioConfig.channels,
          echoCancellation: audioConfig.echoCancellation,
          noiseSuppression: audioConfig.noiseSuppression,
          autoGainControl: audioConfig.autoGainControl,
          sampleSize: audioConfig.bitDepth
        }
      });

      streamRef.current = stream;

      // Create audio context for analysis
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: audioConfig.sampleRate
      });

      // Create analyser for audio visualization
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.8;

      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      // Start audio level monitoring
      startAudioLevelMonitoring();

      // Initialize MediaRecorder with optimized settings
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 128000
      });

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && websocketRef.current?.readyState === WebSocket.OPEN && readyStateRef.current) {
          // Send audio data directly as binary
          websocketRef.current.send(event.data);
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
      };

      console.log('Audio initialized successfully');
      return true;

    } catch (error) {
      console.error('Failed to initialize audio:', error);
      return false;
    }
  }, [audioConfig]);

  // Start audio level monitoring
  const startAudioLevelMonitoring = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    
    const updateAudioLevel = () => {
      if (analyserRef.current) {
        analyserRef.current.getByteFrequencyData(dataArray);
        
        // Calculate RMS (Root Mean Square) for better level detection
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length);
        const level = rms / 255; // Normalize to 0-1
        
        setAudioLevel(level);
        
        animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
      }
    };
    
    updateAudioLevel();
  }, []);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      if (!streamRef.current) {
        const audioInitialized = await initializeAudio();
        if (!audioInitialized) {
          throw new Error('Failed to initialize audio');
        }
      }

      if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
        await connectWithFallback();
        // Wait for connection and ready state
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Connection timeout')), 5000);
          const checkConnection = () => {
            if (websocketRef.current?.readyState === WebSocket.OPEN && readyStateRef.current) {
              clearTimeout(timeout);
              resolve();
            } else if (websocketRef.current?.readyState === WebSocket.CLOSED) {
              clearTimeout(timeout);
              reject(new Error('WebSocket connection failed'));
            } else {
              setTimeout(checkConnection, 100);
            }
          };
          checkConnection();
        });
      }

      // Start recording
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
        audioChunksRef.current = [];
        mediaRecorderRef.current.start(100); // Send chunks every 100ms
        
        // Send start recording command
        sendMessage({
          type: 'start_recording'
        });
        
        setIsRecording(true);
        setCurrentTranscript('');
        console.log('Recording started');
      }

    } catch (error) {
      console.error('Failed to start recording:', error);
      setIsRecording(false);
    }
  }, [initializeAudio, connectWithFallback, sendMessage]);

  // Stop recording
  const stopRecording = useCallback(() => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
        
        // Send stop recording command
        sendMessage({
          type: 'stop_recording'
        });
        
        setIsRecording(false);
        setIsProcessing(true);
        console.log('Recording stopped');
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
      setIsRecording(false);
    }
  }, [sendMessage]);

  // Play audio chunk
  const playAudioChunk = useCallback(async (audioData, format) => {
    try {
      setIsPlaying(true);
      
      // Decode base64 audio data
      const binaryData = atob(audioData);
      const bytes = new Uint8Array(binaryData.length);
      for (let i = 0; i < binaryData.length; i++) {
        bytes[i] = binaryData.charCodeAt(i);
      }

      // Create audio blob and play
      const audioBlob = new Blob([bytes], { type: `audio/${format}` });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.onerror = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
      
      if (onAudioResponse) {
        onAudioResponse({ audioUrl, format });
      }

    } catch (error) {
      console.error('Failed to play audio chunk:', error);
      setIsPlaying(false);
    }
  }, [onAudioResponse]);

  // Update session statistics
  const updateSessionStats = useCallback(() => {
    sendMessage({
      type: 'get_stats'
    });
  }, [sendMessage]);

  // Handle voice settings change
  const handleSettingsChange = useCallback((newSettings) => {
    setVoiceSettings(prev => ({ ...prev, ...newSettings }));
    
    // Update session configuration
    sendMessage({
      type: 'update_config',
      config: {
        voice_name: newSettings.voice || voiceSettings.voice,
        language_code: newSettings.language || voiceSettings.language,
        enhancement_level: (newSettings.enableEnhancement ?? voiceSettings.enableEnhancement) ? 'high' : 'standard'
      }
    });
  }, [voiceSettings, sendMessage]);

  // Toggle recording
  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  // Initialize on mount
  useEffect(() => {
    connectWithFallback();
    
    return () => {
      // Cleanup
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
      
      if (websocketRef.current) {
        websocketRef.current.close();
      }
      
      // Clear refs
      setIsWebSocketReady(false);
      readyStateRef.current = false;
      messageQueueRef.current = [];
    };
  }, []); // Empty dependency array to avoid infinite loop

  // Connection quality indicator
  const getConnectionIndicator = () => {
    const indicators = {
      good: { color: '#10b981', icon: Activity, text: 'Connected' },
      poor: { color: '#f59e0b', icon: Activity, text: 'Poor Connection' },
      disconnected: { color: '#ef4444', icon: Activity, text: 'Disconnected' }
    };
    
    const indicator = indicators[connectionQuality];
    const Icon = indicator.icon;
    
    return (
      <div className="connection-indicator" style={{ color: indicator.color }}>
        <Icon size={16} />
        <span>{indicator.text}</span>
      </div>
    );
  };

  return (
    <div className={`enhanced-voice-interface ${className}`}>
      {/* Header with connection status */}
      <div className="voice-header">
        <div className="voice-title">
          <Waves size={20} />
          <span>Enhanced Voice Chat</span>
        </div>
        {getConnectionIndicator()}
        <button 
          className="settings-btn"
          onClick={() => setShowSettings(!showSettings)}
          aria-label="Voice Settings"
        >
          <Settings size={18} />
        </button>
      </div>

      {/* Settings panel */}
      {showSettings && (
        <VoiceSettings 
          settings={voiceSettings}
          onSettingsChange={handleSettingsChange}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* Main voice interface */}
      <div className="voice-main">
        {/* Audio visualizer */}
        <VoiceVisualizer 
          audioLevel={audioLevel}
          isRecording={isRecording}
          isProcessing={isProcessing}
          isPlaying={isPlaying}
          className="voice-visualizer"
        />

        {/* Current transcript display */}
        {currentTranscript && (
          <div className="current-transcript">
            <div className="transcript-label">Transcript:</div>
            <div className="transcript-text">{currentTranscript}</div>
          </div>
        )}

        {/* Recording button */}
        <div className="recording-section">
          <button
            className={`record-button ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''}`}
            onClick={toggleRecording}
            disabled={isProcessing || connectionQuality === 'disconnected' || !isWebSocketReady}
            aria-label={isRecording ? 'Stop Recording' : 'Start Recording'}
          >
            {isRecording ? <MicOff size={32} /> : <Mic size={32} />}
          </button>
          
          <div className="record-status">
            {isRecording && <span className="recording-indicator">Recording...</span>}
            {isProcessing && <span className="processing-indicator">Processing...</span>}
            {!isRecording && !isProcessing && (
              <span className="ready-indicator">
                {connectionQuality === 'disconnected' ? 'Reconnecting...' : 
                 !isWebSocketReady ? 'Initializing...' : 'Ready to record'}
              </span>
            )}
          </div>
        </div>

        {/* Voice controls */}
        <VoiceControls 
          voiceSettings={voiceSettings}
          onSettingsChange={handleSettingsChange}
          sessionStats={sessionStats}
          connectionQuality={connectionQuality}
        />
      </div>

      {/* Session statistics */}
      <div className="session-stats">
        <div className="stat-item">
          <span className="stat-label">Messages:</span>
          <span className="stat-value">{sessionStats.totalMessages}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg Latency:</span>
          <span className="stat-value">{sessionStats.averageLatency.toFixed(0)}ms</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Quality:</span>
          <span className={`stat-value quality-${sessionStats.audioQuality}`}>
            {sessionStats.audioQuality}
          </span>
        </div>
      </div>
    </div>
  );
};

export default EnhancedVoiceInterface;