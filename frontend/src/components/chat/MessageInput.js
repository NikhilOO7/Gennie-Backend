// components/chat/MessageInput.js
import React, { useState } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';
import { styles } from '../../utils/styles';

const MessageInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // Voice recording implementation would go here
  };

  return (
    <div style={{ 
      padding: '16px 24px', 
      borderTop: '1px solid #e5e7eb',
      backgroundColor: 'white'
    }}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          style={{...styles.input, margin: 0}}
          disabled={disabled}
        />
        <button
          type="button"
          onClick={toggleRecording}
          style={{
            ...styles.button,
            padding: '12px',
            backgroundColor: isRecording ? '#ef4444' : '#4f46e5'
          }}
          title={isRecording ? 'Stop recording' : 'Start recording'}
        >
          {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
        </button>
        <button 
          type="submit"
          style={{ ...styles.button, padding: '12px' }}
          disabled={!message.trim() || disabled}
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
};

export default MessageInput;