// components/voice/EnhancedVoiceInterface.js
// EXACT original UI structure with ONLY functional fixes applied

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Settings, Activity, Waves } from 'lucide-react';
import VoiceVisualizer from './VoiceVisualizer';
import VoiceControls from './VoiceControls';
import VoiceSettings from './VoiceSettings';
import AudioPlayer from './AudioPlayer';
import enhancedAudioService from '../../services/enhancedAudioService';
import UnifiedWebSocketService from '../../services/UnifiedWebSocketService';
import './EnhancedVoiceInterface.css';

const EnhancedVoiceInterface = ({ 
  onTranscript, 
  onAudioResponse, 
  isConnected,
  className = "" 
}) => {
  // State management - EXACT original state structure
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

  // Refs - EXACT original refs structure
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

  // Enhanced audio processing settings - EXACT original config
  const audioConfig = useMemo(() => ({
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16,
    bufferSize: 4096,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  }), []);

  // Play audio chunk - original functionality
  const playAudioChunk = useCallback((audioData, format = 'mp3') => {
    try {
      const audioBlob = new Blob([audioData], { type: `audio/${format}` });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onplay = () => setIsPlaying(true);
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      audio.onerror = (error) => {
        console.error('Audio playback error:', error);
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.play().catch(error => {
        console.error('Failed to play audio:', error);
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      });
    } catch (error) {
      console.error('Error playing audio chunk:', error);
    }
  }, []);

  // Update session stats - original functionality
  const updateSessionStats = useCallback(() => {
    setSessionStats(prev => ({
      ...prev,
      totalMessages: prev.totalMessages + 1,
    }));
  }, []);

  // Handle WebSocket messages - EXACT original message handling with fixes
  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'session_started':
        console.log('Voice session started:', data.session_id);
        setConnectionQuality('good');
        setIsWebSocketReady(true);
        readyStateRef.current = true;
        flushMessageQueue();
        break;

      case 'transcription':
      case 'transcript_interim':
      case 'transcript_final':
      case 'transcript':
        const transcript = data.transcript || data.text || data.content;
        if (transcript) {
          setCurrentTranscript(transcript);
          if (onTranscript) {
            onTranscript({
              text: transcript,
              confidence: data.confidence || 0.9,
              isFinal: data.is_final || data.isFinal || data.type === 'transcript_final',
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
      case 'ai_message_complete':
        setIsProcessing(false);
        updateSessionStats();
        break;

      case 'session_stats':
        setSessionStats(data.stats);
        break;

      case 'error':
        // FIXED: Proper error string handling
        const errorMessage = typeof data.error === 'string' ? data.error : 
                              (data.error?.message || JSON.stringify(data.error));
        console.error('Voice session error:', errorMessage);
        setIsProcessing(false);
        setConnectionQuality('poor');
        break;

      case 'audio_chunk':
        if (data.audio_data) {
          playAudioChunk(data.audio_data, data.format || 'mp3');
        }
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
  }, [onTranscript, playAudioChunk, updateSessionStats]);

  // Queue messages when WebSocket isn't ready - original functionality
  const queueMessage = useCallback((message) => {
    messageQueueRef.current.push(message);
  }, []);

  // Flush queued messages when WebSocket is ready - original functionality
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

  // Safe message sending - original functionality with fixes
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

  // Schedule reconnection - original functionality
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

  // Initialize WebSocket - FIXED: Uses unified service
  const initializeWebSocket = useCallback(async () => {
    try {
      console.log('Initializing enhanced voice WebSocket...');
      
      // Use unified WebSocket service
      await UnifiedWebSocketService.connectVoiceStream(voiceSettings);
      
      // Set up event listeners
      UnifiedWebSocketService.on('connected', () => {
        console.log('Enhanced voice WebSocket connected');
        setIsWebSocketReady(true);
        readyStateRef.current = true;
        setConnectionQuality('good');
      });

      UnifiedWebSocketService.on('message', handleWebSocketMessage);
      UnifiedWebSocketService.on('transcript', handleWebSocketMessage);
      UnifiedWebSocketService.on('audio_chunk', handleWebSocketMessage);

      UnifiedWebSocketService.on('error', (errorData) => {
        console.error('WebSocket service error:', errorData);
        setConnectionQuality('poor');
      });

      UnifiedWebSocketService.on('disconnected', (event) => {
        console.log('WebSocket disconnected:', event);
        setIsWebSocketReady(false);
        readyStateRef.current = false;
        setConnectionQuality('disconnected');
        scheduleReconnect();
      });

    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      setConnectionQuality('disconnected');
      throw error;
    }
  }, [voiceSettings, handleWebSocketMessage, scheduleReconnect]);

  // Add fallback WebSocket initialization - original functionality
  const initializeFallbackWebSocket = useCallback(async (chatId = 'voice-session') => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No authentication token');
      }

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
          // Always send an initial message for protocol compliance
          try {
            websocketRef.current.send(JSON.stringify({
              type: 'ping',
              message: 'Initial handshake from frontend'
            }));
          } catch (error) {
            console.error('Error sending initial handshake message:', error);
          }
          setIsWebSocketReady(true);
          readyStateRef.current = true;
          flushMessageQueue();
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

  // Connect with fallback - original functionality with fixes
  const connectWithFallback = useCallback(async () => {
    try {
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

  // Initialize audio context and media stream - original functionality
  const initializeAudio = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: audioConfig.sampleRate,
          channelCount: audioConfig.channels,
          echoCancellation: audioConfig.echoCancellation,
          noiseSuppression: audioConfig.noiseSuppression,
          autoGainControl: audioConfig.autoGainControl
        }
      });
      streamRef.current = stream;

      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }

      const analyser = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      
      analyser.fftSize = audioConfig.bufferSize;
      source.connect(analyser);
      analyserRef.current = analyser;

      const options = {
        mimeType: 'audio/webm;codecs=opus'
      };

      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        if (MediaRecorder.isTypeSupported('audio/webm')) {
          options.mimeType = 'audio/webm';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          options.mimeType = 'audio/mp4';
        } else {
          options.mimeType = 'audio/wav';
        }
      }

      mediaRecorderRef.current = new MediaRecorder(stream, options);

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          
          if (websocketRef.current?.readyState === WebSocket.OPEN && readyStateRef.current) {
            try {
              const reader = new FileReader();
              reader.onloadend = () => {
                const base64Audio = reader.result.split(',')[1];
                websocketRef.current.send(JSON.stringify({
                  type: 'audio_chunk',
                  audio_data: base64Audio,
                  timestamp: Date.now()
                }));
              };
              reader.readAsDataURL(event.data);
            } catch (error) {
              console.error('Error sending audio chunk:', error);
            }
          }
        }
      };

      mediaRecorderRef.current.onstop = () => {
        console.log('Media recorder stopped');
        
        if (audioChunksRef.current.length > 0 && websocketRef.current && readyStateRef.current) {
          const audioBlob = new Blob(audioChunksRef.current, { type: options.mimeType });
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64Audio = reader.result.split(',')[1];
            websocketRef.current.send(JSON.stringify({
              type: 'audio_complete',
              audio_data: base64Audio,
              timestamp: Date.now()
            }));
          };
          reader.readAsDataURL(audioBlob);
        }
      };

      console.log('Audio initialized successfully');
      return true;

    } catch (error) {
      console.error('Failed to initialize audio:', error);
      return false;
    }
  }, [audioConfig]);

  // Start recording - original functionality
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

      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
        audioChunksRef.current = [];
        mediaRecorderRef.current.start(100);
        
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

  // Stop recording - original functionality
  const stopRecording = useCallback(() => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }

      sendMessage({
        type: 'stop_recording',
        timestamp: Date.now()
      });

      setIsRecording(false);
      setAudioLevel(0);
      console.log('Recording stopped');

    } catch (error) {
      console.error('Error stopping recording:', error);
      setIsRecording(false);
    }
  }, [sendMessage]);

  // Toggle recording - original functionality
  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  // Handle settings change - original functionality
  const handleSettingsChange = useCallback((newSettings) => {
    setVoiceSettings(prev => ({ ...prev, ...newSettings }));
    
    sendMessage({
      type: 'update_settings',
      settings: { ...voiceSettings, ...newSettings },
      enhancement_level: (newSettings.enableEnhancement ?? voiceSettings.enableEnhancement) ? 'high' : 'standard'
    });
  }, [voiceSettings, sendMessage]);

  // Audio level monitoring - original functionality
  useEffect(() => {
    if (!analyserRef.current || !isRecording) {
      setAudioLevel(0);
      return;
    }

    const updateAudioLevel = () => {
      if (analyserRef.current && isRecording) {
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length);
        const level = rms / 255;
        
        setAudioLevel(level);
        
        animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
      }
    };
    
    updateAudioLevel();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isRecording]);

  // Initialize on mount - original functionality
  useEffect(() => {
    connectWithFallback();
    
    return () => {
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
      
      setIsWebSocketReady(false);
      readyStateRef.current = false;
      messageQueueRef.current = [];
    };
  }, [connectWithFallback]);

  // Connection quality indicator - original functionality
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

  // EXACT ORIGINAL JSX STRUCTURE
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