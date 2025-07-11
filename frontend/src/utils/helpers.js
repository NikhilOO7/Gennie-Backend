export const getErrorMessage = (error) => {
  if (typeof error === 'string') return error;
  if (error?.detail) {
    if (Array.isArray(error.detail)) {
      return error.detail.map(e => e.msg || e.message || 'Validation error').join(', ');
    }
    return error.detail;
  }
  if (error?.message) return error.message;
  if (error?.msg) return error.msg;
  return 'An error occurred';
};

export const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

export const formatDate = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleDateString();
};

export const playNotificationSound = (enabled = true) => {
  if (enabled) {
    const audio = new Audio('/notification.mp3');
    audio.play().catch(e => console.log('Could not play sound:', e));
  }
};

export const getStatusColor = (status) => {
  switch (status) {
    case 'healthy':
      return '#10b981';
    case 'degraded':
      return '#f59e0b';
    case 'unhealthy':
      return '#ef4444';
    default:
      return '#6b7280';
  }
};

export const saveToLocalStorage = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error('Error saving to localStorage:', error);
  }
};

export const getFromLocalStorage = (key, defaultValue = null) => {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.error('Error reading from localStorage:', error);
    return defaultValue;
  }
};