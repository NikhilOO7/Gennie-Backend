// components/voice/EnhancedVoiceInterface.js
// EXACT original UI structure with ONLY functional fixes applied

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Settings, Activity, Waves } from 'lucide-react';
import VoiceVisualizer from './VoiceVisualizer';
import VoiceControls from './VoiceControls';
import VoiceSettings from './VoiceSettings';
import AudioPlayer from './AudioPlayer';
import UnifiedWebSocketService from '../../services/unifiedWebSocketService';
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
    voice_name: 'en-US-Neural2-F',
    speaking_rate: 1.0,
    pitch: 0.0,
    voice_language: 'en-US',
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
        setConnectionQuality('disconnected');
      });

    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      setConnectionQuality('disconnected');
      throw error;
    }
  }, [voiceSettings, handleWebSocketMessage]);



  const startRecording = useCallback(() => {
    UnifiedWebSocketService.startRecording();
    setIsRecording(true);
    setCurrentTranscript('');
  }, []);

  const stopRecording = useCallback(() => {
    UnifiedWebSocketService.stopRecording();
    setIsRecording(false);
    setAudioLevel(0);
  }, []);

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
    
    UnifiedWebSocketService.send({
      type: 'update_settings',
      settings: { ...voiceSettings, ...newSettings },
      enhancement_level: (newSettings.enableEnhancement ?? voiceSettings.enableEnhancement) ? 'high' : 'standard'
    });
  }, [voiceSettings]);

  // Audio level monitoring - original functionality
  useEffect(() => {
    const analyserRef = React.createRef();
    const animationFrameRef = React.createRef();

    if (!isRecording) {
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

  useEffect(() => {
    const fetchVoicePreferences = async () => {
      try {
        const prefs = await UnifiedWebSocketService.getVoicePreferences();
        setVoiceSettings(prefs);
      } catch (error) {
        console.error('Failed to fetch voice preferences:', error);
      }
    };
    fetchVoicePreferences();
  }, []);

  // Initialize on mount
  useEffect(() => {
    initializeWebSocket();
    
    return () => {
      UnifiedWebSocketService.disconnect();
    };
  }, [initializeWebSocket]);

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