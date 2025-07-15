import React, { useState } from 'react';
import { X, MessageCircle, Mic } from 'lucide-react';
import { styles } from '../../utils/styles';

const NewChatModal = ({ isOpen, onClose, onCreate, userTopics = [] }) => {
  const [selectedMode, setSelectedMode] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState(null);

  const handleCreate = () => {
    if (selectedMode) {
      onCreate({
        mode: selectedMode,
        topic: selectedTopic
      });
      handleClose();
    }
  };

  const handleClose = () => {
    setSelectedMode(null);
    setSelectedTopic(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      animation: 'fadeIn 0.2s ease-out'
    }}>
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '32px',
        maxWidth: '480px',
        width: '90%',
        maxHeight: '90vh',
        overflowY: 'auto',
        animation: 'slideUp 0.3s ease-out'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '24px'
        }}>
          <div>
            <h2 style={{ fontSize: '24px', marginBottom: '8px' }}>Create New Chat</h2>
            <p style={{ color: '#6b7280', fontSize: '14px' }}>Choose your preferred chat mode</p>
          </div>
          <button
            onClick={handleClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#6b7280'
            }}
          >
            <X size={24} />
          </button>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'grid', gap: '16px' }}>
            <div
              onClick={() => setSelectedMode('text')}
              style={{
                padding: '20px',
                border: `2px solid ${selectedMode === 'text' ? '#4f46e5' : '#e5e7eb'}`,
                borderRadius: '12px',
                cursor: 'pointer',
                backgroundColor: selectedMode === 'text' ? '#e0e7ff' : 'transparent',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '16px'
              }}
            >
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                backgroundColor: selectedMode === 'text' ? '#4f46e5' : '#f3f4f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <MessageCircle size={24} color={selectedMode === 'text' ? 'white' : '#6b7280'} />
              </div>
              <div>
                <h3 style={{ fontSize: '18px', marginBottom: '4px' }}>Text Chat</h3>
                <p style={{ fontSize: '14px', color: '#6b7280' }}>
                  Type messages and receive text responses
                </p>
              </div>
            </div>

            <div
              onClick={() => setSelectedMode('voice')}
              style={{
                padding: '20px',
                border: `2px solid ${selectedMode === 'voice' ? '#4f46e5' : '#e5e7eb'}`,
                borderRadius: '12px',
                cursor: 'pointer',
                backgroundColor: selectedMode === 'voice' ? '#e0e7ff' : 'transparent',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '16px'
              }}
            >
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                backgroundColor: selectedMode === 'voice' ? '#4f46e5' : '#f3f4f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Mic size={24} color={selectedMode === 'voice' ? 'white' : '#6b7280'} />
              </div>
              <div>
                <h3 style={{ fontSize: '18px', marginBottom: '4px' }}>Voice Chat</h3>
                <p style={{ fontSize: '14px', color: '#6b7280' }}>
                  Speak naturally and have voice conversations
                </p>
              </div>
            </div>
          </div>
        </div>

        {selectedMode && userTopics.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>
              Optional: Select a topic for this chat
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {userTopics.map(topic => (
                <button
                  key={topic.id}
                  onClick={() => setSelectedTopic(selectedTopic === topic.id ? null : topic.id)}
                  style={{
                    padding: '8px 16px',
                    border: `1px solid ${selectedTopic === topic.id ? '#4f46e5' : '#e5e7eb'}`,
                    borderRadius: '20px',
                    backgroundColor: selectedTopic === topic.id ? '#e0e7ff' : 'white',
                    color: selectedTopic === topic.id ? '#4f46e5' : '#6b7280',
                    fontSize: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  {topic.icon} {topic.name}
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            onClick={handleClose}
            style={{
              ...styles.button,
              backgroundColor: '#f3f4f6',
              color: '#6b7280'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!selectedMode}
            style={{
              ...styles.button,
              opacity: selectedMode ? 1 : 0.5,
              cursor: selectedMode ? 'pointer' : 'not-allowed'
            }}
          >
            Create Chat
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewChatModal;