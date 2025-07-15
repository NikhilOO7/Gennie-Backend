import React from 'react';
import { 
  User, 
  LogOut, 
  Plus, 
  MessageCircle, 
  Activity, 
  Settings, 
  Moon, 
  Sun,
  Trash2 
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { styles } from '../../utils/styles';
import { formatDate } from '../../utils/helpers';

const Sidebar = ({ 
  activeTab, 
  setActiveTab, 
  chats, 
  activeChat, 
  setActiveChat,
  onCreateNewChat,
  onDeleteChat,
  darkMode,
  setDarkMode,
  setShowSettings
}) => {
  const { user, logout } = useAuth();

  const navigationTabs = [
    { id: 'chat', label: 'Chat', icon: MessageCircle },
    { id: 'health', label: 'Health Status', icon: Activity },
    { id: 'profile', label: 'Profile', icon: User }
  ];

  return (
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
          onClick={onCreateNewChat}
          style={{ ...styles.button, width: '100%', marginTop: '16px' }}
        >
          <Plus size={16} style={{ marginRight: '8px', display: 'inline' }} />
          New Chat
        </button>
      </div>

      {/* Navigation */}
      <div style={{ padding: '8px' }}>
        <div style={{ marginBottom: '16px' }}>
          {navigationTabs.map((tab) => (
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
                color: activeTab === tab.id ? '#4338ca' : darkMode ? '#f3f4f6' : '#6b7280',
                width: '100%',
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <tab.icon size={20} />
              <span style={{ fontSize: '14px', fontWeight: '500' }}>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chat List */}
      {activeTab === 'chat' && (
        <div style={{ 
          flex: 1, 
          overflowY: 'auto', 
          padding: '8px',
          borderTop: '1px solid #e5e7eb'
        }}>
          <p style={{ 
            fontSize: '12px', 
            color: '#6b7280', 
            padding: '8px 12px',
            fontWeight: '500'
          }}>
            Your Chats
          </p>
          {chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => setActiveChat(chat)}
              style={{
                padding: '12px',
                marginBottom: '4px',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'background-color 0.2s',
                backgroundColor: activeChat?.id === chat.id ? '#e0e7ff' : 'transparent',
                ':hover': {
                  backgroundColor: darkMode ? '#374151' : '#f3f4f6'
                }
              }}
              onMouseEnter={(e) => {
                if (activeChat?.id !== chat.id) {
                  e.currentTarget.style.backgroundColor = darkMode ? '#374151' : '#f3f4f6';
                }
              }}
              onMouseLeave={(e) => {
                if (activeChat?.id !== chat.id) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontWeight: '500', 
                    color: activeChat?.id === chat.id ? '#4338ca' : darkMode ? '#f3f4f6' : '#111827',
                    marginBottom: '4px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {chat.title}
                  </div>
                  <div style={{ 
                    fontSize: '12px', 
                    color: '#9ca3af',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {chat.description}
                  </div>
                  {chat.last_message_at && (
                    <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                      {formatDate(chat.last_message_at)}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '4px', alignItems: 'center', marginLeft: '8px' }}>
                  {chat.chat_mode && (
                    <span style={{
                      fontSize: '10px',
                      padding: '2px 6px',
                      borderRadius: '10px',
                      backgroundColor: activeChat?.id === chat.id ? '#4f46e5' : '#f3f4f6',
                      color: activeChat?.id === chat.id ? 'white' : '#6b7280',
                      fontWeight: '500',
                      whiteSpace: 'nowrap'
                    }}>
                      {chat.chat_mode === 'voice' ? '🎤' : '💬'}
                    </span>
                  )}
                  <button
                    onClick={(e) => onDeleteChat(chat.id, e)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '4px',
                      color: '#6b7280',
                      opacity: 0,
                      transition: 'opacity 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.opacity = '1';
                      e.stopPropagation();
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.opacity = '0';
                    }}
                    title="Delete chat"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {chats.length === 0 && (
            <div style={{ 
              textAlign: 'center', 
              padding: '20px',
              color: '#9ca3af',
              fontSize: '14px'
            }}>
              No chats yet. Create one to get started!
            </div>
          )}
        </div>
      )}

      {/* Bottom Controls */}
      <div style={{ 
        padding: '16px', 
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <button
          onClick={() => setDarkMode(!darkMode)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#6b7280',
            padding: '8px',
            borderRadius: '8px',
            transition: 'background-color 0.2s'
          }}
          title={darkMode ? 'Light mode' : 'Dark mode'}
        >
          {darkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        <button
          onClick={() => setShowSettings(true)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#6b7280',
            padding: '8px',
            borderRadius: '8px',
            transition: 'background-color 0.2s'
          }}
          title="Settings"
        >
          <Settings size={20} />
        </button>
      </div>
    </div>
  );
};

export default Sidebar;