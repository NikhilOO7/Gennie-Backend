// Fix for VoiceVisualizer.js infinite loop
// Replace your entire VoiceVisualizer.js with this corrected version:

import React, { useEffect, useRef } from 'react';

const VoiceVisualizer = ({ 
  audioLevel = 0, 
  isRecording = false, 
  isProcessing = false,
  isPlaying = false,
  className = "",
  width = 300,
  height = 100,
  barCount = 32,
  visualizerStyle = 'waveform' // Renamed from 'style'
}) => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const animationDataRef = useRef([]); // Use ref instead of state to avoid re-renders

  // Initialize animation data once
  useEffect(() => {
    animationDataRef.current = Array(barCount).fill(0).map(() => Math.random() * 0.1);
  }, [barCount]);

  // Animation loop - removed animationData from dependencies
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const devicePixelRatio = window.devicePixelRatio || 1;
    
    // Set canvas size for crisp rendering
    canvas.width = width * devicePixelRatio;
    canvas.height = height * devicePixelRatio;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(devicePixelRatio, devicePixelRatio);

    const animate = () => {
      if (!canvas || !ctx) return;
      
      ctx.clearRect(0, 0, width, height);

      if (visualizerStyle === 'waveform') {
        drawWaveform(ctx);
      } else if (visualizerStyle === 'circular') {
        drawCircular(ctx);
      } else {
        drawBars(ctx);
      }

      // Update animation data directly in ref (no setState call)
      animationDataRef.current = animationDataRef.current.map((value, index) => {
        if (isRecording) {
          // More dynamic animation when recording
          return Math.sin(Date.now() * 0.01 + index * 0.5) * audioLevel * 0.8 + 
                 Math.random() * audioLevel * 0.2;
        } else if (isProcessing) {
          // Pulsing animation when processing
          return Math.sin(Date.now() * 0.005 + index * 0.3) * 0.3;
        } else if (isPlaying) {
          // Playing animation
          return Math.sin(Date.now() * 0.008 + index * 0.4) * 0.5;
        } else {
          // Idle animation
          return Math.sin(Date.now() * 0.002 + index * 0.2) * 0.1;
        }
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [width, height, audioLevel, isRecording, isProcessing, isPlaying, visualizerStyle]); // Removed animationData dependency

  const drawWaveform = (ctx) => {
    const centerY = height / 2;
    const barWidth = width / barCount;

    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    if (isRecording) {
      gradient.addColorStop(0, '#ef4444');
      gradient.addColorStop(0.5, '#f97316');
      gradient.addColorStop(1, '#eab308');
    } else if (isProcessing) {
      gradient.addColorStop(0, '#3b82f6');
      gradient.addColorStop(1, '#8b5cf6');
    } else if (isPlaying) {
      gradient.addColorStop(0, '#10b981');
      gradient.addColorStop(1, '#06b6d4');
    } else {
      gradient.addColorStop(0, '#6b7280');
      gradient.addColorStop(1, '#9ca3af');
    }

    ctx.fillStyle = gradient;

    // Draw waveform bars using ref data
    animationDataRef.current.forEach((value, index) => {
      const barHeight = Math.abs(value) * height * 0.8;
      const x = index * barWidth;

      // Add some randomness for more organic look
      const adjustedHeight = barHeight + Math.sin(Date.now() * 0.01 + index) * 2;
      
      ctx.fillRect(x, centerY - adjustedHeight / 2, barWidth - 1, adjustedHeight);
    });

    // Add glow effect
    if (isRecording || isProcessing) {
      ctx.shadowColor = isRecording ? '#ef4444' : '#3b82f6';
      ctx.shadowBlur = 20;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;
    }
  };

  const drawCircular = (ctx) => {
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.3;

    // Clear shadow
    ctx.shadowBlur = 0;

    // Draw circular visualizer using ref data
    animationDataRef.current.forEach((value, index) => {
      const angle = (index / barCount) * Math.PI * 2;
      const barLength = Math.abs(value) * radius * 0.8;
      
      const startX = centerX + Math.cos(angle) * radius;
      const startY = centerY + Math.sin(angle) * radius;
      const endX = centerX + Math.cos(angle) * (radius + barLength);
      const endY = centerY + Math.sin(angle) * (radius + barLength);

      // Color based on state
      if (isRecording) {
        ctx.strokeStyle = `hsl(${(index / barCount) * 60}, 70%, 60%)`;
      } else if (isProcessing) {
        ctx.strokeStyle = `hsl(${220 + (index / barCount) * 40}, 70%, 60%)`;
      } else if (isPlaying) {
        ctx.strokeStyle = `hsl(${160 + (index / barCount) * 40}, 70%, 60%)`;
      } else {
        ctx.strokeStyle = `hsl(0, 0%, ${50 + (index / barCount) * 30}%)`;
      }

      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
    });

    // Draw center circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.2, 0, Math.PI * 2);
    ctx.fillStyle = isRecording ? '#ef4444' : isProcessing ? '#3b82f6' : isPlaying ? '#10b981' : '#6b7280';
    ctx.fill();
  };

  const drawBars = (ctx) => {
    const barWidth = (width - (barCount - 1) * 2) / barCount;
    const maxBarHeight = height * 0.8;

    // Create gradient
    const gradient = ctx.createLinearGradient(0, height, 0, 0);
    if (isRecording) {
      gradient.addColorStop(0, '#ef4444');
      gradient.addColorStop(1, '#fbbf24');
    } else if (isProcessing) {
      gradient.addColorStop(0, '#3b82f6');
      gradient.addColorStop(1, '#8b5cf6');
    } else if (isPlaying) {
      gradient.addColorStop(0, '#10b981');
      gradient.addColorStop(1, '#06b6d4');
    } else {
      gradient.addColorStop(0, '#6b7280');
      gradient.addColorStop(1, '#d1d5db');
    }

    ctx.fillStyle = gradient;

    // Draw bars using ref data
    animationDataRef.current.forEach((value, index) => {
      const barHeight = Math.abs(value) * maxBarHeight;
      const x = index * (barWidth + 2);
      const y = height - barHeight;

      ctx.fillRect(x, y, barWidth, barHeight);
    });
  };

  return (
    <div className={`voice-visualizer-container ${className}`}>
      <canvas
        ref={canvasRef}
        className="voice-visualizer-canvas"
        style={{
          borderRadius: '8px',
          background: 'rgba(0, 0, 0, 0.1)'
        }}
      />
      
      {/* Status indicator */}
      <div className="mt-2 text-center text-sm">
        {isRecording && (
          <span className="text-red-500 font-medium animate-pulse">
            🔴 Recording... ({Math.round(audioLevel * 100)}%)
          </span>
        )}
        {isProcessing && (
          <span className="text-blue-500 font-medium">
            ⚡ Processing...
          </span>
        )}
        {isPlaying && (
          <span className="text-green-500 font-medium">
            🔊 Playing...
          </span>
        )}
        {!isRecording && !isProcessing && !isPlaying && (
          <span className="text-gray-500">
            Ready
          </span>
        )}
      </div>
    </div>
  );
};

export default VoiceVisualizer;