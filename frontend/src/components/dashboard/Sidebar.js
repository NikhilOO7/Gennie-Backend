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
                    {formatDate(chat.created_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => onDeleteChat(chat.id, e)}
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
  );
};

export default Sidebar;