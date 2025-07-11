import React from 'react';
import { Activity, Smile, Frown, Meh } from 'lucide-react';
import { styles } from '../../utils/styles';
import { formatTime } from '../../utils/helpers';

const Message = ({ message, onShowRAGContext }) => {
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
        position: 'relative'
      }}>
        <p style={{ margin: 0 }}>{message.content}</p>
        
        {message.created_at && (
          <div style={{ 
            marginTop: '8px', 
            fontSize: '12px', 
            opacity: 0.7,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
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