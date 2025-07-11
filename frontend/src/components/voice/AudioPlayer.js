import React, { useState, useRef, useEffect } from 'react';

const AudioPlayer = ({
  src,
  onPlay,
  onPause,
  onEnded,
  onError,
  showControls = true,
  autoPlay = false,
  className = '',
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const audioRef = useRef(null);
  const progressBarRef = useRef(null);
  const animationRef = useRef(null);
  
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    
    // Set up event listeners
    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
      setIsLoading(false);
      if (autoPlay) {
        play();
      }
    };
    
    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };
    
    const handleEnded = () => {
      setIsPlaying(false);
      onEnded?.();
    };
    
    const handleError = (e) => {
      setError('Failed to load audio');
      setIsLoading(false);
      onError?.(e);
    };
    
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    
    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [autoPlay, onEnded, onError]);
  
  useEffect(() => {
    // Update audio element when src changes
    if (audioRef.current && src) {
      audioRef.current.src = src;
      setIsLoading(true);
      setError(null);
      setCurrentTime(0);
      audioRef.current.load();
    }
  }, [src]);
  
  const play = async () => {
    try {
      await audioRef.current.play();
      setIsPlaying(true);
      onPlay?.();
    } catch (error) {
      console.error('Playback failed:', error);
      setError('Playback failed');
    }
  };
  
  const pause = () => {
    audioRef.current.pause();
    setIsPlaying(false);
    onPause?.();
  };
  
  const togglePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };
  
  const handleProgressChange = (e) => {
    const audio = audioRef.current;
    const clickX = e.nativeEvent.offsetX;
    const width = progressBarRef.current.offsetWidth;
    const newTime = (clickX / width) * duration;
    
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };
  
  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    audioRef.current.volume = newVolume;
  };
  
  const handlePlaybackRateChange = (rate) => {
    setPlaybackRate(rate);
    audioRef.current.playbackRate = rate;
  };
  
  const formatTime = (time) => {
    if (isNaN(time)) return '0:00';
    
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };
  
  const progressPercentage = duration ? (currentTime / duration) * 100 : 0;
  
  return (
    <div className={`audio-player ${className}`}>
      <audio
        ref={audioRef}
        preload="metadata"
      />
      
      {error ? (
        <div className="audio-error">
          <span className="error-icon">⚠️</span>
          <span className="error-message">{error}</span>
        </div>
      ) : (
        <>
          <div className="audio-main-controls">
            <button
              className="play-pause-button"
              onClick={togglePlayPause}
              disabled={isLoading || !src}
            >
              {isLoading ? (
                <span className="loading-spinner">⟳</span>
              ) : isPlaying ? (
                <span className="pause-icon">⏸</span>
              ) : (
                <span className="play-icon">▶</span>
              )}
            </button>
            
            {showControls && (
              <>
                <div className="time-display" style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  minWidth: '80px',
                  fontSize: '14px',
                  color: '#666'
                }}>
                  <span className="current-time">{formatTime(currentTime)}</span>
                  <span className="time-separator">/</span>
                  <span className="total-time">{formatTime(duration)}</span>
                </div>
                
                <div
                  ref={progressBarRef}
                  className="progress-bar"
                  onClick={handleProgressChange}
                  style={{
                    flex: 1,
                    height: '32px',
                    display: 'flex',
                    alignItems: 'center',
                    cursor: 'pointer',
                    padding: '0 8px'
                  }}
                >
                  <div className="progress-bg" style={{
                    position: 'relative',
                    width: '100%',
                    height: '6px',
                    background: '#e0e0e0',
                    borderRadius: '3px',
                    overflow: 'visible'
                  }}>
                    <div
                      className="progress-fill"
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        height: '100%',
                        width: `${progressPercentage}%`,
                        background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                        borderRadius: '3px',
                        transition: 'width 0.1s ease'
                      }}
                    />
                    <div
                      className="progress-handle"
                      style={{
                        position: 'absolute',
                        top: '50%',
                        left: `${progressPercentage}%`,
                        transform: 'translate(-50%, -50%)',
                        width: '16px',
                        height: '16px',
                        background: 'white',
                        border: '3px solid #667eea',
                        borderRadius: '50%',
                        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                        transition: 'all 0.1s ease'
                      }}
                    />
                  </div>
                </div>
              </>
            )}
          </div>
          
          {showControls && (
            <div className="audio-secondary-controls" style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px',
              marginTop: '12px'
            }}>
              <div className="playback-rate-control" style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <label style={{ fontSize: '14px', color: '#666' }}>Speed:</label>
                <div className="rate-buttons" style={{ display: 'flex', gap: '4px' }}>
                  {[0.5, 0.75, 1, 1.25, 1.5, 2].map(rate => (
                    <button
                      key={rate}
                      className={`rate-button ${playbackRate === rate ? 'active' : ''}`}
                      onClick={() => handlePlaybackRateChange(rate)}
                      style={{
                        padding: '4px 8px',
                        border: '1px solid #ddd',
                        background: playbackRate === rate ? '#667eea' : 'white',
                        color: playbackRate === rate ? 'white' : '#333',
                        borderRadius: '4px',
                        fontSize: '12px',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="volume-control" style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span className="volume-icon" style={{ fontSize: '18px' }}>
                  {volume === 0 ? '🔇' : volume < 0.5 ? '🔉' : '🔊'}
                </span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={volume}
                  onChange={handleVolumeChange}
                  className="volume-slider"
                  style={{
                    width: '100px',
                    height: '4px',
                    appearance: 'none',
                    background: '#e0e0e0',
                    borderRadius: '2px',
                    outline: 'none'
                  }}
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AudioPlayer;