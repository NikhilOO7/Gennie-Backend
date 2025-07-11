import React, { useState, useEffect } from 'react';
import { User, Activity, MessageCircle, Clock } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import apiService from '../../services/api';
import { styles } from '../../utils/styles';

const UserProfile = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchUserStats();
  }, []);

  const fetchUserStats = async () => {
    try {
      const data = await apiService.getUserStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch user stats:', error);
    }
  };

  return (
    <div style={{ padding: '24px', backgroundColor: '#f9fafb', height: '100%', overflowY: 'auto' }}>
      <div style={{ ...styles.card, marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '24px' }}>
          Profile
        </h2>

        {/* User Info */}
        <div style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
            <div style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              backgroundColor: '#e0e7ff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <User size={40} color="#4338ca" />
            </div>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: '600' }}>
                {user.first_name} {user.last_name}
              </h3>
              <p style={{ color: '#6b7280' }}>@{user.username}</p>
              <p style={{ color: '#6b7280' }}>{user.email}</p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
            <div style={{
              padding: '16px',
              backgroundColor: '#f3f4f6',
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                {user.total_chats || 0}
              </p>
              <p style={{ fontSize: '12px', color: '#6b7280' }}>Total Chats</p>
            </div>
            <div style={{
              padding: '16px',
              backgroundColor: '#f3f4f6',
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                {user.total_messages || 0}
              </p>
              <p style={{ fontSize: '12px', color: '#6b7280' }}>Total Messages</p>
            </div>
          </div>
        </div>

        {/* User Stats */}
        {stats && (
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
              Usage Statistics
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
              <div style={{
                padding: '16px',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                border: '1px solid #e5e7eb'
              }}>
                <Activity size={20} color="#4f46e5" style={{ marginBottom: '8px' }} />
                <p style={{ fontSize: '20px', fontWeight: '600' }}>
                  {stats.total_tokens_used || 0}
                </p>
                <p style={{ fontSize: '12px', color: '#6b7280' }}>Tokens Used</p>
              </div>
              <div style={{
                padding: '16px',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                border: '1px solid #e5e7eb'
              }}>
                <MessageCircle size={20} color="#4f46e5" style={{ marginBottom: '8px' }} />
                <p style={{ fontSize: '20px', fontWeight: '600' }}>
                  {stats.avg_messages_per_chat || 0}
                </p>
                <p style={{ fontSize: '12px', color: '#6b7280' }}>Avg Messages/Chat</p>
              </div>
              <div style={{
                padding: '16px',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                border: '1px solid #e5e7eb'
              }}>
                <Clock size={20} color="#4f46e5" style={{ marginBottom: '8px' }} />
                <p style={{ fontSize: '20px', fontWeight: '600' }}>
                  {stats.last_active || 'N/A'}
                </p>
                <p style={{ fontSize: '12px', color: '#6b7280' }}>Last Active</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserProfile;