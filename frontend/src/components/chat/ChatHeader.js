// components/chat/ChatHeader.js
import React, { useState } from 'react';
import { 
  MessageCircle, 
  Volume2, 
  VolumeX, 
  Mic, 
  MicOff, 
  Keyboard,
  MoreVertical,
  Settings,
  Brain,
  Activity,
  Zap
} from 'lucide-react';

const ChatHeader = ({ 
  chat, 
  isConnected, 
  soundEnabled, 
  setSoundEnabled,
  showRAGVisualization,
  setShowRAGVisualization,
  onToggleInputMode
}) => {
  const [showOptions, setShowOptions] = useState(false);

  const getConnectionStatus = () => {
    if (isConnected) {
      return {
        icon: Activity,
        text: 'Connected',
        color: 'text-green-500'
      };
    } else {
      return {
        icon: Activity,
        text: 'Connecting...',
        color: 'text-yellow-500'
      };
    }
  };

  const connectionStatus = getConnectionStatus();
  const ConnectionIcon = connectionStatus.icon;

  return (
    <div className="border-b bg-white px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Chat Info */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <MessageCircle size={20} className="text-blue-500" />
            <div>
              <h3 className="font-semibold text-gray-900 truncate max-w-48">
                {chat?.title || 'AI Chat'}
              </h3>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                {/* Connection Status */}
                <div className={`flex items-center space-x-1 ${connectionStatus.color}`}>
                  <ConnectionIcon size={14} />
                  <span>{connectionStatus.text}</span>
                </div>
                
                {/* Chat Mode */}
                {chat?.chat_mode && (
                  <span className="px-2 py-1 bg-gray-100 rounded-full text-xs">
                    {chat.chat_mode}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-2">
          {/* Sound Toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-2 rounded-lg transition-colors ${
              soundEnabled
                ? 'text-blue-500 hover:text-blue-600 hover:bg-blue-50'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
            }`}
            title={soundEnabled ? 'Disable Sound' : 'Enable Sound'}
          >
            {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
          </button>

          {/* RAG Visualization Toggle */}
          <button
            onClick={() => setShowRAGVisualization(!showRAGVisualization)}
            className={`p-2 rounded-lg transition-colors ${
              showRAGVisualization
                ? 'text-purple-500 hover:text-purple-600 hover:bg-purple-50'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
            }`}
            title={showRAGVisualization ? 'Hide RAG Info' : 'Show RAG Info'}
          >
            <Brain size={18} />
          </button>

          {/* Options Menu */}
          <div className="relative">
            <button
              onClick={() => setShowOptions(!showOptions)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="More Options"
            >
              <MoreVertical size={18} />
            </button>

            {showOptions && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                <div className="py-1">
                  <button
                    onClick={() => {
                      setShowOptions(false);
                      // Add chat settings functionality
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                  >
                    <Settings size={16} />
                    <span>Chat Settings</span>
                  </button>
                  
                  <button
                    onClick={() => {
                      setShowOptions(false);
                      // Add export functionality
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Export Chat
                  </button>
                  
                  <button
                    onClick={() => {
                      setShowOptions(false);
                      // Add clear functionality
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                  >
                    Clear Messages
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Disconnect Warning */}
      {!isConnected && (
        <div className="mt-2 flex items-center space-x-2 text-xs text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full">
          <Activity size={12} />
          <span>Reconnecting to chat server...</span>
        </div>
      )}
    </div>
  );
};

export default ChatHeader;