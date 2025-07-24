import React, { useState, useEffect } from 'react';
import { X, Volume2, Mic, Zap, Globe } from 'lucide-react';
import apiService from '../../services/api';

const VoiceSettings = ({ settings, onSettingsChange, onClose }) => {
  const [localSettings, setLocalSettings] = useState(settings);
  const [availableVoices, setAvailableVoices] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const languageOptions = [
    { code: 'en-US', label: 'English (US)', flag: '🇺🇸' },
    { code: 'en-GB', label: 'English (UK)', flag: '🇬🇧' },
    { code: 'es-US', label: 'Spanish (US)', flag: '🇪🇸' },
    { code: 'fr-FR', label: 'French', flag: '🇫🇷' },
    { code: 'de-DE', label: 'German', flag: '🇩🇪' },
    { code: 'it-IT', label: 'Italian', flag: '🇮🇹' },
    { code: 'pt-BR', label: 'Portuguese (Brazil)', flag: '🇧🇷' },
    { code: 'ja-JP', label: 'Japanese', flag: '🇯🇵' },
    { code: 'ko-KR', label: 'Korean', flag: '🇰🇷' },
    { code: 'zh-CN', label: 'Chinese (Simplified)', flag: '🇨🇳' }
  ];

  useEffect(() => {
    setLocalSettings(settings);
    fetchVoices(settings.voice_language);
  }, [settings]);

// Add new error state
const [availableVoices, setAvailableVoices] = useState([]);
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState(null);

const fetchVoices = async (language) => {
  setIsLoading(true);
  setError(null);
  try {
    const response = await apiService.getVoices(language);
    setAvailableVoices(response.voices);
  } catch (error) {
    console.error('Failed to fetch voices:', error);
    setError('Failed to load available voices. Please try again later.');
    // Optionally set default voices as fallback
  } finally {
    setIsLoading(false);
  }
};

  const handleSettingChange = (key, value) => {
    const newSettings = { ...localSettings, [key]: value };
    setLocalSettings(newSettings);
  };

  const handleSave = async () => {
    try {
      await apiService.updateVoicePreferences(localSettings);
      onSettingsChange(localSettings);
      onClose();
    } catch (error) {
      console.error('Failed to save voice preferences:', error);
    }
  };

  const handleReset = () => {
    const defaultSettings = {
      voice_name: 'en-US-Neural2-F',
      speaking_rate: 1.0,
      pitch: 0.0,
      voice_language: 'en-US',
    };
    setLocalSettings(defaultSettings);
  };

  const handleLanguageChange = (language) => {
    handleSettingChange('voice_language', language);
    fetchVoices(language);
  };

  const testVoice = async () => {
    setIsLoading(true);
    try {
      const testText = "Hello! This is a test of your selected voice settings.";
      const audio = await apiService.synthesizeSpeech(testText, {
        voice_name: localSettings.voice_name,
        language_code: localSettings.voice_language,
        speaking_rate: localSettings.speaking_rate,
        pitch: localSettings.pitch,
      });
      const audioData = new Audio(`data:audio/mp3;base64,${audio.audio_data}`);
      audioData.play();
    } catch (error) {
      console.error('Voice test failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const currentVoices = availableVoices;

  return (
    <div className="voice-settings-panel">
      <div className="settings-header">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Volume2 size={20} />
          Voice Settings
        </h3>
        <button
          onClick={onClose}
          className="close-btn"
          aria-label="Close Settings"
        >
          <X size={20} />
        </button>
      </div>

      <div className="settings-content">
        {/* Language Selection */}
        <div className="setting-group">
          <label className="flex items-center gap-2">
            <Globe size={16} />
            Language
          </label>
          <select
            value={localSettings.language}
            onChange={(e) => handleLanguageChange(e.target.value)}
            className="w-full"
          >
            {languageOptions.map(lang => (
              <option key={lang.code} value={lang.code}>
                {lang.flag} {lang.label}
              </option>
            ))}
          </select>
        </div>

        {/* Voice Selection */}
        <div className="setting-group">
          <label className="flex items-center gap-2">
            <Mic size={16} />
            Voice
          </label>
          <select
            value={localSettings.voice}
            onChange={(e) => handleSettingChange('voice', e.target.value)}
            className="w-full"
          >
            {currentVoices.map(voice => (
              <option key={voice.name} value={voice.name}>
                {voice.label}
              </option>
            ))}
          </select>
          <button
            onClick={testVoice}
            disabled={isLoading}
            className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {isLoading ? 'Testing...' : 'Test Voice'}
          </button>
        </div>

        {/* Speed Control */}
        <div className="setting-group">
          <label>
            Speaking Speed: {localSettings.speed.toFixed(1)}x
          </label>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={localSettings.speed}
            onChange={(e) => handleSettingChange('speed', parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Slower</span>
            <span>Normal</span>
            <span>Faster</span>
          </div>
        </div>

        {/* Pitch Control */}
        <div className="setting-group">
          <label>
            Voice Pitch: {localSettings.pitch > 0 ? '+' : ''}{localSettings.pitch.toFixed(1)} st
          </label>
          <input
            type="range"
            min="-5.0"
            max="5.0"
            step="0.5"
            value={localSettings.pitch}
            onChange={(e) => handleSettingChange('pitch', parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Lower</span>
            <span>Normal</span>
            <span>Higher</span>
          </div>
        </div>

        {/* Enhancement Options */}
        <div className="setting-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="enhancement"
              checked={localSettings.enableEnhancement}
              onChange={(e) => handleSettingChange('enableEnhancement', e.target.checked)}
            />
            <label htmlFor="enhancement" className="flex items-center gap-2 mb-0">
              <Zap size={16} />
              Enable Audio Enhancement
            </label>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Improves audio quality with advanced processing (may increase latency)
          </p>
        </div>

        {/* Emotion Detection */}
        <div className="setting-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="emotion"
              checked={localSettings.emotionDetection}
              onChange={(e) => handleSettingChange('emotionDetection', e.target.checked)}
            />
            <label htmlFor="emotion" className="flex items-center gap-2 mb-0">
              😊 Emotion Detection
            </label>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Detects emotions in speech for better AI responses
          </p>
        </div>

        {/* Advanced Settings */}
        <div className="setting-group">
          <details>
            <summary className="font-medium cursor-pointer">Advanced Settings</summary>
            <div className="mt-3 space-y-3">
              {/* Noise Suppression */}
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="noiseSuppression"
                  checked={localSettings.noiseSuppression ?? true}
                  onChange={(e) => handleSettingChange('noiseSuppression', e.target.checked)}
                />
                <label htmlFor="noiseSuppression" className="mb-0">
                  Noise Suppression
                </label>
              </div>

              {/* Echo Cancellation */}
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="echoCancellation"
                  checked={localSettings.echoCancellation ?? true}
                  onChange={(e) => handleSettingChange('echoCancellation', e.target.checked)}
                />
                <label htmlFor="echoCancellation" className="mb-0">
                  Echo Cancellation
                </label>
              </div>

              {/* Auto Gain Control */}
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="autoGainControl"
                  checked={localSettings.autoGainControl ?? true}
                  onChange={(e) => handleSettingChange('autoGainControl', e.target.checked)}
                />
                <label htmlFor="autoGainControl" className="mb-0">
                  Auto Gain Control
                </label>
              </div>
            </div>
          </details>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="settings-footer">
        <button
          onClick={handleReset}
          className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Reset to Defaults
        </button>
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceSettings;