import { useState, useEffect, useRef, useCallback, memo } from 'react';
import type { FC } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, Copy, Check, Square, RefreshCw, BookOpen, FileText, FilePlus, Sparkles, ArrowRight, Search, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { apiClient } from '../services/api';
import toast from 'react-hot-toast';
import { Popover, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import './Chat.css';

interface Document {
  id: string;
  title: string;
  file_name: string;
}

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
  documents?: Document[];
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
        <div className="nova-avatar small">
          <Sparkles size={14} />
        </div>
        <div className="message-content">
          <div className="assistant-bubble">
            <div className="typing-indicator">
              <Loader2 size={16} className="spin-icon" /> Analyzing data, please wait...
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!msg) return null;

  const isUser = msg.role === 'user';

  return (
    <div className={`message-wrapper ${isUser ? 'user' : 'assistant'} animate-fade-in`}>
      {!isUser && (
        <div className="nova-avatar small">
          <Sparkles size={14} />
        </div>
      )}
      <div className="message-content">
        <div className={isUser ? 'user-bubble' : 'assistant-bubble'}>
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
                    <BookOpen size={14} /> <span>Sources</span>
                  </div>
                  <ul className="citations-list">
                    {msg.citations.map((c, idx) => (
                      <li key={idx} className="citation-card">
                        <div className="citation-title-row">
                          <FileText size={14} className="text-muted" />
                          <span>{c.title}</span>
                        </div>
                        {c.metadata && c.metadata.page_number && (
                          <div className="citation-pages">Page {c.metadata.page_number}</div>
                        )}
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
  const [availableDocs, setAvailableDocs] = useState<Document[]>([]);
  const [attachedDocs, setAttachedDocs] = useState<Document[]>([]);
  const [docSearchTerm, setDocSearchTerm] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingTogglesRef = useRef<Set<string>>(new Set());

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
      setAttachedDocs(data.documents || []);
      setIsAutoScrollPaused(false);
    } catch (err) {
      console.error('Failed to load conversation', err);
      toast.error('Failed to load conversation');
    }
  }, [id]);

  const loadDocuments = useCallback(async () => {
    try {
      const data = await apiClient.get<Document[]>('/api/v1/documents/');
      setAvailableDocs(data);
    } catch (err) {
      console.error('Failed to load documents', err);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    if (!isNewChat) {
      loadConversation();
    } else {
      setMessages([]);
      setAttachedDocs([]);
    }
  }, [id, isNewChat, loadConversation, loadDocuments]);

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

        // Attach any selected documents
        for (const doc of attachedDocs) {
          await apiClient.post(`/api/v1/conversations/${activeConversationId}/documents/${doc.id}`, {});
        }

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
        {
          message: userText,
          document_ids: attachedDocs.map(d => d.id)
        },
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

  const handleToggleDocument = async (doc: Document) => {
    if (pendingTogglesRef.current.has(doc.id)) return;

    const isAttached = attachedDocs.some(d => d.id === doc.id);

    if (isNewChat) {
      // Just update local state
      if (isAttached) {
        setAttachedDocs(prev => prev.filter(d => d.id !== doc.id));
      } else {
        setAttachedDocs(prev => [...prev, doc]);
      }
    } else {
      pendingTogglesRef.current.add(doc.id);

      // Optimistic UI update
      setAttachedDocs(prev => isAttached
        ? prev.filter(d => d.id !== doc.id)
        : [...prev, doc]
      );

      // API call to attach/detach
      try {
        if (isAttached) {
          await apiClient.delete(`/api/v1/conversations/${id}/documents/${doc.id}`);
        } else {
          await apiClient.post(`/api/v1/conversations/${id}/documents/${doc.id}`, {});
        }
      } catch (err) {
        // Rollback
        setAttachedDocs(prev => isAttached
          ? [...prev, doc]
          : prev.filter(d => d.id !== doc.id)
        );
        toast.error('Failed to update document attachments');
      } finally {
        pendingTogglesRef.current.delete(doc.id);
      }
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
            <div className="nova-avatar large">
              <Sparkles size={32} />
            </div>
            <h2>ASK NOVA</h2>
            <p className="text-muted mt-2">Ask questions, explore your documents, and get answers grounded in your knowledge.</p>
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
            {attachedDocs.length > 0 && (
              <div className="attachments-bar">
                {attachedDocs.map(doc => (
                  <div key={doc.id} className="attachment-chip">
                    <FileText size={12} className="text-muted" />
                    <span className="truncate max-w-[150px]" title={doc.title}>{doc.title}</span>
                    <button
                      type="button"
                      onClick={() => handleToggleDocument(doc)}
                      className="chip-remove ml-1"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="input-row">
              <Popover className="relative">
                <Popover.Button className="composer-icon-btn" title="Attach Document">
                  <FilePlus size={20} />
                </Popover.Button>
                <Transition
                  as={Fragment}
                  enter="transition ease-out duration-200"
                  enterFrom="opacity-0 translate-y-1"
                  enterTo="opacity-100 translate-y-0"
                  leave="transition ease-in duration-150"
                  leaveFrom="opacity-100 translate-y-0"
                  leaveTo="opacity-0 translate-y-1"
                >
                  <Popover.Panel className="document-picker-panel">
                    <div className="document-picker-search">
                      <Search size={16} className="text-muted" />
                      <input
                        type="text"
                        placeholder="Search documents..."
                        value={docSearchTerm}
                        onChange={(e) => setDocSearchTerm(e.target.value)}
                        className="document-search-input"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div className="document-picker-list">
                      {availableDocs.filter(d =>
                        d.title.toLowerCase().includes(docSearchTerm.toLowerCase()) ||
                        d.file_name.toLowerCase().includes(docSearchTerm.toLowerCase())
                      ).length === 0 ? (
                        <div className="document-picker-empty">No documents found.</div>
                      ) : (
                        availableDocs
                          .filter(d =>
                            d.title.toLowerCase().includes(docSearchTerm.toLowerCase()) ||
                            d.file_name.toLowerCase().includes(docSearchTerm.toLowerCase())
                          )
                          .map(doc => {
                          const isSelected = attachedDocs.some(d => d.id === doc.id);
                          return (
                            <button
                              key={doc.id}
                              type="button"
                              onClick={() => handleToggleDocument(doc)}
                              className="document-picker-row"
                            >
                              <div className={`document-checkbox ${isSelected ? 'selected' : ''}`}>
                                {isSelected && <Check size={12} />}
                              </div>
                              <div className="document-info">
                                <div className="document-title truncate">{doc.title}</div>
                                <div className="document-meta truncate">{doc.file_name}</div>
                              </div>
                            </button>
                          );
                        })
                      )}
                    </div>
                  </Popover.Panel>
                </Transition>
              </Popover>

              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                placeholder="Ask, write or search for anything..."
                disabled={isTyping}
                className="chat-input-textarea"
                rows={1}
                autoFocus
              />
              <button
                type="submit"
                className="chat-submit-btn"
                disabled={!input.trim() || isTyping || isGenerating}
              >
                {isTyping || isGenerating ? <Loader2 size={16} className="spin-icon" /> : <ArrowRight size={16} />}
              </button>
            </div>
          </div>
        </form>
        <div className="chat-footer-text">
          Nova can make mistakes. Verify important information.
        </div>
      </div>
    </div>
  );
};
