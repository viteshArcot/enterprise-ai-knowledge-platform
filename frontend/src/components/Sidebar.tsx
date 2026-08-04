import { useState, useEffect } from 'react';
import type { FC } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { FileText, MessageSquarePlus, MessageSquare, Activity } from 'lucide-react';
import { apiClient } from '../services/api';

interface Conversation {
  id: string;
  title: string;
}

export const Sidebar: FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const location = useLocation();

  // Fetch recent conversations
  useEffect(() => {
    let mounted = true;
    const fetchConvos = async () => {
      try {
        const data = await apiClient.get<Conversation[]>('/api/v1/conversations/');
        if (mounted) setConversations(data.slice(0, 10)); // Just recent ones
      } catch (err) {
        console.error('Failed to load conversations', err);
      }
    };
    
    fetchConvos();
  }, [location.pathname]); // Refresh when navigating (e.g. creating new chat)

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">⬡</span>
          <span className="logo-text">AI Knowledge</span>
        </div>
      </div>
      
      <div className="sidebar-scrollable">
        <nav className="sidebar-nav">
          <NavLink 
            to="/" 
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            end
          >
            <FileText size={18} />
            Documents
          </NavLink>
          <NavLink 
            to="/chat/new" 
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <MessageSquarePlus size={18} />
            New Chat
          </NavLink>
          <NavLink 
            to="/status" 
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <Activity size={18} />
            System Status
          </NavLink>
        </nav>

        {conversations.length > 0 && (
          <div className="sidebar-section">
            <h3 className="sidebar-section-title">Recent Chats</h3>
            <nav className="sidebar-nav">
              {conversations.map(conv => (
                <NavLink 
                  key={conv.id}
                  to={`/chat/${conv.id}`}
                  className={({ isActive }) => `sidebar-link chat-link ${isActive ? 'active' : ''}`}
                  title={conv.title}
                >
                  <MessageSquare size={16} />
                  <span className="truncate">{conv.title || 'Untitled Conversation'}</span>
                </NavLink>
              ))}
            </nav>
          </div>
        )}
      </div>
    </aside>
  );
};
