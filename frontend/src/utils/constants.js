// export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://34.30.186.82:8000/api/v1';
// export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://34.30.186.82:8000/api/v1';

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/api/v1';

export const EMOTION_ICONS = {
  positive: '😊',
  joy: '😊',
  happy: '😊',
  excitement: '🎉',
  negative: '😔',
  sad: '😢',
  angry: '😠',
  fear: '😨',
  neutral: '😐'
};

export const CONVERSATION_STYLES = [
  { value: 'friendly', label: 'Friendly' },
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Casual' },
  { value: 'professional', label: 'Professional' }
];

export const RESPONSE_LENGTHS = [
  { value: 'short', label: 'Short' },
  { value: 'medium', label: 'Medium' },
  { value: 'long', label: 'Long' }
];

export const EMOTIONAL_SUPPORT_LEVELS = [
  { value: 'minimal', label: 'Minimal' },
  { value: 'standard', label: 'Standard' },
  { value: 'high', label: 'High' }
];