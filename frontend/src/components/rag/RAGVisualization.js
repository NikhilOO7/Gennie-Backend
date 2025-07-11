import React, { useState, useEffect } from 'react';
import { X, MessageCircle, Database, Brain } from 'lucide-react';
import apiService from '../../services/api';
import { styles } from '../../utils/styles';

const RAGVisualization = ({ messageId, onClose }) => {
  const [ragData, setRagData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchRAGContext();
  }, [messageId]);

  const fetchRAGContext = async () => {
    try {
      setLoading(true);
      const data = await apiService.getRAGContext(messageId);
      setRagData(data);
    } catch (error) {
      console.error('Failed to fetch RAG context:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderOverviewTab = () => {
    if (!ragData) return null;

    return (
      <div>
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
            Current Query
          </h3>
          <p style={{ padding: '12px', backgroundColor: '#f3f4f6', borderRadius: '8px' }}>
            {ragData.currentMessage}
          </p>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
            How RAG Works
          </h3>
          <div style={{ display: 'flex', gap: '16px', justifyContent: 'space-around' }}>
            {[
              { icon: MessageCircle, title: 'Message Input', desc: 'Your message is processed and converted to embeddings' },
              { icon: Database, title: 'Vector Search', desc: 'Similar messages are found in conversation history' },
              { icon: Brain, title: 'Context Building', desc: 'Relevant context is provided to the AI model' }
            ].map((step, index) => (
              <div key={index} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{
                  width: '60px',
                  height: '60px',
                  borderRadius: '50%',
                  backgroundColor: '#e0e7ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 12px'
                }}>
                  <step.icon size={28} color="#4338ca" />
                </div>
                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                  {index + 1}. {step.title}
                </h4>
                <p style={{ fontSize: '12px', color: '#6b7280' }}>
                  {step.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {ragData.ragStats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
            {Object.entries({
              'Context Window': `${ragData.ragStats.contextWindowSize} messages`,
              'Embeddings': `${ragData.ragStats.embeddingDimensions} dimensions`,
              'Retrieved': `${ragData.ragStats.contextsRetrieved} contexts`,
              'Similarity Threshold': ragData.ragStats.similarityThreshold
            }).map(([label, value]) => (
              <div key={label} style={{
                padding: '16px',
                backgroundColor: '#f3f4f6',
                borderRadius: '8px'
              }}>
                <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                  {label}
                </p>
                <p style={{ fontSize: '20px', fontWeight: '600' }}>
                  {value}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderContextTab = () => {
    if (!ragData || !ragData.contextMessages) return null;

    return (
      <div>
        <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
          Retrieved Context Messages
        </h3>
        <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
          These messages were selected based on semantic similarity to your current query
        </p>
        
        {ragData.contextMessages.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {ragData.contextMessages.map((msg, idx) => (
              <div key={idx} style={{
                padding: '16px',
                backgroundColor: '#f3f4f6',
                borderRadius: '8px'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: '600',
                    color: msg.sender_type === 'user' ? '#4f46e5' : '#10b981'
                  }}>
                    {msg.sender_type}
                  </span>
                  <span style={{ fontSize: '12px', color: '#6b7280' }}>
                    {msg.relevanceScore 
                      ? `${(msg.relevanceScore * 100).toFixed(0)}% relevant` 
                      : 'Recent message'}
                  </span>
                </div>
                <p style={{ marginBottom: '8px' }}>{msg.content}</p>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>
                  <span>{new Date(msg.timestamp).toLocaleString()}</span>
                  {msg.emotion && <span> • Emotion: {msg.emotion}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{
            padding: '40px',
            textAlign: 'center',
            color: '#6b7280'
          }}>
            <p>No previous context was used for this message</p>
          </div>
        )}
      </div>
    );
  };

  const renderPreferencesTab = () => {
    if (!ragData) return null;

    return (
      <div>
        <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
          User Preferences
        </h3>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '24px' }}>
          {Object.entries({
            'Conversation Style': ragData.userPreferences?.conversationStyle || 'Not set',
            'Response Length': ragData.userPreferences?.responseLength || 'Not set',
            'Active Time': ragData.userPreferences?.preferredTime || 'Not set',
            'Interests': ragData.userPreferences?.interests?.join(', ') || 'None identified'
          }).map(([label, value]) => (
            <div key={label}>
              <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                {label}
              </p>
              <p style={{ fontSize: '14px', fontWeight: '500' }}>
                {value}
              </p>
            </div>
          ))}
        </div>

        {ragData.emotionalPattern && (
          <>
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
              Emotional Pattern
            </h3>
            <div style={{ display: 'flex', gap: '24px', marginBottom: '16px' }}>
              <div>
                <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                  Recent Emotion
                </p>
                <p style={{ fontSize: '14px', fontWeight: '500' }}>
                  {ragData.emotionalPattern.recent || 'Neutral'}
                </p>
              </div>
              <div>
                <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                  Trend
                </p>
                <p style={{
                  fontSize: '14px',
                  fontWeight: '500',
                  color: ragData.emotionalPattern.trend === 'improving' ? '#10b981' :
                         ragData.emotionalPattern.trend === 'declining' ? '#ef4444' : '#f59e0b'
                }}>
                  {ragData.emotionalPattern.trend || 'Stable'}
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    }}>
      <div style={{
        ...styles.card,
        width: '90%',
        maxWidth: '800px',
        maxHeight: '80vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px'
        }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600' }}>
            RAG System Visualization
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#6b7280'
            }}
          >
            <X size={24} />
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{ animation: 'spin 1s linear infinite' }}>
              <Brain size={48} color="#4f46e5" />
            </div>
            <p style={{ marginTop: '16px', color: '#6b7280' }}>
              Loading RAG context...
            </p>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
              {['overview', 'context', 'preferences'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '8px',
                    backgroundColor: activeTab === tab ? '#4f46e5' : '#f3f4f6',
                    color: activeTab === tab ? 'white' : '#6b7280',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: '500',
                    textTransform: 'capitalize'
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {activeTab === 'overview' && renderOverviewTab()}
              {activeTab === 'context' && renderContextTab()}
              {activeTab === 'preferences' && renderPreferencesTab()}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default RAGVisualization;