// components/chat/VoiceChat.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Mic, Volume2, AlertCircle, MessageCircle } from 'lucide-react';
import VoiceRecorder from '../voice/VoiceRecorder';
import Message from './Message';
import apiService from '../../services/api';
import unifiedWebSocketService from '../../services/unifiedWebSocketService';
import enhancedAudioService from '../../services/enhancedAudioService';
import { playNotificationSound, formatRelativeTime } from '../../utils/helpers';
import { styles } from '../../utils/styles';
import './VoiceChat.css';

const VoiceChat = ({ activeChat, chats, setChats }) => {
  // State management
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isAiTyping, setIsAiTyping] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('Connecting...');
  const [voiceSubStatus, setVoiceSubStatus] = useState('Please wait...');
  const [isProcessing, setIsProcessing] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [audioLevel, setAudioLevel] = useState(0);
  const [showMessages, setShowMessages] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  
  // Refs
  const messagesEndRef = useRef(null);
  const audioVisualizerRef = useRef(null);
  const connectionTimeoutRef = useRef(null);
  const eventListenersRef = useRef([]);

  // Cleanup event listeners
  const cleanupEventListeners = useCallback(() => {
    eventListenersRef.current.forEach(({ event, handler }) => {
      unifiedWebSocketService.off(event, handler);
    });
    eventListenersRef.current = [];
  }, []);

  // Register event listener with cleanup tracking
  const registerEventListener = useCallback((event, handler) => {
    unifiedWebSocketService.on(event, handler);
    eventListenersRef.current.push({ event, handler });
  }, []);

  // Setup all event listeners
  const setupEventListeners = useCallback(() => {
    console.log('Setting up WebSocket event listeners');
    
    registerEventListener('connected', () => {
      console.log('WebSocket connected event received in VoiceChat');
      setIsConnected(true);
      setConnectionError(false);
      setRetryCount(0);
      setVoiceStatus('Ready to Listen');
      setVoiceSubStatus('Press and hold the button to speak');
      
      // Clear connection timeout
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
    });

    registerEventListener('disconnected', () => {
      console.log('WebSocket disconnected event received');
      setIsConnected(false);
      setIsAiTyping(false);
      setVoiceStatus('Disconnected');
      setVoiceSubStatus('Connection lost');
    });

    registerEventListener('transcription_update', (data) => {
      if (!data.is_final) {
        setVoiceSubStatus(`Listening: "${data.transcript}"`);
      }
    });

    registerEventListener('user_message', (data) => {
      setMessages(prev => [...prev, {
        id: data.message_id,
        content: data.content,
        sender_type: 'user',
        created_at: data.timestamp,
        user_id: data.user_id,
        is_voice: true
      }]);
    });

    registerEventListener('ai_typing', (data) => {
      setIsAiTyping(data.is_typing);
      if (data.is_typing) {
        setVoiceStatus('AI is thinking...');
        setVoiceSubStatus('Preparing response');
      }
    });

    registerEventListener('ai_message', async (data) => {
      setIsAiTyping(false);
      
      const aiMessage = {
        id: data.message_id,
        content: data.content,
        sender_type: 'assistant',
        created_at: data.timestamp,
        emotion_detected: data.emotion_detected,
        tokens_used: data.tokens_used,
        message_metadata: data.message_metadata
      };
      
      setMessages(prev => [...prev, aiMessage]);
      
      // Play audio response
      if (data.has_audio || activeChat?.settings?.enable_tts) {
        try {
          setVoiceStatus('AI is speaking...');
          setVoiceSubStatus('');
          
          const audioResponse = await apiService.synthesizeSpeech(data.content);
          if (audioResponse.audio_data) {
            await enhancedAudioService.playAudio(audioResponse.audio_data, 'mp3');
          }
        } catch (error) {
          console.error('Failed to play audio response:', error);
        }
      }
      
      // Reset status
      setTimeout(() => {
        setVoiceStatus('Ready to Listen');
        setVoiceSubStatus('Press and hold the button to speak');
      }, 1000);
      
      playNotificationSound(soundEnabled);
    });

    registerEventListener('error', (error) => {
      console.error('WebSocket error event:', error);
      setConnectionError(true);
      setVoiceStatus('Connection Error');
      setVoiceSubStatus('Please check your connection');
    });

    registerEventListener('reconnect_failed', () => {
      setConnectionError(true);
      setVoiceStatus('Connection Failed');
      setVoiceSubStatus('Unable to establish connection');
    });
  }, [registerEventListener, activeChat, soundEnabled]);

  // Initialize WebSocket connection and fetch messages
  useEffect(() => {
    let mounted = true;

    const initializeChat = async () => {
      if (!activeChat) return;

      try {
        // Set up event listeners FIRST, before any connection attempt
        cleanupEventListeners();
        setupEventListeners();
        
        // Fetch messages
        await fetchMessages(activeChat.id);
        
        // Then connect WebSocket
        if (mounted) {
          setConnectionError(false);
          setVoiceStatus('Connecting...');
          setVoiceSubStatus('Establishing connection...');

          // Set connection timeout
          connectionTimeoutRef.current = setTimeout(() => {
            if (!isConnected && mounted) {
              setConnectionError(true);
              setVoiceStatus('Connection Timeout');
              setVoiceSubStatus('Taking too long to connect');
            }
          }, 10000);

          try {
            await unifiedWebSocketService.connect(activeChat.id);
          } catch (error) {
            console.error('WebSocket connection failed:', error);
            if (mounted) {
              setConnectionError(true);
              setVoiceStatus('Connection Failed');
              setVoiceSubStatus('Please try again');
            }
          }
        }
      } catch (error) {
        console.error('Failed to initialize chat:', error);
        if (mounted) {
          setConnectionError(true);
          setVoiceStatus('Connection Error');
          setVoiceSubStatus('Please try again');
        }
      }
    };

    initializeChat();

    return () => {
      mounted = false;
      cleanupEventListeners();
      
      // Clear timeout if exists
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
      
      // Disconnect WebSocket
      unifiedWebSocketService.disconnect();
      enhancedAudioService.stopAll();
    };
  }, [activeChat, cleanupEventListeners]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchMessages = async (chatId) => {
    try {
      const data = await apiService.getChatMessages(chatId);
      setMessages(data.messages || data || []);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
      throw error;
    }
  };

  // Handle retry connection
  const handleRetryConnection = async () => {
    if (!activeChat) return;
    
    setRetryCount(prev => prev + 1);
    cleanupEventListeners();
    setupEventListeners();
    
    setConnectionError(false);
    setVoiceStatus('Reconnecting...');
    setVoiceSubStatus('Please wait...');
    
    try {
      await unifiedWebSocketService.connect(activeChat.id);
    } catch (error) {
      console.error('Retry failed:', error);
      setConnectionError(true);
      setVoiceStatus('Connection Failed');
      setVoiceSubStatus('Please try again');
    }
  };

  // Handle voice recording events
  const handleRecordingStart = () => {
    if (!isConnected) {
      setVoiceStatus('Not Connected');
      setVoiceSubStatus('Please wait for connection');
      return;
    }
    
    setVoiceStatus('Listening...');
    setVoiceSubStatus('Speak clearly into your microphone');
  };

  const handleRecordingStop = () => {
    if (!isConnected) return;
    
    setVoiceStatus('Processing...');
    setVoiceSubStatus('Converting speech to text');
    setIsProcessing(true);
  };

  const handleTranscript = async (transcript, audioBlob, isStreaming) => {
    if (!transcript || transcript.trim() === '') {
      setVoiceStatus('No Speech Detected');
      setVoiceSubStatus('Please try again');
      setIsProcessing(false);
      
      setTimeout(() => {
        setVoiceStatus('Ready to Listen');
        setVoiceSubStatus('Press and hold the button to speak');
      }, 2000);
      
      return;
    }

    // Send message through WebSocket as a regular chat message
    try {
      if (unifiedWebSocketService.isConnected) {
        unifiedWebSocketService.send({
          type: 'chat_message',
          content: transcript,
          detect_emotion: true,
          metadata: {
            source: 'voice',
            transcribed: true
          }
        });
      } else {
        // Fallback to REST API
        const data = await apiService.sendMessage(transcript, activeChat.id, {
          is_voice: true,
          enable_tts: true
        });
        
        // Handle response manually if not connected
        setMessages(prev => [...prev, {
          id: Date.now(),
          content: transcript,
          sender_type: 'user',
          created_at: new Date().toISOString(),
          is_voice: true
        }]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setVoiceStatus('Error Sending Message');
      setVoiceSubStatus('Please try again');
    }
    
    setIsProcessing(false);
    
    setTimeout(() => {
      setVoiceStatus('Ready to Listen');
      setVoiceSubStatus('Press and hold the button to speak');
    }, 1000);
  };

  const handleError = (error) => {
    console.error('Voice recording error:', error);
    setVoiceStatus('Recording Error');
    setVoiceSubStatus(error || 'Please check your microphone');
    setIsProcessing(false);
    
    setTimeout(() => {
      setVoiceStatus('Ready to Listen');
      setVoiceSubStatus('Press and hold the button to speak');
    }, 3000);
  };

  // Generate voice visualization bars
  const generateVoiceBars = () => {
    const bars = [];
    const barCount = 20;
    
    for (let i = 0; i < barCount; i++) {
      const height = audioLevel > 0 ? 
        Math.random() * audioLevel * 100 : 
        20 + Math.sin(Date.now() * 0.001 + i) * 10;
      
      bars.push(
        <div
          key={i}
          className="voice-bar"
          style={{
            height: `${height}%`,
            animationDelay: `${i * 0.05}s`
          }}
        />
      );
    }
    return bars;
  };

  return (
    <div className="voice-chat-container">
      <div className="voice-chat-header">
        <div className="header-content">
          <MessageCircle className="chat-icon" />
          <div className="header-text">
            <h3>{activeChat?.title || 'Voice Chat'}</h3>
            <div className="connection-status">
              <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
              <span>{isConnected ? 'Connected' : connectionError ? 'Connection Error' : 'Connecting...'}</span>
            </div>
          </div>
        </div>
        
        <button
          className="toggle-messages-btn"
          onClick={() => setShowMessages(!showMessages)}
        >
          {showMessages ? 'Hide' : 'Show'} Messages
        </button>
      </div>

      {connectionError && (
        <div className="connection-error-banner">
          <AlertCircle size={20} />
          <span>Connection failed. Please check your internet connection.</span>
          <button onClick={handleRetryConnection} className="retry-btn">
            Retry {retryCount > 0 && `(${retryCount})`}
          </button>
        </div>
      )}

      {showMessages && (
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Mic size={48} className="empty-icon" />
              <p>Start a conversation by pressing the voice button</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <Message
                key={message.id || index}
                message={message}
                isLast={index === messages.length - 1}
              />
            ))
          )}
          {isAiTyping && (
            <div className="ai-typing-indicator">
              <div className="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      <div className="voice-interface">
        <div className="voice-status">
          <h2>{voiceStatus}</h2>
          <p>{voiceSubStatus}</p>
        </div>

        <div className="voice-visualizer" ref={audioVisualizerRef}>
          {generateVoiceBars()}
        </div>

        <VoiceRecorder
          onTranscript={handleTranscript}
          onError={handleError}
          onRecordingStart={handleRecordingStart}
          onRecordingStop={handleRecordingStop}
          disabled={!isConnected || connectionError}
          isStreaming={false}
          onAudioLevel={setAudioLevel}
          mode="push-to-talk"
          autoSend={true}
          language="en-US"
        />

        <div className="voice-controls">
          <button
            className="control-btn"
            onClick={() => setSoundEnabled(!soundEnabled)}
            title={soundEnabled ? 'Disable sound' : 'Enable sound'}
          >
            <Volume2 className={!soundEnabled ? 'muted' : ''} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceChat;