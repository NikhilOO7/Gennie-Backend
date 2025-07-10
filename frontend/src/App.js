import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageCircle, 
  Send, 
  User, 
  LogOut, 
  Plus, 
  Activity, 
  Wifi, 
  WifiOff,
  Smile,
  Frown,
  Meh,
  AlertCircle,
  CheckCircle,
  Clock,
  Trash2,
  Settings,
  Moon,
  Sun,
  X,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  Brain,
  Database
} from 'lucide-react'; 

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/api/v1';

// Common styles
const styles = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
    padding: '24px'
  },
  button: {
    backgroundColor: '#4f46e5',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s'
  },
  input: {
    width: '100%',
    padding: '12px',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s'
  },
  sidebar: {
    width: '320px',
    backgroundColor: 'white',
    borderRight: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
    height: '100vh'
  },
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100vh'
  },
  message: {
    maxWidth: '70%',
    padding: '12px 16px',
    borderRadius: '12px',
    marginBottom: '8px',
    wordWrap: 'break-word'
  },
  userMessage: {
    backgroundColor: '#4f46e5',
    color: 'white',
    marginLeft: 'auto'
  },
  aiMessage: {
    backgroundColor: '#f3f4f6',
    color: '#374151',
    marginRight: 'auto'
  }
};

