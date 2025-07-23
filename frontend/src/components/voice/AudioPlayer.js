// components/voice/AudioPlayer.js
// Fixed version - proper function order to prevent initialization errors

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, Volume2, VolumeX, SkipBack, SkipForward, RotateCcw } from 'lucide-react';

const AudioPlayer = ({ 
  audioUrl, 
  audioData, 
  format = 'mp3',
  autoPlay = false,
  showControls = true,
  showProgress = true,
  showVolume = true,
  className = "",
  onPlay,
  onPause,
  onEnded,
  onTimeUpdate,
  onLoadStart,
  onLoadEnd,
  onError,
  isPlaying: externalIsPlaying,
  onPlayStateChange
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [error, setError] = useState(null);
  
  const audioRef = useRef(null);
  const progressRef = useRef(null);
  const volumeRef = useRef(null);

  // Define all callback functions FIRST before any useEffect that uses them
  const handlePlayPause = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;

    try {
      if (isPlaying) {
        audio.pause();
      } else {
        await audio.play();
      }
    } catch (error) {
      setError('Playback failed');
      onError?.(error);
    }
  }, [isPlaying, onError]);

  const handleSeek = useCallback((e) => {
    const audio = audioRef.current;
    const progress = progressRef.current;
    if (!audio || !progress) return;

    const bounds = progress.getBoundingClientRect();
    const percent = (e.clientX - bounds.left) / bounds.width;
    const newTime = percent * duration;
    
    audio.currentTime = Math.max(0, Math.min(newTime, duration));
  }, [duration]);

  const handleVolumeChange = useCallback((e) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newVolume = parseFloat(e.target.value);
    audio.volume = newVolume;
    setVolume(newVolume);
    
    if (newVolume === 0) {
      setIsMuted(true);
    } else if (isMuted) {
      setIsMuted(false);
    }
  }, [isMuted]);

  const handleMuteToggle = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.muted = !isMuted;
    setIsMuted(!isMuted);
  }, [isMuted]);

  const handleSkipBackward = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    
    audio.currentTime = Math.max(0, audio.currentTime - 10);
  }, []);

  const handleSkipForward = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    
    audio.currentTime = Math.min(duration, audio.currentTime + 10);
  }, [duration]);

  const handleRestart = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    
    audio.currentTime = 0;
  }, []);

  const handleSpeedChange = useCallback((speed) => {
    const audio = audioRef.current;
    if (!audio) return;
    
    audio.playbackRate = speed;
    setPlaybackRate(speed);
  }, []);

  const formatTime = useCallback((time) => {
    if (!time || !isFinite(time)) return '0:00';
    
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, []);

  // Sync with external play state
  useEffect(() => {
    if (typeof externalIsPlaying === 'boolean' && externalIsPlaying !== isPlaying) {
      setIsPlaying(externalIsPlaying);
      
      const audio = audioRef.current;
      if (audio) {
        if (externalIsPlaying && audio.paused) {
          audio.play().catch(console.error);
        } else if (!externalIsPlaying && !audio.paused) {
          audio.pause();
        }
      }
    }
  }, [externalIsPlaying, isPlaying]);

  // Initialize audio element
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    // Set up event listeners
    const handleLoadStart = () => {
      setIsLoading(true);
      setError(null);
      onLoadStart?.();
    };

    const handleLoadedData = () => {
      setIsLoading(false);
      setDuration(audio.duration);
      onLoadEnd?.();
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      onTimeUpdate?.(audio.currentTime);
    };

    const handlePlay = () => {
      setIsPlaying(true);
      onPlay?.();
      onPlayStateChange?.(true);
    };

    const handlePause = () => {
      setIsPlaying(false);
      onPause?.();
      onPlayStateChange?.(false);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
      onEnded?.();
      onPlayStateChange?.(false);
    };

    const handleError = (e) => {
      setIsLoading(false);
      setIsPlaying(false);
      setError('Failed to load audio');
      onError?.(e);
      onPlayStateChange?.(false);
    };

    const handleVolumeChangeEvent = () => {
      setVolume(audio.volume);
      setIsMuted(audio.muted);
    };

    const handleRateChange = () => {
      setPlaybackRate(audio.playbackRate);
    };

    // Add event listeners
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('loadeddata', handleLoadedData);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    audio.addEventListener('volumechange', handleVolumeChangeEvent);
    audio.addEventListener('ratechange', handleRateChange);

    return () => {
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('loadeddata', handleLoadedData);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('volumechange', handleVolumeChangeEvent);
      audio.removeEventListener('ratechange', handleRateChange);
    };
  }, [onPlay, onPause, onEnded, onTimeUpdate, onLoadStart, onLoadEnd, onError, onPlayStateChange]);

  // Handle audio source changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audioUrl) {
      audio.src = audioUrl;
    } else if (audioData) {
      // Handle base64 or blob data
      try {
        let blob;
        if (typeof audioData === 'string') {
          // Base64 data
          const binaryData = atob(audioData);
          const bytes = new Uint8Array(binaryData.length);
          for (let i = 0; i < binaryData.length; i++) {
            bytes[i] = binaryData.charCodeAt(i);
          }
          blob = new Blob([bytes], { type: `audio/${format}` });
        } else {
          // Already a blob
          blob = audioData;
        }
        
        const url = URL.createObjectURL(blob);
        audio.src = url;
        
        return () => URL.revokeObjectURL(url);
      } catch (error) {
        setError('Invalid audio data');
        onError?.(error);
      }
    }
  }, [audioUrl, audioData, format, onError]);

  // Auto play - NOW this can safely use handlePlayPause since it's defined above
  useEffect(() => {
    if (autoPlay && audioRef.current && !isPlaying && !isLoading && !error) {
      // Small delay to ensure audio is ready
      const timer = setTimeout(() => {
        handlePlayPause();
      }, 100);
      
      return () => clearTimeout(timer);
    }
  }, [autoPlay, isPlaying, isLoading, error, handlePlayPause]);

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  if (error) {
    return (
      <div className={`audio-player error ${className}`}>
        <div className="error-message">
          ⚠️ {error}
        </div>
      </div>
    );
  }

  return (
    <div className={`audio-player ${className}`}>
      <audio
        ref={audioRef}
        preload="metadata"
        style={{ display: 'none' }}
      />

      {showControls && (
        <div className="audio-controls">
          {/* Main play/pause button */}
          <button
            onClick={handlePlayPause}
            disabled={isLoading}
            className="play-pause-btn"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isLoading ? (
              <div className="loading-spinner" />
            ) : isPlaying ? (
              <Pause size={18} />
            ) : (
              <Play size={18} />
            )}
          </button>

          {/* Skip controls */}
          <button
            onClick={handleSkipBackward}
            className="skip-btn"
            aria-label="Skip backward 10 seconds"
          >
            <SkipBack size={16} />
          </button>

          <button
            onClick={handleRestart}
            className="restart-btn"
            aria-label="Restart"
          >
            <RotateCcw size={16} />
          </button>

          <button
            onClick={handleSkipForward}
            className="skip-btn"
            aria-label="Skip forward 10 seconds"
          >
            <SkipForward size={16} />
          </button>

          {/* Time display */}
          <div className="time-display">
            <span className="current-time">{formatTime(currentTime)}</span>
            <span className="duration">/ {formatTime(duration)}</span>
          </div>

          {/* Speed control */}
          <select
            value={playbackRate}
            onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
            className="speed-control"
            aria-label="Playback speed"
          >
            <option value={0.5}>0.5x</option>
            <option value={0.75}>0.75x</option>
            <option value={1}>1x</option>
            <option value={1.25}>1.25x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2x</option>
          </select>

          {/* Volume control */}
          {showVolume && (
            <div className="volume-control">
              <button
                onClick={handleMuteToggle}
                className="volume-btn"
                aria-label={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted || volume === 0 ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
              <input
                ref={volumeRef}
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="volume-slider"
                aria-label="Volume"
              />
            </div>
          )}
        </div>
      )}

      {/* Progress bar */}
      {showProgress && (
        <div className="progress-container">
          <div
            ref={progressRef}
            className="progress-bar"
            onClick={handleSeek}
            role="slider"
            aria-valuemin={0}
            aria-valuemax={duration}
            aria-valuenow={currentTime}
            aria-label="Audio progress"
          >
            <div
              className="progress-fill"
              style={{ width: `${progressPercent}%` }}
            />
            <div
              className="progress-handle"
              style={{ left: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div className="loading-overlay">
          Loading audio...
        </div>
      )}
    </div>
  );
};

export default AudioPlayer;