import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import ChatInterface from '../chat/ChatInterface';
import HealthDashboard from '../health/HealthDashboard';
import UserProfile from '../profile/UserProfile';
import SettingsModal from '../settings/SettingsModal';
import NewChatModal from '../chat/NewChatModal';
import apiService from '../../services/api';
import { styles } from '../../utils/styles';
import { saveToLocalStorage, getFromLocalStorage } from '../../utils/helpers';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [darkMode, setDarkMode] = useState(getFromLocalStorage('darkMode', false));
  const [showSettings, setShowSettings] = useState(false);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [userTopics, setUserTopics] = useState([]);

  useEffect(() => {
    fetchChats();
    fetchHealthStatus();
    fetchUserTopics();
  }, []);

  // Add new function
  const fetchUserTopics = async () => {
    try {
      const data = await apiService.getUserTopics();
      setUserTopics(data.available_topics.filter(topic => 
        data.selected_topics.includes(topic.id)
      ));
    } catch (error) {
      console.error('Failed to fetch user topics:', error);
    }
  };

  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
    saveToLocalStorage('darkMode', darkMode);
  }, [darkMode]);

  const fetchChats = async () => {
    try {
      const data = await apiService.getChats();
      setChats(data.chats || data || []);
    } catch (error) {
      console.error('Failed to fetch chats:', error);
    }
  };

  const fetchHealthStatus = async () => {
    try {
      const data = await apiService.getHealthStatus();
      setHealthStatus(data);
    } catch (error) {
      console.error('Failed to fetch health status:', error);
    }
  };

  const createNewChat = async (chatConfig) => {
    try {
      const title = `${chatConfig.mode === 'voice' ? 'Voice' : 'Text'} Chat ${chats.length + 1}`;
      const topic = userTopics.find(t => t.id === chatConfig.topic);
      
      const newChat = await apiService.createChat({
        title: topic ? `${topic.name} Chat` : title,
        description: topic ? `${chatConfig.mode} conversation about ${topic.name}` : `New ${chatConfig.mode} conversation`,
        mode: chatConfig.mode,
        topic: chatConfig.topic
      });
      
      setChats([newChat, ...chats]);
      setActiveChat(newChat);
      setActiveTab('chat');
      setShowNewChatModal(false);
    } catch (error) {
      console.error('Failed to create chat:', error);
    }
  };

  const deleteChat = async (chatId, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this chat?')) return;

    try {
      await apiService.deleteChat(chatId);
      setChats(chats.filter(chat => chat.id !== chatId));
      if (activeChat?.id === chatId) {
        setActiveChat(null);
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'chat':
        return (
          <ChatInterface
            activeChat={activeChat}
            setActiveChat={setActiveChat}
            chats={chats}
            setChats={setChats}
          />
        );
      case 'health':
        return (
          <HealthDashboard
            healthStatus={healthStatus}
            onRefresh={fetchHealthStatus}
          />
        );
      case 'profile':
        return <UserProfile />;
      default:
        return null;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: darkMode ? '#1f2937' : '#f3f4f6' }}>
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        chats={chats}
        activeChat={activeChat}
        setActiveChat={setActiveChat}
        onCreateNewChat={() => setShowNewChatModal(true)}
        onDeleteChat={deleteChat}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        setShowSettings={setShowSettings}
      />

      <div style={styles.mainContent}>
        {renderContent()}
      </div>

      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          darkMode={darkMode}
        />
      )}
      
      <NewChatModal
        isOpen={showNewChatModal}
        onClose={() => setShowNewChatModal(false)}
        onCreate={createNewChat}
        userTopics={userTopics}
      />
    </div>
  );
};

export default Dashboard;