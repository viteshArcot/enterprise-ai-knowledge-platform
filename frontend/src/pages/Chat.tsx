import { useState, useEffect, useRef, useCallback, memo } from 'react';
import type { FC } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, User, Bot, Loader2, MessageSquare, Copy, Check, Square, RefreshCw, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { apiClient } from '../services/api';
import toast from 'react-hot-toast';
import './Chat.css';

interface Citation {
  id: number;
  title: string;
  score?: number;
  metadata?: any;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  citations?: Citation[];
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
}

const copyToClipboard = (text: string, callback?: () => void) => {
  navigator.clipboard.writeText(text).then(() => {
    if (callback) callback();
    else toast.success('Copied to clipboard', { position: 'bottom-center' });
  }).catch(() => {
    toast.error('Failed to copy', { position: 'bottom-center' });
  });
};

const CodeBlock = ({ inline, className, children, ...props }: any) => {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const content = String(children).replace(/\n$/, '');

  const handleCopy = () => {
    copyToClipboard(content, () => setCopied(true));
    setTimeout(() => setCopied(false), 2000);
  };

  if (!inline && match) {
    return (
      <div className="code-block-wrapper">
        <div className="code-block-header">
          <span className="code-language">{match[1]}</span>
          <button onClick={handleCopy} className="code-copy-btn" title="Copy code">
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={match[1]}
          PreTag="div"
          className="syntax-highlighter"
          {...props}
        >
          {content}
        </SyntaxHighlighter>
      </div>
    );
  }

  return (
    <code className={className} {...props}>
      {children}
    </code>
  );
};

