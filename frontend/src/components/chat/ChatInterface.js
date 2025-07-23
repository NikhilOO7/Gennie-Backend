// components/chat/ChatInterface.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MessageCircle, Mic, Keyboard } from 'lucide-react';
import ChatHeader from './ChatHeader';
import Message from './Message';
import MessageInput from './MessageInput';
import VoiceChat from './VoiceChat';
import EnhancedVoiceInterface from '../voice/EnhancedVoiceInterface';
import VoiceRecorder from '../voice/VoiceRecorder';
import RAGVisualization from '../rag/RAGVisualization';
import apiService from '../../services/api';
import unifiedWebSocketService from '../../services/UnifiedWebSocketService';
import enhancedAudioService from '../../services/enhancedAudioService';
import { playNotificationSound } from '../../utils/helpers';

const ChatInterface = ({ activeChat, setActiveChat, chats, setChats }) => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isAiTyping, setIsAiTyping] = useState(false);
  const [emotionAnalysis, setEmotionAnalysis] = useState(null);
  const [showRAGVisualization, setShowRAGVisualization] = useState(false);
  const [selectedMessageId, setSelectedMessageId] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [inputMode, setInputMode] = useState('text'); // 'text', 'voice', 'enhanced-voice'
  const [connectionError, setConnectionError] = useState(false);
  const messagesEndRef = useRef(null);
  const connectionTimeoutRef = useRef(null);
  const eventListenersSetupRef = useRef(false);

  // Define isVoiceMode based on chat mode or current input mode
  const isVoiceMode = activeChat?.chat_mode === 'voice' || inputMode === 'voice' || inputMode === 'enhanced-voice';
  const isEnhancedVoiceMode = inputMode === 'enhanced-voice' || activeChat?.chat_mode === 'enhanced-voice';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchMessages = async (chatId) => {
    try {
      const data = await apiService.getChatMessages(chatId);
      setMessages(data.messages || data || []);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  };

  // Clean up event listeners
  const cleanupEventListeners = useCallback(() => {
    if (eventListenersSetupRef.current) {
      console.log('Cleaning up WebSocket event listeners');
      unifiedWebSocketService.off('connected', handleConnected);
      unifiedWebSocketService.off('disconnected', handleDisconnected);
      unifiedWebSocketService.off('user_message', handleUserMessage);
      unifiedWebSocketService.off('ai_message_start', handleAiMessageStart);
      unifiedWebSocketService.off('ai_message_chunk', handleAiMessageChunk);
      unifiedWebSocketService.off('ai_message_complete', handleAiMessageComplete);
      unifiedWebSocketService.off('emotion_detected', handleEmotionDetected);
      unifiedWebSocketService.off('rag_context', handleRagContext);
      unifiedWebSocketService.off('error', handleWebSocketError);
      eventListenersSetupRef.current = false;
    }
  }, []);

  // WebSocket event handlers
  const handleConnected = useCallback(() => {
    console.log('WebSocket connected');
    setIsConnected(true);
    setConnectionError(false);
    
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }
  }, []);

  const handleDisconnected = useCallback((data) => {
    console.log('WebSocket disconnected:', data);
    setIsConnected(false);
    setIsAiTyping(false);
    
    // Only show error if it wasn't a normal closure
    if (data?.code !== 1000) {
      setConnectionError(true);
    }
  }, []);

  const handleUserMessage = useCallback((data) => {
    console.log('User message received:', data);
    setMessages(prev => [...prev, {
      id: data.message_id,
      content: data.content,
      sender: 'user',
      timestamp: new Date().toISOString(),
      audio_url: data.audio_url || null,
      emotion: data.emotion || null
    }]);
  }, []);

  const handleAiMessageStart = useCallback(() => {
    console.log('AI message start');
    setIsAiTyping(true);
  }, []);

  const handleAiMessageChunk = useCallback((data) => {
    console.log('AI message chunk:', data);
    setMessages(prev => {
      const lastMessage = prev[prev.length - 1];
      if (lastMessage && lastMessage.sender === 'ai' && lastMessage.isStreaming) {
        return prev.map((msg, index) => 
          index === prev.length - 1 
            ? { ...msg, content: msg.content + data.content }
            : msg
        );
      } else {
        return [...prev, {
          id: data.message_id || Date.now(),
          content: data.content,
          sender: 'ai',
          timestamp: new Date().toISOString(),
          isStreaming: true,
          emotion: data.emotion || null
        }];
      }
    });
  }, []);

  const handleAiMessageComplete = useCallback((data) => {
    console.log('AI message complete:', data);
    setIsAiTyping(false);
    setMessages(prev => 
      prev.map(msg => 
        msg.isStreaming ? { ...msg, isStreaming: false, audio_url: data.audio_url } : msg
      )
    );
    
    if (soundEnabled && data.audio_url) {
      playNotificationSound();
    }
  }, [soundEnabled]);

  const handleEmotionDetected = useCallback((data) => {
    console.log('Emotion detected:', data);
    setEmotionAnalysis(data);
  }, []);

  const handleRagContext = useCallback((data) => {
    console.log('RAG context received:', data);
    if (data.sources && data.sources.length > 0) {
      setShowRAGVisualization(true);
    }
  }, []);

  const handleWebSocketError = useCallback((data) => {
    console.error('WebSocket error:', data);
    setIsAiTyping(false);
    setConnectionError(true);
  }, []);

  // Set up event listeners
  const setupEventListeners = useCallback(() => {
    if (!eventListenersSetupRef.current) {
      console.log('Setting up WebSocket event listeners');
      
      unifiedWebSocketService.on('connected', handleConnected);
      unifiedWebSocketService.on('disconnected', handleDisconnected);
      unifiedWebSocketService.on('user_message', handleUserMessage);
      unifiedWebSocketService.on('ai_message_start', handleAiMessageStart);
      unifiedWebSocketService.on('ai_message_chunk', handleAiMessageChunk);
      unifiedWebSocketService.on('ai_message_complete', handleAiMessageComplete);
      unifiedWebSocketService.on('emotion_detected', handleEmotionDetected);
      unifiedWebSocketService.on('rag_context', handleRagContext);
      unifiedWebSocketService.on('error', handleWebSocketError);
      
      eventListenersSetupRef.current = true;
    }
  }, [
    handleConnected,
    handleDisconnected,
    handleUserMessage,
    handleAiMessageStart,
    handleAiMessageChunk,
    handleAiMessageComplete,
    handleEmotionDetected,
    handleRagContext,
    handleWebSocketError
  ]);

  const connectWebSocket = useCallback(async (chatId) => {
    try {
      // Set up event listeners first
      setupEventListeners();
      
      // Set connection timeout
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
      }
      
      connectionTimeoutRef.current = setTimeout(() => {
        if (!isConnected) {
          console.error('WebSocket connection timeout');
          setConnectionError(true);
        }
      }, 10000);

      // Connect to WebSocket
      console.log('Connecting to WebSocket for chat:', chatId);
      await unifiedWebSocketService.connect(chatId);
      
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setConnectionError(true);
      setIsConnected(false);
    }
  }, [setupEventListeners, isConnected]);

  // Handle voice transcript from enhanced voice interface
  const handleVoiceTranscript = useCallback(async (transcript, audioData) => {
    if (!transcript.trim()) return;

    console.log('Voice transcript received:', transcript);

    try {
      // Add user message to UI immediately
      const userMessage = {
        id: Date.now(),
        content: transcript,
        sender: 'user',
        timestamp: new Date().toISOString(),
        audio_data: audioData,
        isVoice: true
      };
      
      setMessages(prev => [...prev, userMessage]);

      // Send via WebSocket with audio data
      if (unifiedWebSocketService.isConnected()) {
        const success = unifiedWebSocketService.send({
          type: 'voice_message',
          content: transcript,
          audio_data: audioData,
          chat_id: activeChat.id,
          include_emotion: true,
          include_rag: true
        });
        
        if (!success) {
          console.warn('Failed to send voice message via WebSocket');
        }
      } else {
        console.warn('WebSocket not connected, cannot send voice message');
      }
    } catch (error) {
      console.error('Failed to send voice message:', error);
    }
  }, [activeChat]);

  // Handle audio response from enhanced voice interface
  const handleAudioResponse = useCallback((audioData) => {
    // Audio response is handled by the WebSocket events
    console.log('Audio response received:', audioData);
  }, []);

  // Toggle between input modes
  const toggleInputMode = () => {
    const modes = ['text', 'voice', 'enhanced-voice'];
    const currentIndex = modes.indexOf(inputMode);
    const nextIndex = (currentIndex + 1) % modes.length;
    setInputMode(modes[nextIndex]);
  };

  // Handle regular text message
  const handleSendMessage = async (content, attachments = []) => {
    if (!content.trim() && attachments.length === 0) return;

    try {
      const messageData = {
        content: content.trim(),
        attachments,
        chat_id: activeChat.id
      };

      if (unifiedWebSocketService.isConnected()) {
        const success = unifiedWebSocketService.send({
          type: 'message',
          ...messageData
        });
        
        if (!success) {
          console.warn('Failed to send message via WebSocket, falling back to HTTP');
          // Fallback to HTTP API
          const response = await apiService.sendMessage(activeChat.id, messageData);
          fetchMessages(activeChat.id);
        }
      } else {
        console.warn('WebSocket not connected, using HTTP API');
        // Fallback to HTTP API
        const response = await apiService.sendMessage(activeChat.id, messageData);
        fetchMessages(activeChat.id);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  // Retry connection
  const retryConnection = useCallback(async () => {
    if (activeChat) {
      setConnectionError(false);
      await connectWebSocket(activeChat.id);
    }
  }, [activeChat, connectWebSocket]);

  // Initialize chat
  useEffect(() => {
    let mounted = true;

    const initializeChat = async () => {
      if (!activeChat) return;

      try {
        // Clean up previous listeners
        cleanupEventListeners();
        
        // Fetch messages first
        await fetchMessages(activeChat.id);
        
        if (!mounted) return;
        
        // Connect WebSocket
        await connectWebSocket(activeChat.id);
        
        // Set input mode based on chat mode
        if (activeChat.chat_mode === 'voice') {
          setInputMode('enhanced-voice');
        } else {
          setInputMode('text');
        }
      } catch (error) {
        console.error('Failed to initialize chat:', error);
        if (mounted) {
          setConnectionError(true);
        }
      }
    };

    initializeChat();

    return () => {
      mounted = false;
      cleanupEventListeners();
      
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
      
      // Only disconnect if we're changing chats, not unmounting entirely
      if (activeChat) {
        unifiedWebSocketService.disconnect();
      }
    };
  }, [activeChat, connectWebSocket, cleanupEventListeners]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  if (!activeChat) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <MessageCircle size={64} className="mx-auto text-gray-400 mb-4" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">
            Select a chat to start messaging
          </h3>
          <p className="text-gray-500">
            Choose a conversation from the sidebar or create a new one.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* Header */}
      <ChatHeader 
        chat={activeChat}
        isConnected={isConnected}
        soundEnabled={soundEnabled}
        setSoundEnabled={setSoundEnabled}
        showRAGVisualization={showRAGVisualization}
        setShowRAGVisualization={setShowRAGVisualization}
        inputMode={inputMode}
        onToggleInputMode={toggleInputMode}
      />

      {/* Connection Error Banner */}
      {connectionError && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-200 text-red-700 text-sm flex items-center justify-between">
          <span>⚠️ Connection lost. Some features may not work properly.</span>
          <button
            onClick={retryConnection}
            className="ml-2 px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <Message
            key={message.id}
            message={message}
            onMessageSelect={setSelectedMessageId}
            selectedMessageId={selectedMessageId}
            showRAGVisualization={showRAGVisualization}
          />
        ))}
        
        {isAiTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-xs">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* RAG Visualization */}
      {showRAGVisualization && (
        <RAGVisualization 
          messageId={selectedMessageId} 
          onClose={() => setShowRAGVisualization(false)}
        />
      )}

      {/* Emotion Analysis Display */}
      {emotionAnalysis && (
        <div className="px-4 py-2 bg-blue-50 border-t border-blue-200 text-sm">
          <span className="font-medium text-blue-800">
            Emotion detected: {emotionAnalysis.primary_emotion} 
            ({Math.round(emotionAnalysis.confidence * 100)}% confidence)
          </span>
        </div>
      )}

      {/* Input Area - Conditional rendering based on mode */}
      <div className="border-t bg-white">
        {/* Input Mode Toggle */}
        <div className="px-4 py-2 border-b bg-gray-50 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <span>Input mode:</span>
            <span className="font-medium">
              {inputMode === 'text' && 'Text'}
              {inputMode === 'voice' && 'Voice (Basic)'}
              {inputMode === 'enhanced-voice' && 'Voice (Enhanced)'}
            </span>
            {!isConnected && (
              <span className="text-red-500 text-xs">
                (Some features disabled - connection lost)
              </span>
            )}
          </div>
          <button
            onClick={toggleInputMode}
            className="flex items-center space-x-1 px-3 py-1 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            {inputMode === 'text' && <Keyboard size={16} />}
            {(inputMode === 'voice' || inputMode === 'enhanced-voice') && <Mic size={16} />}
            <span>Switch Mode</span>
          </button>
        </div>

        {/* Text Input */}
        {inputMode === 'text' && (
          <MessageInput 
            onSendMessage={handleSendMessage}
            disabled={!isConnected && !connectionError} // Allow sending via HTTP when disconnected
          />
        )}

        {/* Basic Voice Input */}
        {inputMode === 'voice' && (
          <div className="p-4">
            <VoiceRecorder
              onTranscript={(transcript) => handleSendMessage(transcript)}
              onError={(error) => console.error('Voice recording error:', error)}
              language="en-US"
              autoSend={true}
              disabled={false} // Basic voice input doesn't require WebSocket
            />
            <div className="text-xs text-gray-500 text-center mt-2">
              Click and hold to record. Basic voice recognition.
            </div>
          </div>
        )}

        {/* Enhanced Voice Input */}
        {inputMode === 'enhanced-voice' && (
          <div className="p-4">
            <EnhancedVoiceInterface
              onTranscript={handleVoiceTranscript}
              onAudioResponse={handleAudioResponse}
              isConnected={isConnected}
              className="enhanced-voice-mode"
            />
            <div className="text-xs text-gray-500 text-center mt-2">
              Enhanced voice interface with real-time streaming, emotion detection, and quality improvements.
              {!isConnected && (
                <span className="text-red-500 block">
                  Connection required for full functionality. Some features may be limited.
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;