// Helper function to extract error message
const getErrorMessage = (error) => {
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

// Auth Context
const AuthContext = React.createContext();

// Main App Component
const App = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);

  // Add state for voice recording
  const [isRecording, setIsRecording] = useState(false);
  const [recordingMode, setRecordingMode] = useState('push'); // 'push' or 'continuous'

  // Add voice message handler
  const sendVoiceMessage = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('chat_id', activeChat.id);
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', 'en-US');
      
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/voice/voice-message`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Add messages to chat
        setMessages(prev => [...prev, 
          {
            id: data.user_message.id,
            content: data.user_message.content,
            role: 'user',
            timestamp: new Date().toISOString(),
            metadata: { type: 'voice', confidence: data.user_message.confidence }
          },
          {
            id: data.ai_message.id,
            content: data.ai_message.content,
            role: 'assistant',
            timestamp: new Date().toISOString()
          }
        ]);
        
        // Play audio response
        if (data.audio_response) {
          const audio = new Audio(`data:audio/mp3;base64,${data.audio_response}`);
          audio.play();
        }
      }
    } catch (error) {
      console.error('Voice message error:', error);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUserProfile(token);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUserProfile = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        localStorage.removeItem('access_token');
      }
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      localStorage.removeItem('access_token');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <div style={styles.card}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ animation: 'spin 1s linear infinite' }}>
                <MessageCircle size={48} color="#4f46e5" />
              </div>
              <p style={{ marginTop: '16px', color: '#6b7280' }}>Loading...</p>
            </div>
          </div>
        </div>
        
        {/* <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <ReactMediaRecorder
            audio
            onStop={(blobUrl, blob) => sendVoiceMessage(blob)}
            render={({ status, startRecording, stopRecording }) => (
              <button
                onMouseDown={() => recordingMode === 'push' && startRecording()}
                onMouseUp={() => recordingMode === 'push' && stopRecording()}
                onClick={() => {
                  if (recordingMode === 'continuous') {
                    status === 'recording' ? stopRecording() : startRecording();
                  }
                }}
                style={{
                  padding: '12px',
                  borderRadius: '50%',
                  backgroundColor: status === 'recording' ? '#ef4444' : '#4f46e5',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {status === 'recording' ? '🎤 Recording' : '🎤 Hold to Talk'}
              </button>
            )}
          />
        </div> */}

      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, setUser }}>
      <div style={styles.container}>
        {user ? <Dashboard /> : <AuthPage />}
      </div>
    </AuthContext.Provider>
  );
};

// Authentication Page
const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    first_name: '',
    last_name: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { setUser } = React.useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isLogin) {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email_or_username: formData.email,
            password: formData.password
          })
        });

        if (response.ok) {
          const data = await response.json();
          localStorage.setItem('access_token', data.access_token);
          setUser(data.user);
        } else {
          const errorData = await response.json();
          setError(getErrorMessage(errorData));
        }
      } else {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });

        if (response.ok) {
          const data = await response.json();
          localStorage.setItem('access_token', data.access_token);
          setUser(data.user);
        } else {
          const errorData = await response.json();
          setError(getErrorMessage(errorData));
        }
      }
    } catch (error) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <div style={{ ...styles.card, width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
            <MessageCircle size={48} color="#4f46e5" />
          </div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '8px' }}>
            AI Chatbot
          </h1>
          <p style={{ color: '#6b7280' }}>
            {isLogin ? 'Welcome back!' : 'Create your account'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && (
            <div style={{ 
              backgroundColor: '#fee2e2', 
              border: '1px solid #fecaca', 
              borderRadius: '8px', 
              padding: '12px', 
              marginBottom: '16px',
              color: '#dc2626'
            }}>
              {error}
            </div>
          )}

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
              Email {!isLogin && 'or Username'}
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              style={styles.input}
              required
            />
          </div>

          {!isLogin && (
            <>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
                  Username
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  style={styles.input}
                  required
                />
              </div>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
                    First Name
                  </label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    style={styles.input}
                    required
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
                    Last Name
                  </label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    style={styles.input}
                    required
                  />
                </div>
              </div>
            </>
          )}

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
              Password
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              style={styles.input}
              required
            />
          </div>

          <button 
            type="submit" 
            style={{ ...styles.button, width: '100%' }}
            disabled={loading}
          >
            {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>

          <div style={{ textAlign: 'center', marginTop: '16px' }}>
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              style={{
                background: 'none',
                border: 'none',
                color: '#4f46e5',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Main Dashboard
const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [darkMode, setDarkMode] = useState(localStorage.getItem('darkMode') === 'true');
  const [showSettings, setShowSettings] = useState(false);
  const { user, setUser } = React.useContext(AuthContext);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    fetchChats();
    fetchHealthStatus();
  }, []);

  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  const sendVoiceMessage = async (audioBlob) => {
    if (!activeChat) return;
    
    try {
      const formData = new FormData();
      formData.append('chat_id', activeChat.id);
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', 'en-US');
      
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/voice/transcribe`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        
        // Add transcribed message to chat
        setMessages(prev => [
          ...prev,
          {
            id: Date.now(),
            content: data.transcription,
            sender_type: 'user',
            created_at: new Date().toISOString(),
            is_voice: true
          },
          {
            id: data.message_id || Date.now() + 1,
            content: data.response,
            sender_type: 'assistant',
            created_at: data.timestamp || new Date().toISOString(),
            emotion_detected: data.emotion_analysis?.primary_emotion,
            tokens_used: data.token_usage?.total_tokens
          }
        ]);
      }
    } catch (error) {
      console.error('Voice message failed:', error);
    }
  };

  const fetchChats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setChats(data.chats || data || []);
      }
    } catch (error) {
      console.error('Failed to fetch chats:', error);
    }
  };

  const fetchHealthStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (response.ok) {
        const data = await response.json();
        setHealthStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch health status:', error);
    }
  };

  const createNewChat = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          title: `Chat ${chats.length + 1}`,
          description: 'New conversation'
        })
      });

      if (response.ok) {
        const newChat = await response.json();
        setChats([newChat, ...chats]);
        setActiveChat(newChat);
        setActiveTab('chat');
      }
    } catch (error) {
      console.error('Failed to create chat:', error);
    }
  };

  const deleteChat = async (chatId, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this chat?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat/${chatId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        setChats(chats.filter(chat => chat.id !== chatId));
        if (activeChat?.id === chatId) {
          setActiveChat(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatInterface activeChat={activeChat} setActiveChat={setActiveChat} chats={chats} setChats={setChats} />;
      case 'health':
        return <HealthDashboard healthStatus={healthStatus} onRefresh={fetchHealthStatus} />;
      case 'profile':
        return <UserProfile user={user} />;
      default:
        return <ChatInterface activeChat={activeChat} setActiveChat={setActiveChat} chats={chats} setChats={setChats} />;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: darkMode ? '#1f2937' : '#f3f4f6' }}>
      {/* Sidebar */}
      <div style={{ ...styles.sidebar, backgroundColor: darkMode ? '#111827' : 'white' }}>
        {/* Header */}
        <div style={{ padding: '20px', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ 
                width: '40px', 
                height: '40px', 
                borderRadius: '50%', 
                backgroundColor: '#e0e7ff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <User size={20} color="#4338ca" />
              </div>
              <div>
                <p style={{ fontWeight: '600', color: darkMode ? '#f3f4f6' : '#111827' }}>
                  AI Chatbot
                </p>
                <p style={{ fontSize: '12px', color: '#6b7280' }}>
                  Welcome, {user?.first_name}
                </p>
              </div>
            </div>
            <button
              onClick={logout}
              style={{ 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer',
                color: '#6b7280'
              }}
              title="Logout"
            >
              <LogOut size={20} />
            </button>
          </div>
          <button 
            onClick={createNewChat}
            style={{ ...styles.button, width: '100%', marginTop: '16px' }}
          >
            <Plus size={16} style={{ marginRight: '8px', display: 'inline' }} />
            New Chat
          </button>
        </div>

        {/* Navigation */}
        <div style={{ padding: '8px' }}>
          <div style={{ marginBottom: '16px' }}>
            {[
              { id: 'chat', label: 'Chat', icon: MessageCircle },
              { id: 'health', label: 'Health Status', icon: Activity },
              { id: 'profile', label: 'Profile', icon: User }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: activeTab === tab.id ? '#e0e7ff' : 'transparent',
                  color: activeTab === tab.id ? '#4338ca' : darkMode ? '#d1d5db' : '#6b7280',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                  transition: 'all 0.2s',
                  width: '100%',
                  textAlign: 'left'
                }}
              >
                <tab.icon size={20} />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chat List */}
        {activeTab === 'chat' && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
            <p style={{ 
              fontSize: '12px', 
              fontWeight: '600', 
              color: '#6b7280', 
              padding: '8px',
              textTransform: 'uppercase'
            }}>
              Recent Chats
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => setActiveChat(chat)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px',
                    borderRadius: '8px',
                    border: activeChat?.id === chat.id ? '2px solid #c7d2fe' : '1px solid #e5e7eb',
                    backgroundColor: activeChat?.id === chat.id ? '#e0e7ff' : darkMode ? '#374151' : '#f9fafb',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <p style={{ 
                      fontWeight: '500', 
                      fontSize: '14px',
                      color: darkMode ? '#f3f4f6' : '#111827'
                    }}>
                      {chat.title}
                    </p>
                    <p style={{ fontSize: '12px', color: '#6b7280' }}>
                      {new Date(chat.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={(e) => deleteChat(chat.id, e)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#6b7280',
                      padding: '4px'
                    }}
                    title="Delete chat"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bottom Actions */}
        <div style={{ padding: '16px', borderTop: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
            <button
              onClick={() => setShowSettings(true)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#6b7280',
                padding: '8px'
              }}
              title="Settings"
            >
              <Settings size={20} />
            </button>
            <button
              onClick={() => setDarkMode(!darkMode)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#6b7280',
                padding: '8px'
              }}
              title="Toggle theme"
            >
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={styles.mainContent}>
        {renderTabContent()}
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal
          user={user}
          onClose={() => setShowSettings(false)}
          darkMode={darkMode}
        />
      )}
    </div>
  );
};

