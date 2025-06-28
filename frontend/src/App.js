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
  Clock
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000/api/v1';
const WS_BASE_URL = 'ws://localhost:8000/api/v1';

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
    // Handle FastAPI validation errors
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
      <div style={{...styles.container, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center', color: 'white'}}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid rgba(255,255,255,0.3)',
            borderTop: '3px solid white',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }}></div>
          <p>Loading...</p>
        </div>
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

  const handleSubmit = async () => {
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
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{...styles.card, width: '100%', maxWidth: '400px'}}>
        <div style={{textAlign: 'center', marginBottom: '32px'}}>
          <div style={{
            backgroundColor: '#e0e7ff',
            borderRadius: '50%',
            width: '64px',
            height: '64px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <MessageCircle size={32} color="#4f46e5" />
          </div>
          <h1 style={{fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: '0 0 8px'}}>
            AI Chatbot
          </h1>
          <p style={{color: '#6b7280', margin: 0}}>
            {isLogin ? 'Welcome back!' : 'Create your account'}
          </p>
        </div>

        <div style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
          {error && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              padding: '12px',
              color: '#b91c1c',
              fontSize: '14px'
            }}>
              {error}
            </div>
          )}

          <div>
            <label style={{display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px'}}>
              Email {!isLogin && 'or Username'}
            </label>
            <input
              type="text"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              style={styles.input}
              required
            />
          </div>

          {!isLogin && (
            <>
              <div>
                <label style={{display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px'}}>
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
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px'}}>
                <div>
                  <label style={{display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px'}}>
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
                <div>
                  <label style={{display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px'}}>
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

          <div>
            <label style={{display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '4px'}}>
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
            onClick={handleSubmit}
            disabled={loading}
            style={{
              ...styles.button,
              width: '100%',
              opacity: loading ? 0.5 : 1,
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>

          <div style={{textAlign: 'center'}}>
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
        </div>
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
  const { user, setUser } = React.useContext(AuthContext);

  useEffect(() => {
    fetchChats();
    fetchHealthStatus();
  }, []);

  const fetchChats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setChats(data.chats || []);
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
    <div style={{display: 'flex', height: '100vh'}}>
      {/* Sidebar */}
      <div style={styles.sidebar}>
        {/* Header */}
        <div style={{padding: '16px', borderBottom: '1px solid #e5e7eb'}}>
          <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
              <div style={{
                backgroundColor: '#e0e7ff',
                borderRadius: '50%',
                padding: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <MessageCircle size={24} color="#4f46e5" />
              </div>
              <div>
                <h1 style={{fontWeight: '600', color: '#111827', margin: 0, fontSize: '16px'}}>AI Chatbot</h1>
                <p style={{fontSize: '14px', color: '#6b7280', margin: 0}}>Welcome, {user?.first_name}</p>
              </div>
            </div>
            <button
              onClick={logout}
              style={{
                background: 'none',
                border: 'none',
                color: '#9ca3af',
                cursor: 'pointer',
                padding: '4px'
              }}
            >
              <LogOut size={20} />
            </button>
          </div>

          <button
            onClick={createNewChat}
            style={{
              ...styles.button,
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Navigation */}
        <div style={{padding: '16px'}}>
          <nav style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
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
                  color: activeTab === tab.id ? '#4338ca' : '#6b7280',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                  transition: 'all 0.2s'
                }}
              >
                <tab.icon size={20} />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Chat List */}
        {activeTab === 'chat' && (
          <div style={{flex: 1, overflowY: 'auto', padding: '16px'}}>
            <h3 style={{fontSize: '14px', fontWeight: '500', color: '#111827', marginBottom: '12px'}}>Recent Chats</h3>
            <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
              {chats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => setActiveChat(chat)}
                  style={{
                    textAlign: 'left',
                    padding: '12px',
                    borderRadius: '8px',
                    border: activeChat?.id === chat.id ? '2px solid #c7d2fe' : '1px solid #e5e7eb',
                    backgroundColor: activeChat?.id === chat.id ? '#e0e7ff' : '#f9fafb',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{fontWeight: '500', color: '#111827', fontSize: '14px', marginBottom: '4px'}}>
                    {chat.title}
                  </div>
                  <div style={{fontSize: '12px', color: '#6b7280', marginBottom: '4px'}}>
                    {chat.description}
                  </div>
                  <div style={{fontSize: '11px', color: '#9ca3af'}}>
                    {new Date(chat.created_at).toLocaleDateString()}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div style={styles.mainContent}>
        {renderTabContent()}
      </div>
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

  const fetchMessages = async (chatId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat/${chatId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
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
          // Add the user message when server confirms it was sent
          setMessages(prev => [...prev, {
            id: data.message_id,
            content: data.content,
            sender_type: 'user',
            created_at: data.timestamp
          }]);
          break;
          
        case 'user_message':
          // Another user's message (for multi-user chats)
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
          // Add the AI response
          setMessages(prev => [...prev, {
            id: data.message_id,
            content: data.content,
            sender_type: 'assistant',
            created_at: data.timestamp,
            emotion_detected: data.emotion_detected,
            tokens_used: data.tokens_used
          }]);
          
          if (data.emotion_detected) {
            setEmotionAnalysis({
              emotion: data.emotion_detected,
              confidence: 0.95 // Default confidence if not provided
            });
          }
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
      // Send via WebSocket if connected
      if (wsRef.current && isConnected && wsRef.current.readyState === WebSocket.OPEN) {
        // FIXED: Send message in correct format
        wsRef.current.send(JSON.stringify({
          type: 'chat_message',
          content: messageContent  // Send content directly, not wrapped in data
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
            enable_personalization: true
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
              emotion_detected: data.emotion_detected,
              tokens_used: data.token_usage?.total_tokens
            }
          ]);
          
          if (data.emotion_detected) {
            setEmotionAnalysis({
              emotion: data.emotion_detected,
              confidence: data.confidence_score || 0.95
            });
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const getEmotionIcon = (emotion) => {
    switch (emotion?.toLowerCase()) {
      case 'positive':
      case 'joy':
      case 'happy':
        return <Smile size={16} color="#10b981" />;
      case 'negative':
      case 'sad':
      case 'angry':
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
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f9fafb'
      }}>
        <div style={{textAlign: 'center'}}>
          <MessageCircle size={64} color="#9ca3af" style={{margin: '0 auto 16px'}} />
          <h3 style={{fontSize: '18px', fontWeight: '500', color: '#111827', marginBottom: '8px'}}>
            No Chat Selected
          </h3>
          <p style={{color: '#6b7280', margin: 0}}>
            Choose a chat from the sidebar or create a new one
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{flex: 1, display: 'flex', flexDirection: 'column'}}>
      {/* Chat Header */}
      <div style={{
        backgroundColor: 'white',
        borderBottom: '1px solid #e5e7eb',
        padding: '16px'
      }}>
        <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
          <div>
            <h2 style={{fontSize: '18px', fontWeight: '600', color: '#111827', margin: '0 0 4px'}}>
              {activeChat.title}
            </h2>
            <p style={{fontSize: '14px', color: '#6b7280', margin: 0}}>
              {activeChat.description}
            </p>
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: '16px'}}>
            {emotionAnalysis && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: '#f3f4f6',
                padding: '4px 12px',
                borderRadius: '20px'
              }}>
                {getEmotionIcon(emotionAnalysis.emotion)}
                <span style={{fontSize: '14px', color: '#374151'}}>
                  {emotionAnalysis.emotion} ({Math.round(emotionAnalysis.confidence * 100)}%)
                </span>
              </div>
            )}
            <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
              {isConnected ? (
                <Wifi size={20} color="#10b981" />
              ) : (
                <WifiOff size={20} color="#ef4444" />
              )}
              <span style={{fontSize: '14px', color: '#6b7280'}}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        {messages.map((message, index) => (
          <div
            key={message.id || index}
            style={{
              display: 'flex',
              justifyContent: message.sender_type === 'user' ? 'flex-end' : 'flex-start'
            }}
          >
            <div
              style={{
                ...styles.message,
                ...(message.sender_type === 'user' ? styles.userMessage : styles.aiMessage)
              }}
            >
              <p style={{margin: '0 0 8px', whiteSpace: 'pre-wrap'}}>{message.content}</p>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '12px',
                opacity: 0.75
              }}>
                <span>
                  {new Date(message.created_at).toLocaleTimeString()}
                </span>
                {message.emotion_detected && (
                  <div style={{display: 'flex', alignItems: 'center', gap: '4px'}}>
                    {getEmotionIcon(message.emotion_detected)}
                    <span>{message.emotion_detected}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {isAiTyping && (
          <div style={{display: 'flex', justifyContent: 'flex-start'}}>
            <div style={{...styles.message, ...styles.aiMessage}}>
              <p style={{margin: 0}}>AI is typing...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <div style={{
        backgroundColor: 'white',
        borderTop: '1px solid #e5e7eb',
        padding: '16px'
      }}>
        <div style={{display: 'flex', gap: '12px'}}>
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
          />
          <button
            onClick={sendMessage}
            disabled={!newMessage.trim() || !isConnected}
            style={{
              ...styles.button,
              padding: '12px',
              opacity: (!newMessage.trim() || !isConnected) ? 0.5 : 1,
              cursor: (!newMessage.trim() || !isConnected) ? 'not-allowed' : 'pointer'
            }}
          >
            <Send size={20} />
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
        return <CheckCircle size={20} />;
      case 'degraded':
        return <Clock size={20} />;
      case 'unhealthy':
        return <AlertCircle size={20} />;
      default:
        return <AlertCircle size={20} />;
    }
  };

  return (
    <div style={{
      flex: 1,
      backgroundColor: '#f9fafb',
      padding: '24px',
      overflowY: 'auto'
    }}>
      <div style={{maxWidth: '1024px', margin: '0 auto'}}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '24px'
        }}>
          <h1 style={{fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0}}>
            System Health
          </h1>
          <button onClick={onRefresh} style={styles.button}>
            Refresh
          </button>
        </div>

        {healthStatus ? (
          <div style={{display: 'flex', flexDirection: 'column', gap: '24px'}}>
            {/* Overall Status */}
            <div style={styles.card}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '16px'
              }}>
                <h2 style={{fontSize: '18px', fontWeight: '600', color: '#111827', margin: 0}}>
                  Overall Status
                </h2>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '4px 12px',
                  borderRadius: '20px',
                  backgroundColor: getStatusColor(healthStatus.status) + '20',
                  color: getStatusColor(healthStatus.status)
                }}>
                  {getStatusIcon(healthStatus.status)}
                  <span style={{fontWeight: '500', textTransform: 'capitalize'}}>
                    {healthStatus.status}
                  </span>
                </div>
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '16px'
              }}>
                <div style={{textAlign: 'center'}}>
                  <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                    {healthStatus.version}
                  </div>
                  <div style={{fontSize: '14px', color: '#6b7280'}}>Version</div>
                </div>
                <div style={{textAlign: 'center'}}>
                  <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                    {healthStatus.environment}
                  </div>
                  <div style={{fontSize: '14px', color: '#6b7280'}}>Environment</div>
                </div>
                <div style={{textAlign: 'center'}}>
                  <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                    {Math.round(healthStatus.response_time_seconds * 1000)}ms
                  </div>
                  <div style={{fontSize: '14px', color: '#6b7280'}}>Response Time</div>
                </div>
              </div>
            </div>

            {/* Service Checks */}
            <div style={styles.card}>
              <h2 style={{fontSize: '18px', fontWeight: '600', color: '#111827', marginBottom: '16px'}}>
                Service Status
              </h2>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: '16px'
              }}>
                {Object.entries(healthStatus.checks).map(([service, check]) => (
                  <div
                    key={service}
                    style={{
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      padding: '16px'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '8px'
                    }}>
                      <h3 style={{
                        fontWeight: '500',
                        color: '#111827',
                        margin: 0,
                        textTransform: 'capitalize'
                      }}>
                        {service.replace('_', ' ')}
                      </h3>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        backgroundColor: getStatusColor(check.status) + '20',
                        color: getStatusColor(check.status)
                      }}>
                        {getStatusIcon(check.status)}
                        <span style={{textTransform: 'capitalize'}}>{check.status}</span>
                      </div>
                    </div>
                    {check.response_time_ms && (
                      <div style={{fontSize: '14px', color: '#6b7280'}}>
                        Response time: {Math.round(check.response_time_ms)}ms
                      </div>
                    )}
                    {check.error && (
                      <div style={{fontSize: '14px', color: '#dc2626', marginTop: '4px'}}>
                        Error: {getErrorMessage(check.error)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div style={{...styles.card, textAlign: 'center'}}>
            <Activity size={48} color="#9ca3af" style={{margin: '0 auto 16px'}} />
            <h3 style={{fontSize: '18px', fontWeight: '500', color: '#111827', marginBottom: '8px'}}>
              Loading Health Status
            </h3>
            <p style={{color: '#6b7280', margin: 0}}>
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
    <div style={{
      flex: 1,
      backgroundColor: '#f9fafb',
      padding: '24px',
      overflowY: 'auto'
    }}>
      <div style={{maxWidth: '600px', margin: '0 auto'}}>
        <h1 style={{fontSize: '24px', fontWeight: 'bold', color: '#111827', marginBottom: '24px'}}>
          Profile
        </h1>

        {/* User Info */}
        <div style={{...styles.card, marginBottom: '24px'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px'}}>
            <div style={{
              backgroundColor: '#e0e7ff',
              borderRadius: '50%',
              padding: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <User size={32} color="#4f46e5" />
            </div>
            <div>
              <h2 style={{fontSize: '20px', fontWeight: '600', color: '#111827', margin: '0 0 4px'}}>
                {user.first_name} {user.last_name}
              </h2>
              <p style={{color: '#6b7280', margin: '0 0 2px'}}>@{user.username}</p>
              <p style={{color: '#6b7280', margin: 0}}>{user.email}</p>
            </div>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginTop: '24px'
          }}>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                {user.total_chats || 0}
              </div>
              <div style={{fontSize: '14px', color: '#6b7280'}}>Total Chats</div>
            </div>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                {user.total_messages || 0}
              </div>
              <div style={{fontSize: '14px', color: '#6b7280'}}>Total Messages</div>
            </div>
          </div>
        </div>

        {/* User Stats */}
        {stats && (
          <div style={styles.card}>
            <h3 style={{fontSize: '18px', fontWeight: '600', color: '#111827', marginBottom: '16px'}}>
              Usage Statistics
            </h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '16px'
            }}>
              <div style={{textAlign: 'center'}}>
                <Activity size={32} color="#4f46e5" style={{margin: '0 auto 8px'}} />
                <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                  {stats.total_tokens_used || 0}
                </div>
                <div style={{fontSize: '14px', color: '#6b7280'}}>Tokens Used</div>
              </div>
              <div style={{textAlign: 'center'}}>
                <MessageCircle size={32} color="#4f46e5" style={{margin: '0 auto 8px'}} />
                <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                  {stats.avg_messages_per_chat || 0}
                </div>
                <div style={{fontSize: '14px', color: '#6b7280'}}>Avg Messages/Chat</div>
              </div>
              <div style={{textAlign: 'center'}}>
                <Clock size={32} color="#4f46e5" style={{margin: '0 auto 8px'}} />
                <div style={{fontSize: '24px', fontWeight: 'bold', color: '#111827'}}>
                  {stats.last_active || 'N/A'}
                </div>
                <div style={{fontSize: '14px', color: '#6b7280'}}>Last Active</div>
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
`;
document.head.appendChild(style);

export default App;