import React, { useState, useRef, useCallback, useEffect } from 'react';
import RecordButton from './RecordButton';
import enhancedAudioService from '../../services/enhancedAudioService';
import apiService from '../../services/api';

const VoiceRecorder = ({ 
  onTranscript, 
  onRecordingStart, 
  onRecordingStop,
  onError,
  mode = 'push-to-talk',
  autoSend = true,
  language = 'en-US',
  maxDuration = 60000,
  enableStreaming = false
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
  const vadRef = useRef(null);

  useEffect(() => {
    checkPermission();
    return () => {
      stopRecording();
    };
  }, []);

  const checkPermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      setHasPermission(true);
    } catch (error) {
      setHasPermission(false);
    }
  };

  const startRecording = async () => {
    if (hasPermission === false) {
      onError?.('Microphone permission denied');
      return;
    }

    try {
      audioChunksRef.current = [];
      
      if (enableStreaming) {
        // Use streaming mode
        const { stream, stop } = await enhancedAudioService.startStreaming((chunk) => {
          // Handle streaming chunks
          if (onTranscript) {
            onTranscript(null, chunk, true); // streaming flag
          }
        });
        
        streamRef.current = { stream, stop };
      } else {
        // Traditional recording mode
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: 16000,
          } 
        });
        
        streamRef.current = stream;
        
        // Set up level monitoring
        levelMeterRef.current = enhancedAudioService.createLevelMeter(setAudioLevel);
        const source = await enhancedAudioService.audioContext.createMediaStreamSource(stream);
        source.connect(levelMeterRef.current.analyser);
        levelMeterRef.current.start();
        
        // Set up VAD
        vadRef.current = enhancedAudioService.createVAD();
        
        // Set up MediaRecorder
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
          ? 'audio/webm;codecs=opus' 
          : 'audio/webm';
        
        const mediaRecorder = new MediaRecorder(stream, {
          mimeType,
          audioBitsPerSecond: 128000,
        });
        
        mediaRecorderRef.current = mediaRecorder;
        
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };
        
        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          
          try {
            const wavBlob = await enhancedAudioService.convertToWav(audioBlob);
            handleRecordingComplete(wavBlob);
          } catch (error) {
            console.error('Audio conversion error:', error);
            handleRecordingComplete(audioBlob);
          }
        };
        
        mediaRecorder.start(100);
      }
      
      setIsRecording(true);
      setRecordingTime(0);
      
      // Start timer
      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startTime;
        setRecordingTime(elapsed);
        
        if (elapsed >= maxDuration) {
          stopRecording();
        }
      }, 100);
      
      onRecordingStart?.();
      
    } catch (error) {
      console.error('Failed to start recording:', error);
      onError?.('Failed to start recording');
    }
  };

  const stopRecording = () => {
    if (levelMeterRef.current) {
      levelMeterRef.current.stop();
      levelMeterRef.current = null;
    }
    
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
    
    if (streamRef.current) {
      if (streamRef.current.stop) {
        streamRef.current.stop();
      } else if (streamRef.current.getTracks) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      streamRef.current = null;
    }
    
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    
    setIsRecording(false);
    setAudioLevel(0);
    onRecordingStop?.();
  };

  const handleRecordingComplete = async (audioBlob) => {
    if (autoSend) {
      try {
        const result = await apiService.transcribeAudio(audioBlob, language);
        onTranscript?.(result.transcript, audioBlob);
      } catch (error) {
        console.error('Transcription error:', error);
        onError?.('Transcription failed');
      }
    } else {
      onTranscript?.(null, audioBlob);
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
          onMouseDown={mode === 'push-to-talk' ? startRecording : undefined}
          onMouseUp={mode === 'push-to-talk' ? stopRecording : undefined}
          onMouseLeave={mode === 'push-to-talk' ? stopRecording : undefined}
          onTouchStart={mode === 'push-to-talk' ? startRecording : undefined}
          onTouchEnd={mode === 'push-to-talk' ? stopRecording : undefined}
          onClick={mode === 'continuous' ? (isRecording ? stopRecording : startRecording) : undefined}
          mode={mode}
          audioLevel={audioLevel}
          disabled={hasPermission === false}
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
    </div>
  );
};

export default VoiceRecorder;