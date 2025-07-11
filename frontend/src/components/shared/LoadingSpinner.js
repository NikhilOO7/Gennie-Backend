import React from 'react';
import { MessageCircle } from 'lucide-react';
import { styles } from '../../utils/styles';

const LoadingSpinner = ({ message = 'Loading...', size = 48 }) => {
  return (
    <div style={styles.container}>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div style={styles.card}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ animation: 'spin 1s linear infinite' }}>
              <MessageCircle size={size} color="#4f46e5" />
            </div>
            <p style={{ marginTop: '16px', color: '#6b7280' }}>{message}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoadingSpinner;