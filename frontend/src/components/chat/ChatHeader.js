import React from 'react';
import { Wifi, WifiOff, Volume2, VolumeX, Brain, Smile, Frown, Meh } from 'lucide-react';

const ChatHeader = ({ 
  chat, 
  isConnected, 
  emotionAnalysis, 
  soundEnabled, 
  setSoundEnabled,
  onToggleRAG
}) => {
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
    <div style={{ 
      padding: '16px 24px', 
      borderBottom: '1px solid #e5e7eb',
      backgroundColor: 'white'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '4px' }}>
            {chat.title}
          </h3>
          <p style={{ fontSize: '14px', color: '#6b7280' }}>
            {chat.description}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {emotionAnalysis && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '4px',
              padding: '6px 12px',
              backgroundColor: '#f3f4f6',
              borderRadius: '16px'
            }}>
              {getEmotionIcon(emotionAnalysis.emotion)}
              <span style={{ fontSize: '12px', color: '#6b7280' }}>
                {emotionAnalysis.emotion} ({Math.round(emotionAnalysis.confidence * 100)}%)
              </span>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isConnected ? (
              <Wifi size={16} color="#10b981" />
            ) : (
              <WifiOff size={16} color="#ef4444" />
            )}
            <span style={{ fontSize: '12px', color: '#6b7280' }}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <button
            onClick={onToggleRAG}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#6b7280',
              padding: '8px'
            }}
            title="Toggle RAG Visualization"
          >
            <Brain size={20} />
          </button>
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#6b7280',
              padding: '8px'
            }}
            title="Toggle sound"
          >
            {soundEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatHeader;