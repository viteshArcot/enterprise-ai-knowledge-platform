import { useState, useEffect, useRef, useCallback } from 'react';
import type { FC } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, User, Bot, Loader2, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { apiClient } from '../services/api';
import './Chat.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
}

export const Chat: FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);
  
  const isNewChat = id === 'new' || !id;

  const loadConversation = useCallback(async () => {
    try {
      const data = await apiClient.get<Conversation>(`/api/v1/conversations/${id}`);
      setMessages(data.messages || []);
    } catch (err) {
      console.error('Failed to load conversation', err);
    }
  }, [id]);

  useEffect(() => {
    if (!isNewChat) {
      loadConversation();
    } else {
      setMessages([]);
    }
  }, [id, isNewChat, loadConversation]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userText = input.trim();
    setInput('');
    
    // Optimistic UI for user message
    const tempUserMsgId = Date.now().toString();
    setMessages(prev => [...prev, { id: tempUserMsgId, role: 'user', content: userText }]);
    
    let activeConversationId = id;
    setIsTyping(true);

    try {
      // Create conversation if it's a new chat
      if (isNewChat) {
        const newConv = await apiClient.post<Conversation>('/api/v1/conversations/', {
          title: userText.slice(0, 40) + (userText.length > 40 ? '...' : '')
        });
        activeConversationId = newConv.id;
        navigate(`/chat/${activeConversationId}`, { replace: true });
      }

      // Prepare assistant message slot
      const tempAssistantMsgId = (Date.now() + 1).toString();
      setMessages(prev => [...prev, { id: tempAssistantMsgId, role: 'assistant', content: '' }]);

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // Start stream
      const stream = apiClient.stream(
        `/api/v1/conversations/${activeConversationId}/messages`, 
        { message: userText },
        { signal: abortControllerRef.current.signal }
      );

      for await (const chunk of stream) {
        setMessages(prev => 
          prev.map(msg => 
            msg.id === tempAssistantMsgId 
              ? { ...msg, content: msg.content + chunk }
              : msg
          )
        );
      }
      
    } catch (err) {
      console.error('Failed to send message', err);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chat-page animate-fade-in">
      <div className="chat-messages-container">
        {isNewChat && messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="chat-empty-icon">
              <MessageSquare size={48} className="text-primary" />
            </div>
            <h2>How can I help you today?</h2>
            <p className="text-muted">Ask questions about your uploaded documents.</p>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-wrapper ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                </div>
                <div className="message-content">
                  <div className="message-header">
                    <span className="message-author">{msg.role === 'user' ? 'You' : 'AI Assistant'}</span>
                  </div>
                  <div className="message-bubble">
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      <p>{msg.content}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="message-wrapper assistant typing">
                <div className="message-avatar">
                  <Bot size={20} />
                </div>
                <div className="message-content">
                  <div className="message-header">
                    <span className="message-author">AI Assistant</span>
                  </div>
                  <div className="message-bubble typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="chat-input-container">
        <form onSubmit={handleSubmit} className="chat-input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isTyping}
            className="chat-input"
            autoFocus
          />
          <button 
            type="submit" 
            className="btn btn-primary chat-submit-btn"
            disabled={!input.trim() || isTyping}
          >
            {isTyping ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
          </button>
        </form>
      </div>
    </div>
  );
};
