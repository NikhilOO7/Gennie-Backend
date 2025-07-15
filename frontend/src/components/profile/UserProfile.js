import React, { useState, useEffect } from 'react';
import { User, Save, Edit2, TrendingUp, MessageCircle, Hash } from 'lucide-react';
import apiService from '../../services/api';
import { styles } from '../../utils/styles';
import LoadingSpinner from '../shared/LoadingSpinner';

const UserProfile = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingTopics, setEditingTopics] = useState(false);
  const [topicsData, setTopicsData] = useState({
    selected_topics: [],
    available_topics: [],
    topic_stats: {},
    recommendations: []
  });
  const [selectedTopics, setSelectedTopics] = useState([]);

  useEffect(() => {
    fetchUserData();
    fetchTopicsData();
  }, []);

  const fetchUserData = async () => {
    try {
      const userData = await apiService.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
    }
  };

  const fetchTopicsData = async () => {
    try {
      const data = await apiService.getUserTopics();
      setTopicsData(data);
      setSelectedTopics(data.selected_topics || []);
    } catch (error) {
      console.error('Failed to fetch topics:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTopic = (topicId) => {
    if (!editingTopics) return;
    
    setSelectedTopics(prev => {
      if (prev.includes(topicId)) {
        return prev.filter(id => id !== topicId);
      } else {
        return [...prev, topicId];
      }
    });
  };

  const saveTopics = async () => {
    setSaving(true);
    try {
      const updatedData = await apiService.updateUserTopics(selectedTopics);
      setTopicsData(updatedData);
      setEditingTopics(false);
      
      // Show success message
      const toast = document.createElement('div');
      toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        z-index: 1000;
      `;
      toast.textContent = 'Topics saved successfully!';
      document.body.appendChild(toast);
      
      setTimeout(() => toast.remove(), 3000);
    } catch (error) {
      console.error('Failed to save topics:', error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  const { topic_stats } = topicsData;

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* User Info Section */}
      <div style={styles.card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '32px',
            fontWeight: '600'
          }}>
            {user?.first_name?.charAt(0) || 'U'}
          </div>
          <div>
            <h2 style={{ fontSize: '24px', marginBottom: '4px' }}>
              {user?.full_name || 'User'}
            </h2>
            <p style={{ color: '#6b7280' }}>{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Interest Topics Section */}
      <div style={{ ...styles.card, marginTop: '20px' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '20px'
        }}>
          <h3 style={{ fontSize: '20px', fontWeight: '600' }}>My Interest Topics</h3>
          <button
            onClick={() => editingTopics ? saveTopics() : setEditingTopics(true)}
            disabled={saving}
            style={{
              ...styles.button,
              padding: '8px 16px',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            {editingTopics ? (
              <>
                <Save size={16} />
                {saving ? 'Saving...' : 'Save Topics'}
              </>
            ) : (
              <>
                <Edit2 size={16} />
                Edit Topics
              </>
            )}
          </button>
        </div>

        {!editingTopics && (
          <div style={{
            padding: '16px',
            backgroundColor: '#f0f9ff',
            border: '1px solid #bae6fd',
            borderRadius: '8px',
            marginBottom: '20px',
            fontSize: '14px',
            color: '#0369a1'
          }}>
            <strong>💡 Tip:</strong> Your selected topics help personalize your chat experience. 
            The AI will tailor responses based on your interests.
          </div>
        )}

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
          gap: '12px',
          marginBottom: '20px'
        }}>
          {topicsData.available_topics.map(topic => {
            const isSelected = selectedTopics.includes(topic.id);
            const shouldShow = editingTopics || isSelected;
            
            if (!shouldShow) return null;
            
            return (
              <div
                key={topic.id}
                onClick={() => toggleTopic(topic.id)}
                style={{
                  padding: '16px',
                  border: `2px solid ${isSelected ? '#4f46e5' : '#e5e7eb'}`,
                  borderRadius: '8px',
                  cursor: editingTopics ? 'pointer' : 'default',
                  backgroundColor: isSelected ? '#e0e7ff' : 'white',
                  transition: 'all 0.2s',
                  textAlign: 'center',
                  position: 'relative'
                }}
              >
                <div style={{ fontSize: '24px', marginBottom: '4px' }}>{topic.icon}</div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: isSelected ? '500' : '400',
                  color: isSelected ? '#4f46e5' : '#6b7280'
                }}>
                  {topic.name}
                </div>
                {isSelected && !editingTopics && topic_stats.chat_counts?.[topic.id] > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: '-8px',
                    right: '-8px',
                    background: '#4f46e5',
                    color: 'white',
                    borderRadius: '12px',
                    padding: '2px 8px',
                    fontSize: '12px',
                    fontWeight: '500'
                  }}>
                    {topic_stats.chat_counts[topic.id]}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Topic Statistics */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginTop: '30px'
        }}>
          <div style={{
            padding: '20px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
              {selectedTopics.length}
            </div>
            <div style={{ fontSize: '14px', color: '#6b7280', marginTop: '4px' }}>
              Selected Topics
            </div>
          </div>
          
          <div style={{
            padding: '20px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
              {topic_stats.total_topic_chats || 0}
            </div>
            <div style={{ fontSize: '14px', color: '#6b7280', marginTop: '4px' }}>
              Topic-based Chats
            </div>
          </div>
          
          <div style={{
            padding: '20px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
              {topic_stats.most_active_topic ? 
                topicsData.available_topics.find(t => t.id === topic_stats.most_active_topic)?.icon : '—'}
            </div>
            <div style={{ fontSize: '14px', color: '#6b7280', marginTop: '4px' }}>
              Most Active Topic
            </div>
          </div>
        </div>
      </div>

      {/* Recommended Topics */}
      {topicsData.recommendations.length > 0 && (
        <div style={{ ...styles.card, marginTop: '20px' }}>
          <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '16px' }}>
            Recommended Topics
          </h3>
          <p style={{ color: '#6b7280', marginBottom: '16px' }}>
            Based on your interests, you might also enjoy:
          </p>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {topicsData.recommendations.map(topic => (
              <button
                key={topic.id}
                onClick={() => {
                  setSelectedTopics([...selectedTopics, topic.id]);
                  setEditingTopics(true);
                }}
                style={{
                  padding: '12px 20px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  backgroundColor: 'white',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={e => {
                  e.target.style.borderColor = '#4f46e5';
                  e.target.style.backgroundColor = '#f9fafb';
                }}
                onMouseLeave={e => {
                  e.target.style.borderColor = '#e5e7eb';
                  e.target.style.backgroundColor = 'white';
                }}
              >
                <span style={{ fontSize: '20px' }}>{topic.icon}</span>
                <span style={{ fontSize: '14px' }}>{topic.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default UserProfile;