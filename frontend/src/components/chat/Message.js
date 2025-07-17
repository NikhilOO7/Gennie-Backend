// components/chat/Message.js
import React, { useState } from 'react';
import { Activity, Smile, Frown, Meh, Play, Pause, Volume2 } from 'lucide-react';
import { styles } from '../../utils/styles';
import { formatTime } from '../../utils/helpers';
import TTSControls from '../voice/TTSControls';
import enhancedAudioService from '../../services/enhancedAudioService';

const Message = ({ message, onShowRAGContext, isVoiceMode }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioError, setAudioError] = useState(null);

  const getEmotionIcon = (emotion) => {
    switch (emotion?.toLowerCase()) {
      case 'positive':
      case 'joy':
      case 'happy':
      case 'excitement':
        return <Smile size={16} color="#10b981" />;
      case 'negative':
      case 'sad':
      case 'angry':
      case 'fear':
        return <Frown size={16} color="#ef4444" />;
      default:
        return <Meh size={16} color="#f59e0b" />;
    }
  };

  const handlePlayVoice = async () => {
    if (message.audio_url) {
      try {
        setAudioError(null);
        const response = await fetch(message.audio_url, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.audio_data) {
            setIsPlaying(true);
            await enhancedAudioService.playAudio(data.audio_data, 'mp3');
            setIsPlaying(false);
          }
        } else {
          throw new Error('Failed to fetch audio');
        }
      } catch (error) {
        console.error('Failed to play audio:', error);
        setAudioError('Failed to play audio');
        setIsPlaying(false);
      }
    }
  };

  return (
    <div
      style={{
        marginBottom: '16px',
        display: 'flex',
        justifyContent: message.sender_type === 'user' ? 'flex-end' : 'flex-start',
        animation: 'fadeIn 0.3s ease-in'
      }}
    >
      <div style={{
        ...styles.message,
        ...(message.sender_type === 'user' ? styles.userMessage : styles.aiMessage),
        position: 'relative',
        maxWidth: '70%'
      }}>
        {/* Always show text content */}
        <p style={{ margin: 0 }}>{message.content}</p>
        
        {/* Show voice controls if message has voice */}
        {message.has_voice && (
          <div style={{
            marginTop: '12px',
            padding: '8px',
            background: 'rgba(0, 0, 0, 0.05)',
            borderRadius: '6px'
          }}>
            {message.voice_status === 'generating' ? (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '14px',
                color: '#666'
              }}>
                <span className="loading-icon" style={{ animation: 'spin 1s linear infinite' }}>⟳</span>
                <span>Generating voice...</span>
              </div>
            ) : message.voice_status === 'ready' || message.audio_url ? (
              <div>
                <button 
                  onClick={handlePlayVoice} 
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '6px',
                    background: isPlaying ? '#ef4444' : '#4f46e5',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '14px',
                    transition: 'all 0.2s ease'
                  }}
                  disabled={isPlaying}
                >
                  {isPlaying ? (
                    <>
                      <Pause size={16} />
                      <span>Playing...</span>
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      <span>Play Voice</span>
                    </>
                  )}
                </button>
                {audioError && (
                  <div style={{
                    marginTop: '8px',
                    color: '#ef4444',
                    fontSize: '12px'
                  }}>
                    {audioError}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}
        
        {/* TTS controls for any assistant message without voice */}
        {message.sender_type === 'assistant' && !message.has_voice && (
          <div style={{ marginTop: '8px' }}>
            <TTSControls 
              text={message.content}
              messageId={message.id}
              onDemand={true}
              showVoiceSelector={false}
              autoPlay={false}
            />
          </div>
        )}
        
        {/* Message metadata */}
        {message.created_at && (
          <div style={{ 
            marginTop: '8px', 
            fontSize: '12px', 
            opacity: 0.7,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexWrap: 'wrap'
          }}>
            <span>
              {formatTime(message.created_at)}
            </span>
            {message.emotion_detected && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {getEmotionIcon(message.emotion_detected)}
                {message.emotion_detected}
              </div>
            )}
            {message.tokens_used && (
              <span>{message.tokens_used} tokens</span>
            )}
            {message.has_voice && (
              <Volume2 size={14} color="#667eea" />
            )}
            {message.message_metadata?.rag_context_used && onShowRAGContext && (
              <button
                onClick={() => onShowRAGContext(message.id)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'inherit',
                  padding: '2px'
                }}
                title="View RAG Context"
              >
                <Activity size={14} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Message;