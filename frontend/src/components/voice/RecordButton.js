import React from 'react';

const RecordButton = ({
  isRecording,
  isPaused,
  onMouseDown,
  onMouseUp,
  onMouseLeave,
  onTouchStart,
  onTouchEnd,
  onClick,
  mode,
  audioLevel = 0,
  disabled = false,
}) => {
  const buttonClass = `record-button ${
    isRecording ? 'recording' : ''
  } ${isPaused ? 'paused' : ''} ${disabled ? 'disabled' : ''}`;
  
  const rippleStyle = {
    transform: `scale(${1 + audioLevel * 0.5})`,
    opacity: isRecording ? 0.3 + audioLevel * 0.7 : 0,
  };
  
  const innerRippleStyle = {
    transform: `scale(${1 + audioLevel * 0.3})`,
    opacity: isRecording ? 0.5 + audioLevel * 0.5 : 0,
  };
  
  return (
    <button
      className={buttonClass}
      onMouseDown={mode === 'push-to-talk' ? onMouseDown : undefined}
      onMouseUp={mode === 'push-to-talk' ? onMouseUp : undefined}
      onMouseLeave={mode === 'push-to-talk' ? onMouseLeave : undefined}
      onTouchStart={mode === 'push-to-talk' ? onTouchStart : undefined}
      onTouchEnd={mode === 'push-to-talk' ? onTouchEnd : undefined}
      onClick={mode === 'continuous' ? onClick : undefined}
      disabled={disabled}
      aria-label={isRecording ? 'Stop recording' : 'Start recording'}
    >
      {/* Outer ripple for audio level */}
      <div className="audio-ripple outer" style={rippleStyle} />
      
      {/* Inner ripple for audio level */}
      <div className="audio-ripple inner" style={innerRippleStyle} />
      
      {/* Recording indicator */}
      <div className="record-indicator">
        {isRecording && !isPaused ? (
          <div className="recording-animation">
            <span className="pulse-dot" />
            <span className="pulse-dot" />
            <span className="pulse-dot" />
          </div>
        ) : (
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="microphone-icon"
          >
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
          </svg>
        )}
      </div>
      
      {/* Push-to-talk indicator */}
      {mode === 'push-to-talk' && !disabled && (
        <div className="mode-indicator">
          <span className="mode-text">HOLD</span>
        </div>
      )}
    </button>
  );
};

export default RecordButton;