// Chat Interface Component
const ChatInterface = ({ activeChat, setActiveChat, chats, setChats }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isAiTyping, setIsAiTyping] = useState(false);
  const [emotionAnalysis, setEmotionAnalysis] = useState(null);
  const [showRAGVisualization, setShowRAGVisualization] = useState(false);
  const [selectedMessageId, setSelectedMessageId] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (activeChat) {
      fetchMessages(activeChat.id);
      connectWebSocket(activeChat.id);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [activeChat]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const playNotificationSound = () => {
    if (soundEnabled) {
      const audio = new Audio('/notification.mp3');
      audio.play().catch(e => console.log('Could not play sound:', e));
    }
  };

  const fetchMessages = async (chatId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat/${chatId}/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || data || []);
      }
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  };

  const connectWebSocket = (chatId) => {
    const token = localStorage.getItem('access_token');
    const wsUrl = `${WS_BASE_URL}/ws/chat/${chatId}?token=${token}`;
    
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);
      
      switch (data.type) {
        case 'connected':
          console.log('Connection confirmed');
          break;
          
        case 'message_sent':
          setMessages(prev => [...prev, {
            id: data.message_id,
            content: data.content,
            sender_type: 'user',
            created_at: data.timestamp
          }]);
          break;
          
        case 'user_message':
          setMessages(prev => [...prev, {
            id: data.message_id,
            content: data.content,
            sender_type: 'user',
            created_at: data.timestamp,
            user_id: data.user_id
          }]);
          break;
          
        case 'ai_typing':
          setIsAiTyping(data.is_typing);
          break;
          
        case 'ai_message':
          setIsAiTyping(false);
          setMessages(prev => [...prev, {
            id: data.message_id,
            content: data.content,
            sender_type: 'assistant',
            created_at: data.timestamp,
            emotion_detected: data.emotion_detected,
            tokens_used: data.tokens_used,
            message_metadata: data.message_metadata
          }]);
          
          if (data.emotion_detected) {
            setEmotionAnalysis({
              emotion: data.emotion_detected,
              confidence: data.confidence_score || 0.95
            });
          }
          playNotificationSound();
          break;
          
        case 'error':
          console.error('WebSocket error:', data.error);
          setIsAiTyping(false);
          break;
          
        default:
          console.log('Unknown message type:', data.type);
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      setIsAiTyping(false);
      console.log('WebSocket disconnected');
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
      setIsAiTyping(false);
    };
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !activeChat) return;

    const messageContent = newMessage.trim();
    setNewMessage('');

    try {
      if (wsRef.current && isConnected && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'chat_message',
          content: messageContent
        }));
      } else {
        // Fallback to REST API
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}/ai/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            message: messageContent,
            chat_id: activeChat.id,
            detect_emotion: true,
            enable_personalization: true,
            use_context: true
          })
        });

        if (response.ok) {
          const data = await response.json();
          setMessages(prev => [
            ...prev,
            {
              id: Date.now(),
              content: messageContent,
              sender_type: 'user',
              created_at: new Date().toISOString()
            },
            {
              id: data.message_id || Date.now() + 1,
              content: data.response || data.content,
              sender_type: 'assistant',
              created_at: data.timestamp || new Date().toISOString(),
              emotion_detected: data.emotion_analysis?.primary_emotion,
              tokens_used: data.token_usage?.total_tokens,
              message_metadata: data.metadata
            }
          ]);
          
          if (data.emotion_analysis) {
            setEmotionAnalysis({
              emotion: data.emotion_analysis.primary_emotion,
              confidence: data.emotion_analysis.confidence || 0.95
            });
          }
          playNotificationSound();
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const toggleVoiceRecording = () => {
    setIsRecording(!isRecording);
    // Voice recording implementation would go here
  };

  const showRAGContext = (messageId) => {
    setSelectedMessageId(messageId);
    setShowRAGVisualization(true);
  };

  const getEmotionIcon = (emotion) => {
    switch (emotion?.toLowerCase()) {
      case 'positive':
      case 'joy':
      case 'happy':
      case 'excitement':
        return <Smile size={16} color="#10b981" />;
      case 'negative':
      case 'sad':
      case 'angry':
      case 'fear':
        return <Frown size={16} color="#ef4444" />;
      default:
        return <Meh size={16} color="#f59e0b" />;
    }
  };

  if (!activeChat) {
    return (
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        backgroundColor: '#f9fafb'
      }}>
        <div style={{ textAlign: 'center' }}>
          <MessageCircle size={64} color="#e5e7eb" />
          <h3 style={{ marginTop: '16px', color: '#6b7280' }}>
            No Chat Selected
          </h3>
          <p style={{ marginTop: '8px', color: '#9ca3af' }}>
            Choose a chat from the sidebar or create a new one
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Chat Header */}
      <div style={{ 
        padding: '16px 24px', 
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: 'white'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '4px' }}>
              {activeChat.title}
            </h3>
            <p style={{ fontSize: '14px', color: '#6b7280' }}>
              {activeChat.description}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {emotionAnalysis && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '4px',
                padding: '6px 12px',
                backgroundColor: '#f3f4f6',
                borderRadius: '16px'
              }}>
                {getEmotionIcon(emotionAnalysis.emotion)}
                <span style={{ fontSize: '12px', color: '#6b7280' }}>
                  {emotionAnalysis.emotion} ({Math.round(emotionAnalysis.confidence * 100)}%)
                </span>
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {isConnected ? (
                <Wifi size={16} color="#10b981" />
              ) : (
                <WifiOff size={16} color="#ef4444" />
              )}
              <span style={{ fontSize: '12px', color: '#6b7280' }}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <button
              onClick={() => setShowRAGVisualization(!showRAGVisualization)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#6b7280',
                padding: '8px'
              }}
              title="Toggle RAG Visualization"
            >
              <Brain size={20} />
            </button>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#6b7280',
                padding: '8px'
              }}
              title="Toggle sound"
            >
              {soundEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '24px',
        backgroundColor: '#f9fafb'
      }}>
        {messages.map((message, index) => (
          <div
            key={message.id}
            style={{
              marginBottom: '16px',
              display: 'flex',
              justifyContent: message.sender_type === 'user' ? 'flex-end' : 'flex-start',
              animation: 'fadeIn 0.3s ease-in'
            }}
          >
            <div style={{
              ...styles.message,
              ...(message.sender_type === 'user' ? styles.userMessage : styles.aiMessage),
              position: 'relative'
            }}>
              <p style={{ margin: 0 }}>{message.content}</p>
              <div style={{ 
                marginTop: '8px', 
                fontSize: '12px', 
                opacity: 0.7,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span>
                  {new Date(message.created_at).toLocaleTimeString()}
                </span>
                {message.emotion_detected && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {getEmotionIcon(message.emotion_detected)}
                    {message.emotion_detected}
                  </div>
                )}
                {message.tokens_used && (
                  <span>{message.tokens_used} tokens</span>
                )}
                {message.message_metadata?.rag_context_used && (
                  <button
                    onClick={() => showRAGContext(message.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'inherit',
                      padding: '2px'
                    }}
                    title="View RAG Context"
                  >
                    <Activity size={14} />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {isAiTyping && (
          <div style={{ 
            marginBottom: '16px',
            display: 'flex',
            justifyContent: 'flex-start'
          }}>
            <div style={{ ...styles.message, ...styles.aiMessage }}>
              <p style={{ margin: 0 }}>AI is typing...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <div style={{ 
        padding: '16px 24px', 
        borderTop: '1px solid #e5e7eb',
        backgroundColor: 'white'
      }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Type your message..."
            style={{...styles.input, margin: 0}}
            disabled={isAiTyping}
          />
          <button
            onClick={toggleVoiceRecording}
            style={{
              ...styles.button,
              padding: '12px',
              backgroundColor: isRecording ? '#ef4444' : '#4f46e5'
            }}
            title={isRecording ? 'Stop recording' : 'Start recording'}
          >
            {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
          <button 
            onClick={sendMessage}
            style={{ ...styles.button, padding: '12px' }}
            disabled={!newMessage.trim() || isAiTyping}
          >
            <Send size={20} />
          </button>
        </div>
      </div>

      {/* RAG Visualization Modal */}
      {showRAGVisualization && selectedMessageId && (
        <RAGVisualization
          messageId={selectedMessageId}
          onClose={() => setShowRAGVisualization(false)}
        />
      )}
    </div>
  );
};

// RAG Visualization Component
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
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/ai/rag-context/${messageId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setRagData(data);
      }
    } catch (error) {
      console.error('Failed to fetch RAG context:', error);
    } finally {
      setLoading(false);
    }
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
              {activeTab === 'overview' && ragData && (
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

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                    {ragData.ragStats && Object.entries({
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
                </div>
              )}

              {activeTab === 'context' && ragData && (
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                    Retrieved Context Messages
                  </h3>
                  <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
                    These messages were selected based on semantic similarity to your current query
                  </p>
                  {ragData.contextMessages?.length > 0 ? (
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
              )}

              {activeTab === 'preferences' && ragData && (
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

                      {ragData.emotionalPattern.history && (
                        <div>
                          <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
                            7-Day Emotional Trend
                          </p>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', height: '100px' }}>
                            {ragData.emotionalPattern.history.map((day, i) => (
                              <div key={i} style={{ flex: 1, position: 'relative' }}>
                                <div style={{
                                  position: 'absolute',
                                  bottom: 0,
                                  width: '100%',
                                  backgroundColor: '#4f46e5',
                                  borderRadius: '4px 4px 0 0',
                                  height: `${day.score * 100}%`,
                                  minHeight: '4px'
                                }} title={`Score: ${day.score.toFixed(2)}`} />
                                <span style={{
                                  position: 'absolute',
                                  bottom: '-20px',
                                  fontSize: '10px',
                                  color: '#6b7280',
                                  width: '100%',
                                  textAlign: 'center'
                                }}>
                                  {day.date}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Settings Modal Component
const SettingsModal = ({ user, onClose, darkMode }) => {
  const [preferences, setPreferences] = useState({
    conversation_style: 'friendly',
    response_length: 'medium',
    emotional_support_level: 'standard'  // Changed from 'emotional_support'
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/ai/personalization`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        if (data.preferences && Object.keys(data.preferences).length > 0) {
          // Map backend preferences to frontend state
          setPreferences({
            conversation_style: data.preferences.conversation_style || 'friendly',
            response_length: data.preferences.preferred_response_length || 'medium',
            emotional_support_level: data.preferences.emotional_support_level || 'standard'
          });
        }
      }
    } catch (error) {
      console.error('Failed to fetch preferences:', error);
    }
  };

  const savePreferences = async () => {
    setLoading(true);
    setMessage('');
    
    try {
      const token = localStorage.getItem('access_token');
      
      // Send preferences with correct field names
      const response = await fetch(`${API_BASE_URL}/ai/personalization`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(preferences)  // Send the preferences object directly
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Preferences saved:', data);
        setMessage('Preferences saved successfully!');
        // Close modal after a short delay
        setTimeout(() => {
          onClose();
        }, 1500);
      } else {
        const error = await response.json();
        console.error('Failed to save preferences:', error);
        setMessage('Failed to save preferences. Please try again.');
      }
    } catch (error) {
      console.error('Failed to save preferences:', error);
      setMessage('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Settings</h2>
        
        <div className="preference-section">
          <label>Conversation Style</label>
          <select
            value={preferences.conversation_style}
            onChange={(e) => setPreferences({...preferences, conversation_style: e.target.value})}
            disabled={loading}
          >
            <option value="friendly">Friendly</option>
            <option value="formal">Formal</option>
            <option value="casual">Casual</option>
            <option value="professional">Professional</option>
          </select>
        </div>

        <div className="preference-section">
          <label>Response Length</label>
          <select
            value={preferences.response_length}
            onChange={(e) => setPreferences({...preferences, response_length: e.target.value})}
            disabled={loading}
          >
            <option value="short">Short</option>
            <option value="medium">Medium</option>
            <option value="long">Long</option>
          </select>
        </div>

        <div className="preference-section">
          <label>Emotional Support Level</label>
          <select
            value={preferences.emotional_support_level}
            onChange={(e) => setPreferences({...preferences, emotional_support_level: e.target.value})}
            disabled={loading}
          >
            <option value="minimal">Minimal</option>
            <option value="standard">Standard</option>
            <option value="high">High</option>
          </select>
        </div>

        {message && (
          <div className={`message ${message.includes('success') ? 'success' : 'error'}`}>
            {message}
          </div>
        )}

        <div className="modal-actions">
          <button onClick={onClose} disabled={loading}>Cancel</button>
          <button onClick={savePreferences} disabled={loading}>
            {loading ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Health Dashboard Component
const HealthDashboard = ({ healthStatus, onRefresh }) => {
  const getStatusColor = (status) => {
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

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle size={20} color="#10b981" />;
      case 'degraded':
        return <AlertCircle size={20} color="#f59e0b" />;
      case 'unhealthy':
        return <AlertCircle size={20} color="#ef4444" />;
      default:
        return <Clock size={20} color="#6b7280" />;
    }
  };

  return (
    <div style={{ padding: '24px', backgroundColor: '#f9fafb', height: '100%', overflowY: 'auto' }}>
      <div style={{ ...styles.card, marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600' }}>System Health</h2>
          <button onClick={onRefresh} style={styles.button}>
            Refresh
          </button>
        </div>

        {healthStatus ? (
          <div>
            {/* Overall Status */}
            <div style={{ marginBottom: '32px' }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px',
                padding: '16px',
                backgroundColor: '#f3f4f6',
                borderRadius: '8px',
                marginBottom: '16px'
              }}>
                <div>
                  {getStatusIcon(healthStatus.status)}
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Overall Status</h3>
                  <p style={{ 
                    color: getStatusColor(healthStatus.status), 
                    textTransform: 'capitalize',
                    fontWeight: '500'
                  }}>
                    {healthStatus.status}
                  </p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                    {healthStatus.version}
                  </p>
                  <p style={{ fontSize: '12px', color: '#6b7280' }}>Version</p>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                    {healthStatus.environment}
                  </p>
                  <p style={{ fontSize: '12px', color: '#6b7280' }}>Environment</p>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                    {Math.round(healthStatus.response_time_seconds * 1000)}ms
                  </p>
                  <p style={{ fontSize: '12px', color: '#6b7280' }}>Response Time</p>
                </div>
              </div>
            </div>

            {/* Service Checks */}
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
                Service Status
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {Object.entries(healthStatus.checks).map(([service, check]) => (
                  <div
                    key={service}
                    style={{
                      padding: '16px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '8px',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: '500', textTransform: 'capitalize' }}>
                        {service.replace('_', ' ')}
                      </h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {getStatusIcon(check.status)}
                        <span style={{ color: getStatusColor(check.status), fontWeight: '500' }}>
                          {check.status}
                        </span>
                      </div>
                    </div>
                    {check.response_time_ms && (
                      <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                        Response time: {Math.round(check.response_time_ms)}ms
                      </p>
                    )}
                    {check.error && (
                      <p style={{ fontSize: '12px', color: '#ef4444', marginTop: '4px' }}>
                        Error: {getErrorMessage(check.error)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Activity size={48} color="#e5e7eb" />
            <h3 style={{ marginTop: '16px', color: '#6b7280' }}>
              Loading Health Status
            </h3>
            <p style={{ marginTop: '8px', color: '#9ca3af' }}>
              Fetching system health information...
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// User Profile Component
const UserProfile = ({ user }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchUserStats();
  }, []);

  const fetchUserStats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/users/me/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
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

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  body.dark-mode {
    background-color: #111827;
    color: #f3f4f6;
  }
  
  * {
    box-sizing: border-box;
  }
  
  /* Scrollbar styling */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  
  ::-webkit-scrollbar-track {
    background: #f3f4f6;
  }
  
  ::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 4px;
  }
  
  ::-webkit-scrollbar-thumb:hover {
    background: #9ca3af;
  }
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
  }

  .modal-content {
    background: white;
    border-radius: 8px;
    padding: 24px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  }

  .dark-mode .modal-content {
    background: #2d2d2d;
    color: #e0e0e0;
  }

  .modal-content h2 {
    margin-top: 0;
    margin-bottom: 20px;
    color: #333;
  }

  .dark-mode .modal-content h2 {
    color: #e0e0e0;
  }

  .preference-section {
    margin-bottom: 20px;
  }

  .preference-section label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #555;
  }

  .dark-mode .preference-section label {
    color: #b0b0b0;
  }

  .preference-section select {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    background: white;
    color: #333;
    cursor: pointer;
  }

  .dark-mode .preference-section select {
    background: #3d3d3d;
    border-color: #555;
    color: #e0e0e0;
  }

  .preference-section select:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .message {
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 20px;
    text-align: center;
    font-size: 14px;
  }

  .message.success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
  }

  .message.error {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
  }

  .dark-mode .message.success {
    background-color: #1e4620;
    color: #90ee90;
    border-color: #2e5f30;
  }

  .dark-mode .message.error {
    background-color: #5a1e1e;
    color: #ff6b6b;
    border-color: #7a2e2e;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
  }

  .modal-actions button {
    padding: 8px 20px;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .modal-actions button:first-child {
    background: #e0e0e0;
    color: #333;
  }

  .modal-actions button:first-child:hover {
    background: #d0d0d0;
  }

  .modal-actions button:last-child {
    background: #007bff;
    color: white;
  }

  .modal-actions button:last-child:hover {
    background: #0056b3;
  }

  .modal-actions button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .dark-mode .modal-actions button:first-child {
    background: #4a4a4a;
    color: #e0e0e0;
  }

  .dark-mode .modal-actions button:first-child:hover {
    background: #5a5a5a;
  }
`;
document.head.appendChild(style);

export default App;