import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import apiService from '../../services/api';
import { 
  CONVERSATION_STYLES, 
  RESPONSE_LENGTHS, 
  EMOTIONAL_SUPPORT_LEVELS 
} from '../../utils/constants';

const SettingsModal = ({ onClose, darkMode }) => {
  const [preferences, setPreferences] = useState({
    conversation_style: 'friendly',
    response_length: 'medium',
    emotional_support_level: 'standard'
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    try {
      const data = await apiService.getPersonalization();
      if (data.preferences && Object.keys(data.preferences).length > 0) {
        setPreferences({
          conversation_style: data.preferences.conversation_style || 'friendly',
          response_length: data.preferences.preferred_response_length || 'medium',
          emotional_support_level: data.preferences.emotional_support_level || 'standard'
        });
      }
    } catch (error) {
      console.error('Failed to fetch preferences:', error);
    }
  };

  const savePreferences = async () => {
    setLoading(true);
    setMessage('');
    
    try {
      await apiService.updatePersonalization(preferences);
      setMessage('Preferences saved successfully!');
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (error) {
      console.error('Failed to save preferences:', error);
      setMessage('Failed to save preferences. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setPreferences(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div 
      className="modal-overlay" 
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000
      }}
    >
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()}
        style={{
          background: darkMode ? '#2d2d2d' : 'white',
          borderRadius: '8px',
          padding: '24px',
          maxWidth: '500px',
          width: '90%',
          maxHeight: '80vh',
          overflowY: 'auto',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, color: darkMode ? '#e0e0e0' : '#333' }}>Settings</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: darkMode ? '#e0e0e0' : '#6b7280'
            }}
          >
            <X size={24} />
          </button>
        </div>
        
        <div className="preference-section" style={{ marginBottom: '20px' }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '8px', 
            fontWeight: '500',
            color: darkMode ? '#b0b0b0' : '#555'
          }}>
            Conversation Style
          </label>
          <select
            value={preferences.conversation_style}
            onChange={(e) => handleChange('conversation_style', e.target.value)}
            disabled={loading}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: `1px solid ${darkMode ? '#555' : '#ddd'}`,
              borderRadius: '4px',
              fontSize: '14px',
              background: darkMode ? '#3d3d3d' : 'white',
              color: darkMode ? '#e0e0e0' : '#333',
              cursor: 'pointer'
            }}
          >
            {CONVERSATION_STYLES.map(style => (
              <option key={style.value} value={style.value}>
                {style.label}
              </option>
            ))}
          </select>
        </div>

        <div className="preference-section" style={{ marginBottom: '20px' }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '8px', 
            fontWeight: '500',
            color: darkMode ? '#b0b0b0' : '#555'
          }}>
            Response Length
          </label>
          <select
            value={preferences.response_length}
            onChange={(e) => handleChange('response_length', e.target.value)}
            disabled={loading}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: `1px solid ${darkMode ? '#555' : '#ddd'}`,
              borderRadius: '4px',
              fontSize: '14px',
              background: darkMode ? '#3d3d3d' : 'white',
              color: darkMode ? '#e0e0e0' : '#333',
              cursor: 'pointer'
            }}
          >
            {RESPONSE_LENGTHS.map(length => (
              <option key={length.value} value={length.value}>
                {length.label}
              </option>
            ))}
          </select>
        </div>

        <div className="preference-section" style={{ marginBottom: '20px' }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '8px', 
            fontWeight: '500',
            color: darkMode ? '#b0b0b0' : '#555'
          }}>
            Emotional Support Level
          </label>
          <select
            value={preferences.emotional_support_level}
            onChange={(e) => handleChange('emotional_support_level', e.target.value)}
            disabled={loading}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: `1px solid ${darkMode ? '#555' : '#ddd'}`,
              borderRadius: '4px',
              fontSize: '14px',
              background: darkMode ? '#3d3d3d' : 'white',
              color: darkMode ? '#e0e0e0' : '#333',
              cursor: 'pointer'
            }}
          >
            {EMOTIONAL_SUPPORT_LEVELS.map(level => (
              <option key={level.value} value={level.value}>
                {level.label}
              </option>
            ))}
          </select>
        </div>

        {message && (
          <div style={{
            padding: '12px',
            borderRadius: '4px',
            marginBottom: '20px',
            textAlign: 'center',
            fontSize: '14px',
            backgroundColor: message.includes('success') 
              ? (darkMode ? '#1e4620' : '#d4edda')
              : (darkMode ? '#5a1e1e' : '#f8d7da'),
            color: message.includes('success')
              ? (darkMode ? '#90ee90' : '#155724')
              : (darkMode ? '#ff6b6b' : '#721c24'),
            border: `1px solid ${
              message.includes('success')
                ? (darkMode ? '#2e5f30' : '#c3e6cb')
                : (darkMode ? '#7a2e2e' : '#f5c6cb')
            }`
          }}>
            {message}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button 
            onClick={onClose}
            disabled={loading}
            style={{
              padding: '8px 20px',
              border: 'none',
              borderRadius: '4px',
              fontSize: '14px',
              cursor: 'pointer',
              background: darkMode ? '#4a4a4a' : '#e0e0e0',
              color: darkMode ? '#e0e0e0' : '#333'
            }}
          >
            Cancel
          </button>
          <button 
            onClick={savePreferences}
            disabled={loading}
            style={{
              padding: '8px 20px',
              border: 'none',
              borderRadius: '4px',
              fontSize: '14px',
              cursor: 'pointer',
              background: '#007bff',
              color: 'white',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;