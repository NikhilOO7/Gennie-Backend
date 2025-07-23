import React from 'react';
import { Volume2, VolumeX, Zap, Wifi } from 'lucide-react';

const VoiceControls = ({ voiceSettings, onSettingsChange, sessionStats, connectionQuality }) => {
  const handleVolumeToggle = () => {
    // Implement volume control
  };

  const handleEnhancementToggle = () => {
    onSettingsChange({
      enableEnhancement: !voiceSettings.enableEnhancement
    });
  };

  return (
    <div className="voice-controls">
      <button 
        className="control-btn"
        onClick={handleVolumeToggle}
        aria-label="Toggle Volume"
      >
        <Volume2 size={18} />
      </button>
      
      <button 
        className={`control-btn ${voiceSettings.enableEnhancement ? 'active' : ''}`}
        onClick={handleEnhancementToggle}
        aria-label="Toggle Enhancement"
      >
        <Zap size={18} />
      </button>
      
      <div className={`connection-quality ${connectionQuality}`}>
        <Wifi size={18} />
      </div>
    </div>
  );
};

export default VoiceControls;