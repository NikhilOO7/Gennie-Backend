import React, { useState, useEffect, useCallback } from 'react';
import AudioPlayer from './AudioPlayer';
import apiService from '../../services/api';

const TTSControls = ({
  text,
  messageId,
  onVoiceChange,
  selectedVoice,
  autoPlay = false,
  showVoiceSelector = true,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showPlayer, setShowPlayer] = useState(false);
  const [voices, setVoices] = useState([]);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  
  // Define fetchVoices with useCallback
  const fetchVoices = useCallback(async () => {
    try {
      const data = await apiService.getVoices();
      setVoices(data.voices || []);
      
      // Set default voice if none selected
      if (!selectedVoice && data.voices.length > 0) {
        const defaultVoice = data.voices.find(v => 
          v.type === 'Neural2' && v.ssml_gender === 'Female'
        ) || data.voices[0];
        onVoiceChange?.(defaultVoice.name);
      }
    } catch (error) {
      console.error('Error fetching voices:', error);
    }
  }, [selectedVoice, onVoiceChange]);
  
  // Helper functions for cache
  const getCachedAudioUrl = (text, voice) => {
    const cacheKey = `tts_${btoa(text + voice).substring(0, 20)}`;
    const cached = sessionStorage.getItem(cacheKey);
    return cached ? JSON.parse(cached).url : null;
  };
  
  const cacheAudioUrl = (text, voice, url) => {
    const cacheKey = `tts_${btoa(text + voice).substring(0, 20)}`;
    sessionStorage.setItem(cacheKey, JSON.stringify({
      url: url,
      timestamp: Date.now(),
    }));
    
    // Clean old cache entries
    cleanCache();
  };
  
  const cleanCache = () => {
    const maxAge = 3600000; // 1 hour
    const now = Date.now();
    
    for (let i = sessionStorage.length - 1; i >= 0; i--) {
      const key = sessionStorage.key(i);
      if (key && key.startsWith('tts_')) {
        try {
          const item = JSON.parse(sessionStorage.getItem(key));
          if (now - item.timestamp > maxAge) {
            sessionStorage.removeItem(key);
          }
        } catch {
          sessionStorage.removeItem(key);
        }
      }
    }
  };
  
  // Define handlePlayClick with useCallback
  const handlePlayClick = useCallback(async () => {
    if (isPlaying || !text) return;
    
    // Check cache first
    const cachedUrl = getCachedAudioUrl(text, selectedVoice);
    if (cachedUrl) {
      setAudioUrl(cachedUrl);
      setShowPlayer(true);
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await apiService.synthesizeSpeech(text, {
        voice_name: selectedVoice,
        speaking_rate: playbackSpeed,
      });
      
      if (response.audio_data) {
        const audioDataUrl = `data:audio/mp3;base64,${response.audio_data}`;
        
        // Cache the audio URL
        cacheAudioUrl(text, selectedVoice, audioDataUrl);
        
        setAudioUrl(audioDataUrl);
        setShowPlayer(true);
      }
    } catch (error) {
      console.error('TTS error:', error);
      setError('Failed to generate audio');
    } finally {
      setIsLoading(false);
    }
  }, [isPlaying, text, selectedVoice, playbackSpeed]);
  
  // useEffect for fetching voices
  useEffect(() => {
    if (showVoiceSelector) {
      fetchVoices();
    }
  }, [showVoiceSelector, fetchVoices]);
  
  // useEffect for auto play
  useEffect(() => {
    if (autoPlay && text) {
      handlePlayClick();
    }
  }, [text, autoPlay, handlePlayClick]);
  
  const handleVoiceChange = (e) => {
    const newVoice = e.target.value;
    onVoiceChange?.(newVoice);
    
    // Clear audio when voice changes
    setAudioUrl(null);
    setShowPlayer(false);
  };
  
  const handleSpeedChange = (speed) => {
    setPlaybackSpeed(speed);
    // Clear audio when speed changes
    setAudioUrl(null);
    setShowPlayer(false);
  };
  
  const handleDownload = async () => {
    if (!audioUrl) {
      await handlePlayClick();
    }
    
    if (audioUrl) {
      const link = document.createElement('a');
      link.href = audioUrl;
      link.download = `speech_${messageId || Date.now()}.mp3`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };
  
  return (
    <div className="tts-controls">
      <div className="tts-main-controls">
        <button
          className={`tts-play-button ${isPlaying ? 'playing' : ''}`}
          onClick={handlePlayClick}
          disabled={isLoading || !text}
          title={isPlaying ? 'Playing...' : 'Play audio'}
        >
          {isLoading ? (
            <span className="loading-icon">⟳</span>
          ) : isPlaying ? (
            <span className="sound-wave">
              <span></span>
              <span></span>
              <span></span>
            </span>
          ) : (
            <span className="play-icon">🔊</span>
          )}
        </button>
        
        {showVoiceSelector && voices.length > 0 && (
          <select
            className="voice-selector"
            value={selectedVoice || ''}
            onChange={handleVoiceChange}
            disabled={isLoading}
            style={{
              padding: '8px 12px',
              border: '1px solid #ddd',
              borderRadius: '6px',
              background: 'white',
              fontSize: '14px',
              cursor: 'pointer',
              maxWidth: '300px'
            }}
          >
            <option value="">Select voice...</option>
            {voices.map(voice => (
              <option key={voice.name} value={voice.name}>
                {voice.name} ({voice.type}, {voice.ssml_gender})
              </option>
            ))}
          </select>
        )}
        
        <div className="speed-controls" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <label style={{ fontSize: '14px', color: '#666' }}>Speed:</label>
          <div className="speed-buttons" style={{ display: 'flex', gap: '4px' }}>
            {[0.75, 1.0, 1.25, 1.5].map(speed => (
              <button
                key={speed}
                className={`speed-button ${playbackSpeed === speed ? 'active' : ''}`}
                onClick={() => handleSpeedChange(speed)}
                disabled={isLoading}
                style={{
                  padding: '4px 8px',
                  border: '1px solid #ddd',
                  background: playbackSpeed === speed ? '#667eea' : 'white',
                  color: playbackSpeed === speed ? 'white' : '#333',
                  borderRadius: '4px',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>
        
        <button
          className="download-button"
          onClick={handleDownload}
          disabled={isLoading || !text}
          title="Download audio"
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            border: '1px solid #ddd',
            background: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          ⬇️
        </button>
      </div>
      
      {error && (
        <div className="tts-error" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginTop: '8px',
          padding: '8px 12px',
          background: '#fee',
          border: '1px solid #fcc',
          borderRadius: '4px',
          color: '#c00',
          fontSize: '14px'
        }}>
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}
      
      {showPlayer && audioUrl && (
        <AudioPlayer
          src={audioUrl}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          autoPlay={true}
          showControls={true}
        />
      )}
    </div>
  );
};

export default TTSControls;