const MessageItem = memo(({ 
  msg, 
  isTypingIndicator,
  isLast,
  isGenerating,
  onRegenerate
}: { 
  msg?: Message, 
  isTypingIndicator?: boolean,
  isLast?: boolean,
  isGenerating?: boolean,
  onRegenerate?: (e: React.MouseEvent) => void
}) => {
  if (isTypingIndicator) {
    return (
      <div className="message-wrapper assistant animate-fade-in">
        <div className="message-avatar bot-avatar">
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
    );
  }

  if (!msg) return null;

  const isUser = msg.role === 'user';
  const timeString = msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  return (
    <div className={`message-wrapper ${msg.role} animate-fade-in`}>
      <div className={`message-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>
      <div className="message-content">
        <div className="message-header">
          <span className="message-author">{isUser ? 'You' : 'AI Assistant'}</span>
          {timeString && <span className="message-time">{timeString}</span>}
        </div>
        <div className={`message-bubble ${isLast && isGenerating ? 'streaming' : ''}`}>
          {msg.role === 'assistant' ? (
            <>
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{ code: CodeBlock }}
              >
                {msg.content}
              </ReactMarkdown>
              
              {msg.citations && msg.citations.length > 0 && (
                <div className="message-citations">
                  <div className="citations-header">
                    <BookOpen size={14} /> <span>Sources Used</span>
                  </div>
                  <ul className="citations-list">
                    {msg.citations.map((c, idx) => (
                      <li key={idx} className="citation-item">
                        <span className="citation-number">[{idx + 1}]</span>
                        <span className="citation-title" title={c.title}>{c.title}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{msg.content}</p>
          )}
        </div>
        {msg.role === 'assistant' && msg.content && (
          <div className="message-actions">
            <button 
              className="copy-response-btn" 
              onClick={() => copyToClipboard(msg.content)}
              title="Copy entire response"
            >
              <Copy size={13} /> Copy
            </button>
            {isLast && !isGenerating && onRegenerate && (
              <button 
                className="copy-response-btn regenerate-btn" 
                onClick={onRegenerate}
                title="Regenerate Response"
              >
                <RefreshCw size={13} /> Regenerate
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  if (prevProps.isTypingIndicator !== nextProps.isTypingIndicator) return false;
  if (prevProps.isLast !== nextProps.isLast) return false;
  if (prevProps.isGenerating !== nextProps.isGenerating) return false;
  if (!prevProps.msg || !nextProps.msg) return false;
  return prevProps.msg.content === nextProps.msg.content && prevProps.msg.id === nextProps.msg.id;
});

export const Chat: FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAutoScrollPaused, setIsAutoScrollPaused] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
      setIsAutoScrollPaused(false);
    } catch (err) {
      console.error('Failed to load conversation', err);
      toast.error('Failed to load conversation');
    }
  }, [id]);

  useEffect(() => {
    if (!isNewChat) {
      loadConversation();
    } else {
      setMessages([]);
    }
  }, [id, isNewChat, loadConversation]);

  // Scroll behavior
  const handleScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAutoScrollPaused(!isAtBottom);
  };

  useEffect(() => {
    if (!isAutoScrollPaused) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping, isAutoScrollPaused]);

  // Textarea auto-resize
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const submitMessage = async (text: string) => {
    if (!text.trim() || isTyping || isGenerating) return;

    const userText = text.trim();
    
    // Optimistic UI for user message
    const tempUserMsgId = Date.now().toString();
    setMessages(prev => [...prev, { 
      id: tempUserMsgId, 
      role: 'user', 
      content: userText, 
      created_at: new Date().toISOString() 
    }]);
    
    let activeConversationId = id;
    setIsTyping(true);
    setIsGenerating(true);
    setIsAutoScrollPaused(false); // Force scroll to bottom on new message

    try {
      // Create conversation if it's a new chat
      if (isNewChat) {
        const newConv = await apiClient.post<Conversation>('/api/v1/conversations/', {
          title: userText.slice(0, 40) + (userText.length > 40 ? '...' : '')
        });
        activeConversationId = newConv.id;
        navigate(`/chat/${activeConversationId}`, { replace: true });
      }

      const tempAssistantMsgId = (Date.now() + 1).toString();

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

      let firstChunkReceived = false;
      for await (const chunk of stream) {
        if (!firstChunkReceived) {
          setIsTyping(false);
          firstChunkReceived = true;
          setMessages(prev => [...prev, { 
            id: tempAssistantMsgId, 
            role: 'assistant', 
            content: chunk,
            created_at: new Date().toISOString() 
          }]);
        } else {
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempAssistantMsgId 
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        }
      }
      
    } catch (err: any) {
      console.error('Failed to send message', err);
      if (err.name !== 'AbortError') {
        toast.error('Failed to get response');
      }
    } finally {
      setIsTyping(false);
      setIsGenerating(false);
    }
  };

  const handleRegenerate = (e: React.MouseEvent) => {
    e.preventDefault();
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user');
    if (lastUserMsg) {
      submitMessage(lastUserMsg.content);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    submitMessage(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <div className="chat-page">
      <div 
        className="chat-messages-container" 
        ref={chatContainerRef}
        onScroll={handleScroll}
      >
        {isNewChat && messages.length === 0 ? (
          <div className="chat-empty-state animate-fade-in">
            <div className="chat-empty-icon-wrapper">
              <MessageSquare size={48} className="text-primary" />
            </div>
            <h2>How can I help you today?</h2>
            <p className="text-muted">Ask questions about your uploaded documents to get started.</p>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, idx) => (
              <MessageItem 
                key={msg.id} 
                msg={msg} 
                isLast={idx === messages.length - 1}
                isGenerating={isGenerating}
                onRegenerate={handleRegenerate}
              />
            ))}
            {isTyping && <MessageItem isTypingIndicator={true} />}
            <div ref={messagesEndRef} className="scroll-anchor" />
          </div>
        )}
      </div>

      <div className="chat-input-container">
        {isGenerating && (
          <div className="stop-generation-container">
            <button 
              type="button" 
              className="stop-generation-btn"
              onClick={() => abortControllerRef.current?.abort()}
            >
              <Square size={14} className="mr-2 inline-block" fill="currentColor" /> Stop Generation
            </button>
          </div>
        )}
        <form onSubmit={handleSubmit} className="chat-input-form">
          <div className="chat-input-wrapper">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything (Shift+Enter for new line)..."
              disabled={isTyping}
              className="chat-input-textarea"
              rows={1}
              autoFocus
            />
            <button 
              type="submit" 
              className="btn btn-primary chat-submit-btn"
              disabled={!input.trim() || isTyping || isGenerating}
            >
              {isTyping || isGenerating ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
            </button>
          </div>
        </form>
        <div className="chat-footer-text text-muted">
          AI can make mistakes. Consider verifying important information.
        </div>
      </div>
    </div>
  );
};
