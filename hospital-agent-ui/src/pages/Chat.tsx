import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import '../css/Chat.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: number;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hello! I'm your AI assistant. Ask me about hospital protocols, procedures, or any medical questions.",
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionStart] = useState(new Date());
  const [sessionDuration, setSessionDuration] = useState('0 min');
  const [modelName, setModelName] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Update session duration every minute
  useEffect(() => {
    const updateDuration = () => {
      const now = new Date();
      const diffMs = now.getTime() - sessionStart.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      setSessionDuration(`${diffMins} min`);
    };

    updateDuration();
    const interval = setInterval(updateDuration, 60000); // Update every minute
    return () => clearInterval(interval);
  }, [sessionStart]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Format conversation history for API
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp.toISOString()
      }));

      const response = await fetch('http://localhost:8000/api/v1/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          conversation_history: conversationHistory,
          stream: false,
        }),
      });

      const data = await response.json();
      console.log('Chat response:', data);
      
      // Update model name from response
      if (data.model && !modelName) {
        setModelName(data.model);
      }
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || 'I apologize, but I couldn\'t generate a response.',
        timestamp: new Date(),
        sources: data.hospital_context?.relevant_protocols?.length || 0,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestion = (question: string) => {
    setInput(question);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>💬 AI Chat Assistant</h1>
      </div>
      
      <div className="chat-layout">
        <div className="suggestions-panel">
          <h3>💡 Suggested Questions</h3>
          <div className="suggestion-category">
            <div className="category-title">🚨 Emergency</div>
            <button 
              className="suggestion-btn"
              onClick={() => handleSuggestion('What is the emergency triage protocol?')}
            >
              Emergency triage protocol
            </button>
            <button 
              className="suggestion-btn"
              onClick={() => handleSuggestion('What is the cardiac arrest procedure?')}
            >
              Cardiac arrest procedure
            </button>
          </div>
          <div className="suggestion-category">
            <div className="category-title">💊 Treatment</div>
            <button 
              className="suggestion-btn"
              onClick={() => handleSuggestion('What are the respiratory treatment guidelines?')}
            >
              Respiratory treatment guidelines
            </button>
            <button 
              className="suggestion-btn"
              onClick={() => handleSuggestion('What are the medication protocols?')}
            >
              Medication protocols
            </button>
          </div>
        </div>

        <div className="chat-main">
          <div className="messages">
            {messages.map((message) => (
              <div key={message.id} className={`message ${message.role}`}>
                {message.role === 'assistant' && <div className="avatar">🤖</div>}
                <div className="message-content">
                  <div className="message-text">
                    {message.role === 'assistant' ? (
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    ) : (
                      message.content
                    )}
                  </div>
                  {message.sources && message.sources > 0 && (
                    <div className="rag-indicator">
                      🔍 Retrieved from {message.sources} document{message.sources > 1 ? 's' : ''}
                    </div>
                  )}
                  <div className="message-time">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
                {message.role === 'user' && <div className="avatar">👤</div>}
              </div>
            ))}
            
            {isLoading && (
              <div className="typing-indicator">
                <div className="avatar">🤖</div>
                <div className="typing-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input">
            <input 
              type="text" 
              placeholder="Ask about protocols, procedures, treatments..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
            />
            <button 
              className="btn btn-primary"
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>

        <div className="context-panel">
          <h3>📋 Context</h3>
          <div className="context-item">
            <div className="context-label">Hospital</div>
            <div className="context-value">Apollo City Hospital (H001)</div>
          </div>
          <div className="context-item">
            <div className="context-label">Session</div>
            <div className="context-value">
              Active ({sessionDuration})
            </div>
          </div>
          <div className="context-item">
            <div className="context-label">Messages</div>
            <div className="context-value">{messages.length} total</div>
          </div>
          <div className="context-item">
            <div className="context-label">Model</div>
            <div className="context-value">{modelName || 'Loading...'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
