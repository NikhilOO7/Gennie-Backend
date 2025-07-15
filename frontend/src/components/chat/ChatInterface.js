// components/chat/ChatInterface.js
import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle } from 'lucide-react';
import ChatHeader from './ChatHeader';
import Message from './Message';
import MessageInput from './MessageInput';
import VoiceChat from './VoiceChat';
import VoiceRecorder from '../voice/VoiceRecorder';
import RAGVisualization from '../rag/RAGVisualization';
import apiService from '../../services/api';
import unifiedWebSocketService from '../../services/unifiedWebSocketService';
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
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (activeChat) {
      // Only fetch messages and connect WebSocket for text chats
      // Voice chats handle their own connections
      if (!activeChat.chat_mode || activeChat.chat_mode === 'text') {
        fetchMessages(activeChat.id);
        connectWebSocket(activeChat.id);
      }
    }

    return () => {
      // Only disconnect for text chats
      if (!activeChat?.chat_mode || activeChat?.chat_mode === 'text') {
        unifiedWebSocketService.disconnect();
        enhancedAudioService.stopAll();
      }
    };
  }, [activeChat]);

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
    }
  };

  const connectWebSocket = (chatId) => {
    unifiedWebSocketService.connect(chatId);

    // Set up event listeners
    unifiedWebSocketService.on('connected', () => {
      setIsConnected(true);
    });

    unifiedWebSocketService.on('disconnected', () => {
      setIsConnected(false);
      setIsAiTyping(false);
    });

    unifiedWebSocketService.on('user_message', (data) => {
      setMessages(prev => [...prev, {
        id: data.message_id,
        content: data.content,
        sender_type: 'user',
        created_at: data.timestamp,
        user_id: data.user_id
      }]);
    });

    unifiedWebSocketService.on('ai_typing', (data) => {
      setIsAiTyping(data.is_typing);
    });

    unifiedWebSocketService.on('ai_message', async (data) => {
      setIsAiTyping(false);
      setMessages(prev => [...prev, {
        id: data.message_id,
        content: data.content,
        sender_type: 'assistant',
        created_at: data.timestamp,
        emotion_detected: data.emotion_detected,
        tokens_used: data.tokens_used,
        message_metadata: data.message_metadata
      }]);
      
      if (data.emotion_detected) {
        setEmotionAnalysis({
          emotion: data.emotion_detected,
          confidence: data.confidence_score || 0.95
        });
      }
      
      // Handle audio response if available
      if (data.has_audio) {
        try {
          const audioResponse = await apiService.synthesizeSpeech(data.content);
          if (audioResponse.audio_data) {
            await enhancedAudioService.playAudio(audioResponse.audio_data, 'mp3');
          }
        } catch (error) {
          console.error('Failed to play audio response:', error);
        }
      }
      
      playNotificationSound(soundEnabled);
    });

    unifiedWebSocketService.on('audioReceived', async ({ messageId, audioBlob }) => {
      try {
        await enhancedAudioService.playAudio(audioBlob);
      } catch (error) {
        console.error('Failed to play received audio:', error);
      }
    });
  };

  const sendMessage = async (content, isVoice = false) => {
    if (!content.trim() || !activeChat) return;

    try {
      if (unifiedWebSocketService.isConnected) {
        unifiedWebSocketService.sendChatMessage(content);
      } else {
        // Fallback to REST API
        const data = await apiService.sendMessage(content, activeChat.id);
        
        setMessages(prev => [
          ...prev,
          {
            id: Date.now(),
            content: content,
            sender_type: 'user',
            created_at: new Date().toISOString()
          },
          {
            id: data.message_id || Date.now() + 1,
            content: data.response || data.content,
            sender_type: 'assistant',
            created_at: data.timestamp || new Date().toISOString(),
            emotion_detected: data.emotion_analysis?.primary_emotion,
            tokens_used: data.token_usage?.total_tokens,
            message_metadata: data.metadata
          }
        ]);
        
        if (data.emotion_analysis) {
          setEmotionAnalysis({
            emotion: data.emotion_analysis.primary_emotion,
            confidence: data.emotion_analysis.confidence || 0.95
          });
        }
        playNotificationSound(soundEnabled);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleVoiceTranscript = (transcript, audioBlob) => {
    if (transcript) {
      sendMessage(transcript, true);
    }
  };

  const showRAGContext = (messageId) => {
    setSelectedMessageId(messageId);
    setShowRAGVisualization(true);
  };

  if (!activeChat) {
    return (
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        backgroundColor: '#f9fafb'
      }}>
        <div style={{ textAlign: 'center' }}>
          <MessageCircle size={64} color="#e5e7eb" />
          <h3 style={{ marginTop: '16px', color: '#6b7280' }}>
            No Chat Selected
          </h3>
          <p style={{ marginTop: '8px', color: '#9ca3af' }}>
            Choose a chat from the sidebar or create a new one
          </p>
        </div>
      </div>
    );
  }

  // Render Voice Chat interface if chat mode is voice
  if (activeChat.chat_mode === 'voice') {
    return <VoiceChat activeChat={activeChat} chats={chats} setChats={setChats} />;
  }

  // Render Text Chat interface (default)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <ChatHeader
        chat={activeChat}
        isConnected={isConnected}
        emotionAnalysis={emotionAnalysis}
        soundEnabled={soundEnabled}
        setSoundEnabled={setSoundEnabled}
        onToggleRAG={() => setShowRAGVisualization(!showRAGVisualization)}
      />

      <div style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '24px',
        backgroundColor: '#f9fafb'
      }}>
        {messages.map((message) => (
          <Message
            key={message.id}
            message={message}
            onShowRAGContext={showRAGContext}
          />
        ))}
        {isAiTyping && (
          <Message
            message={{
              content: 'AI is typing...',
              sender_type: 'assistant',
              created_at: new Date().toISOString()
            }}
          />
        )}
        <div ref={messagesEndRef} />
      </div>

      <MessageInput
        onSendMessage={sendMessage}
        disabled={isAiTyping}
      />

      {showVoiceRecorder && (
        <div style={{
          position: 'absolute',
          bottom: '80px',
          right: '20px',
          background: 'white',
          padding: '20px',
          borderRadius: '12px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
        }}>
          <VoiceRecorder
            onTranscript={handleVoiceTranscript}
            mode="push-to-talk"
            autoSend={true}
          />
        </div>
      )}

      {showRAGVisualization && selectedMessageId && (
        <RAGVisualization
          messageId={selectedMessageId}
          onClose={() => setShowRAGVisualization(false)}
        />
      )}
    </div>
  );
};

export default ChatInterface;