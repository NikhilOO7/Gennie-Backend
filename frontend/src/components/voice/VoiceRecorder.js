// components/voice/VoiceRecorder.js
import React, { useState, useRef, useCallback, useEffect } from 'react';
import RecordButton from './RecordButton';
import apiService from '../../services/api';

const VoiceRecorder = ({ 
  onTranscript, 
  onRecordingStart, 
  onRecordingStop,
  onError,
  onAudioLevel,
  mode = 'push-to-talk',
  autoSend = true,
  language = 'en-US',
  maxDuration = 60000,
  enableStreaming = false,
  disabled = false
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [hasPermission, setHasPermission] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const levelMeterRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);

  useEffect(() => {
    checkPermission();
    return () => {
      stopRecording();
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  // Report audio level to parent
  useEffect(() => {
    if (onAudioLevel) {
      onAudioLevel(audioLevel);
    }
  }, [audioLevel, onAudioLevel]);

  const checkPermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      setHasPermission(true);
    } catch (error) {
      setHasPermission(false);
      onError?.('Microphone permission denied');
    }
  };

  const startRecording = async () => {
    if (disabled || hasPermission === false || isRecording) {
      return;
    }

    try {
      audioChunksRef.current = [];
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        } 
      });
      
      streamRef.current = stream;
      
      // Set up audio level monitoring
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      microphone.connect(analyser);
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      
      // Monitor audio levels
      const updateLevel = () => {
        if (!analyserRef.current || !isRecording) return;
        
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
        
        // Calculate average level
        const average = dataArray.reduce((acc, val) => acc + val, 0) / dataArray.length;
        const normalizedLevel = Math.min(average / 128, 1); // Normalize to 0-1
        setAudioLevel(normalizedLevel);
        
        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
      
      // Set up MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' : 'audio/webm';
      
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000
      });
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        handleRecordingComplete(audioBlob);
      };
      
      mediaRecorderRef.current.onerror = (error) => {
        console.error('MediaRecorder error:', error);
        onError?.('Recording failed');
        stopRecording();
      };
      
      // Start recording
      mediaRecorderRef.current.start();
      setIsRecording(true);
      onRecordingStart?.();
      
      // Start timer
      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startTime;
        setRecordingTime(elapsed);
        
        // Auto-stop at max duration
        if (elapsed >= maxDuration) {
          stopRecording();
        }
      }, 100);
      
    } catch (error) {
      console.error('Failed to start recording:', error);
      onError?.('Failed to start recording: ' + error.message);
    }
  };

  const stopRecording = () => {
    if (analyserRef.current) {
      analyserRef.current = null;
    }
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (error) {
        console.error('Error stopping MediaRecorder:', error);
      }
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop();
      });
      streamRef.current = null;
    }
    
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    
    setIsRecording(false);
    setAudioLevel(0);
    setRecordingTime(0);
    onRecordingStop?.();
  };

  const handleRecordingComplete = async (audioBlob) => {
    if (!audioBlob || audioBlob.size === 0) {
      onError?.('No audio recorded');
      return;
    }

    if (autoSend) {
      try {
        console.log('Sending audio for transcription...');
        const result = await apiService.transcribeAudio(audioBlob, language);
        console.log('Transcription result:', result);
        
        if (result.transcript) {
          onTranscript?.(result.transcript, audioBlob, false);
        } else {
          onError?.('No transcript received');
        }
      } catch (error) {
        console.error('Transcription error:', error);
        onError?.('Transcription failed: ' + error.message);
      }
    } else {
      onTranscript?.(null, audioBlob, false);
    }
  };

  const formatTime = (ms) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="voice-recorder">
      <div className="recording-controls">
        <RecordButton
          isRecording={isRecording}
          onMouseDown={mode === 'push-to-talk' && !disabled ? startRecording : undefined}
          onMouseUp={mode === 'push-to-talk' && isRecording ? stopRecording : undefined}
          onMouseLeave={mode === 'push-to-talk' && isRecording ? stopRecording : undefined}
          onTouchStart={mode === 'push-to-talk' && !disabled ? startRecording : undefined}
          onTouchEnd={mode === 'push-to-talk' && isRecording ? stopRecording : undefined}
          onClick={mode === 'continuous' && !disabled ? (isRecording ? stopRecording : startRecording) : undefined}
          mode={mode}
          audioLevel={audioLevel}
          disabled={disabled || hasPermission === false}
        />
        
        {isRecording && (
          <div className="recording-info">
            <span className="recording-time">{formatTime(recordingTime)}</span>
          </div>
        )}
      </div>
      
      {hasPermission === false && (
        <div className="permission-warning">
          <p>Microphone permission required</p>
          <button onClick={checkPermission}>Enable Microphone</button>
        </div>
      )}
      
      {disabled && hasPermission && (
        <div className="disabled-warning">
          <p>Waiting for connection...</p>
        </div>
      )}
    </div>
  );
};

export default VoiceRecorder;