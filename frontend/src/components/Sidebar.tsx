import { useState, useEffect, useMemo, useRef } from 'react';
import type { FC } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { FileText, MessageSquarePlus, MessageSquare, Activity, Search, Edit2, Trash2, X, Check, Sparkles } from 'lucide-react';
import { apiClient } from '../services/api';
import toast from 'react-hot-toast';

interface Conversation {
  id: string;
  title: string;
  created_at?: string;
}

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: FC<SidebarProps> = ({ isOpen, onClose }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let mounted = true;
    const fetchConvos = async () => {
      try {
        const data = await apiClient.get<Conversation[]>('/api/v1/conversations/');
        if (mounted) setConversations(data);
      } catch (err) {
        console.error('Failed to load conversations', err);
      }
    };

    fetchConvos();
    return () => { mounted = false; };
  }, [location.pathname]);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
    }
  }, [editingId]);

  const handleRenameSubmit = async (id: string, e?: React.FormEvent | React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    if (!editTitle.trim() || editTitle.trim() === conversations.find(c => c.id === id)?.title) {
      setEditingId(null);
      return;
    }

    const oldConvos = [...conversations];
    const newTitle = editTitle.trim();

    setConversations(prev => prev.map(c => c.id === id ? { ...c, title: newTitle } : c));
    setEditingId(null);

    try {
      await apiClient.patch(`/api/v1/conversations/${id}`, { title: newTitle });
      toast.success('Conversation renamed');
    } catch (err) {
      setConversations(oldConvos);
      toast.error('Failed to rename conversation');
    }
  };

  const handleKeyDown = (id: string, e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRenameSubmit(id, e);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this conversation?')) return;

    try {
      await apiClient.delete(`/api/v1/conversations/${id}`);
      setConversations(prev => prev.filter(c => c.id !== id));
      if (location.pathname === `/chat/${id}`) {
        navigate('/chat/new');
      }
      toast.success('Conversation deleted');
    } catch (err) {
      toast.error('Failed to delete conversation');
    }
  };

  const filteredConvos = useMemo(() => {
    if (!searchTerm) return conversations;
    return conversations.filter(c => c.title.toLowerCase().includes(searchTerm.toLowerCase()));
  }, [conversations, searchTerm]);

  // Grouping logic
  const groupedConvos = useMemo(() => {
    const groups = {
      Today: [] as Conversation[],
      Yesterday: [] as Conversation[],
      'Previous 7 Days': [] as Conversation[],
      Older: [] as Conversation[],
      'Recent Chats': [] as Conversation[] // Fallback
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const yesterday = today - 86400000;
    const last7Days = today - 86400000 * 7;

    filteredConvos.forEach(conv => {
      if (!conv.created_at) {
        groups['Recent Chats'].push(conv);
        return;
      }
      const convTime = new Date(conv.created_at).getTime();
      if (convTime >= today) {
        groups['Today'].push(conv);
      } else if (convTime >= yesterday) {
        groups['Yesterday'].push(conv);
      } else if (convTime >= last7Days) {
        groups['Previous 7 Days'].push(conv);
      } else {
        groups['Older'].push(conv);
      }
    });

    return groups;
  }, [filteredConvos]);

  const hasGroups = Object.keys(groupedConvos).some(k => k !== 'Recent Chats' && groupedConvos[k as keyof typeof groupedConvos].length > 0);

  // Render groups
  const renderGroup = (title: string, convos: Conversation[]) => {
    if (convos.length === 0) return null;
    return (
      <div key={title} className="sidebar-section">
        <h3 className="sidebar-section-title">{title}</h3>
        <nav className="sidebar-nav">
          {convos.map(conv => (
            <div key={conv.id} className="sidebar-chat-item">
              <NavLink
                to={`/chat/${conv.id}`}
                className={({ isActive }) => `sidebar-link chat-link ${isActive ? 'active' : ''}`}
                title={conv.title}
                onClick={(e) => {
                  if (editingId === conv.id) {
                    e.preventDefault();
                  } else if (onClose) {
                    onClose();
                  }
                }}
              >
                <MessageSquare size={16} className="chat-icon" />
                {editingId === conv.id ? (
                  <input
                    ref={editInputRef}
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(conv.id, e)}
                    onBlur={() => setEditingId(null)}
                    onClick={(e) => e.preventDefault()}
                    className="sidebar-edit-input"
                  />
                ) : (
                  <span className="truncate">{conv.title || 'Untitled Conversation'}</span>
                )}
              </NavLink>
              <div className="chat-actions">
                 {editingId === conv.id ? (
                   <button className="chat-action-btn text-success" onMouseDown={(e) => handleRenameSubmit(conv.id, e)} title="Save">
                     <Check size={14} />
                   </button>
                 ) : (
                   <button className="chat-action-btn" onClick={(e) => { e.preventDefault(); e.stopPropagation(); setEditingId(conv.id); setEditTitle(conv.title || ''); }} title="Rename">
                     <Edit2 size={14} />
                   </button>
                 )}
                 <button className="chat-action-btn hover-danger" onClick={(e) => handleDelete(conv.id, e)} title="Delete">
                   <Trash2 size={14} />
                 </button>
              </div>
            </div>
          ))}
        </nav>
      </div>
    );
  };

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon"><Sparkles size={18} /></span>
          <span className="logo-text">AI Knowledge</span>
        </div>
        <button className="mobile-close-btn" onClick={onClose}>
          <X size={20} />
        </button>
      </div>

      <div className="sidebar-search-container">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search chats..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="sidebar-search-input"
          />
        </div>
      </div>

      <div className="sidebar-scrollable">
        <nav className="sidebar-nav">
          <NavLink
            to="/"
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            end
            onClick={onClose}
          >
            <FileText size={18} />
            Documents
          </NavLink>
          <NavLink
            to="/chat/new"
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            onClick={onClose}
          >
            <MessageSquarePlus size={18} />
            New Chat
          </NavLink>
          <NavLink
            to="/status"
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            onClick={onClose}
          >
            <Activity size={18} />
            System Status
          </NavLink>
        </nav>

        {hasGroups ? (
          <>
            {renderGroup('Today', groupedConvos['Today'])}
            {renderGroup('Yesterday', groupedConvos['Yesterday'])}
            {renderGroup('Previous 7 Days', groupedConvos['Previous 7 Days'])}
            {renderGroup('Older', groupedConvos['Older'])}
          </>
        ) : (
          renderGroup('Recent Chats', groupedConvos['Recent Chats'])
        )}
      </div>
    </aside>
  );
};
