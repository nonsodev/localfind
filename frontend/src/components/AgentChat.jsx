import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import AudioPlayer from './AudioPlayer'

const API = '/api'

const AGENT_MODALITIES = [
  { id: 'text',  label: 'Docs',   icon: '📄' },
  { id: 'image', label: 'Images', icon: '🖼️' },
  { id: 'audio', label: 'Audio',  icon: '🎵' },
  { id: 'video', label: 'Video',  icon: '🎬', note: 'slower' },
]

export default function AgentChat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [expandedPreview, setExpandedPreview] = useState(null)
  const [searchModalities, setSearchModalities] = useState(['text', 'image', 'audio'])
  const messagesEndRef = useRef(null)

  const toggleModality = (id) => {
    setSearchModalities(prev =>
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    )
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    console.log('Sending message to agent:', userMessage)

    try {
      const res = await fetch(`${API}/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_history: messages,
          search_modalities: searchModalities.join(','),
        })
      })

      if (res.ok) {
        const data = await res.json()
        console.log('Agent response data:', data)
        console.log('File references received:', data.file_references)
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          sources: data.sources || [],
          fileReferences: data.file_references || []
        }])
      } else {
        console.error('Agent chat failed with status:', res.status)
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          error: true
        }])
      }
    } catch (e) {
      console.error('Agent chat connection error:', e)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Cannot connect to agent. Make sure the backend is running.',
        error: true
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '70vh',
      background: 'rgba(255, 255, 255, 0.03)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      borderRadius: 16,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <svg viewBox="0 0 56 56" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
              <circle cx="22" cy="22" r="14" fill="none" stroke="white" strokeWidth="2.6" opacity="0.95"/>
              <line x1="22" y1="12" x2="15" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
              <line x1="22" y1="12" x2="29" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
              <line x1="15" y1="28" x2="29" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
              <circle cx="22" cy="12" r="1.9" fill="white" opacity="0.95"/>
              <circle cx="15" cy="28" r="1.9" fill="white" opacity="0.95"/>
              <circle cx="29" cy="28" r="1.9" fill="white" opacity="0.95"/>
              <line x1="33" y1="33" x2="46" y2="46" stroke="white" strokeWidth="2.6" strokeLinecap="round" opacity="0.95"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 600 }}>LocalFind Agent</div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.5)' }}>
              Local Multimodal Semantic Search
            </div>
          </div>
        </div>
        
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: '1px solid rgba(255, 255, 255, 0.2)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'rgba(255, 255, 255, 0.7)',
              fontSize: '0.8rem',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            Clear Chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: 24,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: 'rgba(255, 255, 255, 0.5)',
          }}>
            <div style={{ fontSize: '3rem', marginBottom: 16 }}>💬</div>
            <div style={{ fontSize: '1.1rem', marginBottom: 8 }}>Start a conversation</div>
            <div style={{ fontSize: '0.9rem' }}>
              Ask me anything about your indexed documents
            </div>
            <div style={{
              marginTop: 24,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              alignItems: 'center',
            }}>
              <div style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.4)' }}>
                Try asking:
              </div>
              <div style={{ fontSize: '0.8rem', fontStyle: 'italic' }}>
                "What is machine learning?"
              </div>
              <div style={{ fontSize: '0.8rem', fontStyle: 'italic' }}>
                "Show me neural network diagrams"
              </div>
              <div style={{ fontSize: '0.8rem', fontStyle: 'italic' }}>
                "Summarize the Q3 policy update"
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
              animation: 'fadeUp 0.3s ease',
            }}
          >
            {/* Avatar */}
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              flexShrink: 0,
              background: msg.role === 'user'
                ? 'rgba(255, 255, 255, 0.1)'
                : 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1rem',
            }}>
              {msg.role === 'user' ? '👤' : (
                <svg viewBox="0 0 56 56" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="22" cy="22" r="14" fill="none" stroke="white" strokeWidth="2.6" opacity="0.95"/>
                  <line x1="22" y1="12" x2="15" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
                  <line x1="22" y1="12" x2="29" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
                  <line x1="15" y1="28" x2="29" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
                  <circle cx="22" cy="12" r="1.9" fill="white" opacity="0.95"/>
                  <circle cx="15" cy="28" r="1.9" fill="white" opacity="0.95"/>
                  <circle cx="29" cy="28" r="1.9" fill="white" opacity="0.95"/>
                  <line x1="33" y1="33" x2="46" y2="46" stroke="white" strokeWidth="2.6" strokeLinecap="round" opacity="0.95"/>
                </svg>
              )}
            </div>

            {/* Message */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                background: msg.role === 'user'
                  ? 'rgba(255, 255, 255, 0.05)'
                  : msg.error
                  ? 'rgba(239, 68, 68, 0.1)'
                  : 'rgba(102, 126, 234, 0.1)',
                border: `1px solid ${msg.role === 'user'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : msg.error
                  ? 'rgba(239, 68, 68, 0.3)'
                  : 'rgba(102, 126, 234, 0.3)'}`,
                borderRadius: 12,
                padding: '12px 16px',
                fontSize: '0.9rem',
                lineHeight: 1.6,
                color: 'rgba(255, 255, 255, 0.9)',
                wordBreak: 'break-word',
              }}>
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p style={{ margin: '0 0 12px 0' }} {...props} />,
                    ul: ({ node, ...props }) => <ul style={{ margin: '0 0 12px 0', paddingLeft: '20px' }} {...props} />,
                    ol: ({ node, ...props }) => <ol style={{ margin: '0 0 12px 0', paddingLeft: '20px' }} {...props} />,
                    li: ({ node, ...props }) => <li style={{ marginBottom: '4px' }} {...props} />,
                    code: ({ node, inline, ...props }) => (
                      <code style={{
                        background: 'rgba(0, 0, 0, 0.3)',
                        padding: '2px 4px',
                        borderRadius: 4,
                        fontFamily: 'monospace',
                        fontSize: '0.85em'
                      }} {...props} />
                    )
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>

              {/* References Gallery */}
              {((msg.sources && msg.sources.length > 0) || (msg.fileReferences && msg.fileReferences.length > 0)) && (
                <div style={{
                  marginTop: 12,
                  padding: '16px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 12,
                }}>
                  <div style={{
                    fontSize: '0.75rem',
                    color: 'rgba(255, 255, 255, 0.5)',
                    marginBottom: 12,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}>
                    <span>📚</span>
                    <span>References & Previews</span>
                  </div>
                  
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: 10,
                  }}>
                    {/* Render visual cards for every file reference we extracted */}
                    {msg.fileReferences?.map((fileRef, j) => {
                      const fileName = fileRef.path.split('/').pop()
                      const ext = fileRef.extension
                      
                      return (
                        <div
                          key={`ref-${j}`}
                          onClick={() => {
                            console.log(`Clicking reference: ${fileName}`, { index: j, msgIndex: i, path: fileRef.path });
                            setExpandedPreview(`${i}-${j}`);
                          }}
                          style={{
                            position: 'relative',
                            aspectRatio: '1',
                            background: 'rgba(255, 255, 255, 0.03)',
                            borderRadius: 10,
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            overflow: 'hidden',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            display: 'flex',
                            flexDirection: 'column',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-2px)'
                            e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.5)'
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)'
                            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'
                          }}
                        >
                          <div style={{ flex: 1, position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {fileRef.type === 'image' ? (
                              <img
                                src={`${API}/files/${encodeURIComponent(fileRef.path)}`}
                                alt={fileName}
                                style={{
                                  width: '100%',
                                  height: '100%',
                                  objectFit: 'cover',
                                }}
                              />
                            ) : (
                              <div style={{ fontSize: '2.5rem' }}>
                                {fileRef.type === 'audio' ? '🎙️' : '📄'}
                              </div>
                            )}
                          </div>
                          <div style={{
                            padding: '6px 8px',
                            background: 'rgba(0, 0, 0, 0.6)',
                            backdropFilter: 'blur(4px)',
                            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                          }}>
                            <div style={{
                              fontSize: '0.65rem',
                              color: 'rgba(255, 255, 255, 0.9)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              fontFamily: 'monospace',
                            }}>
                              {fileName}
                            </div>
                          </div>
                          <div style={{
                            position: 'absolute',
                            top: 6,
                            right: 6,
                            padding: '2px 5px',
                            background: 'rgba(102, 126, 234, 0.8)',
                            borderRadius: 4,
                            fontSize: '0.6rem',
                            fontWeight: 700,
                            color: '#fff',
                            textTransform: 'uppercase',
                          }}>
                            {ext}
                          </div>
                        </div>
                      )
                    })}

                    {/* Fallback for sources that didn't get full path references but we want to show them */}
                    {msg.sources?.filter(s => !msg.fileReferences?.some(r => r.path.endsWith(s))).map((source, j) => (
                      <div
                        key={`src-${j}`}
                        style={{
                          aspectRatio: '1',
                          background: 'rgba(255, 255, 255, 0.02)',
                          borderRadius: 10,
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 6,
                          padding: 8,
                          opacity: 0.6,
                        }}
                      >
                        <span style={{ fontSize: '1.5rem' }}>📄</span>
                        <span style={{
                          fontSize: '0.6rem',
                          color: 'rgba(255, 255, 255, 0.5)',
                          textAlign: 'center',
                          wordBreak: 'break-all',
                          fontFamily: 'monospace',
                        }}>
                          {source}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Expanded Preview Modal */}
              {expandedPreview && expandedPreview.startsWith(`${i}-`) && msg.fileReferences && (
                <div
                  onClick={() => {
                    console.log('Closing modal');
                    setExpandedPreview(null);
                  }}
                  style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0, 0, 0, 0.9)',
                    backdropFilter: 'blur(8px)',
                    zIndex: 1000,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 24,
                  }}
                >
                  <div
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      width: '90vw',
                      maxWidth: 800,
                      maxHeight: '90vh',
                      background: 'rgba(30, 30, 30, 0.95)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: 16,
                      overflow: 'hidden',
                      display: 'flex',
                      flexDirection: 'column',
                    }}
                  >
                    {msg.fileReferences.map((fileRef, j) => {
                      if (expandedPreview !== `${i}-${j}`) return null
                      
                      const fileName = fileRef.path.split('/').pop()
                      
                      return (
                        <div key={j} style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                          {/* Modal Header */}
                          <div style={{
                            padding: '16px 20px',
                            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            background: 'rgba(255, 255, 255, 0.02)',
                          }}>
                            <div style={{ minWidth: 0 }}>
                              <div style={{ 
                                fontSize: '0.95rem', 
                                fontWeight: 600, 
                                color: '#fff',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                              }}>
                                {fileName}
                              </div>
                              <div style={{ 
                                fontSize: '0.75rem', 
                                color: 'rgba(255, 255, 255, 0.4)',
                                fontFamily: 'monospace',
                                marginTop: 2
                              }}>
                                {fileRef.path}
                              </div>
                            </div>
                            <button
                              onClick={() => setExpandedPreview(null)}
                              style={{
                                background: 'rgba(255, 255, 255, 0.1)',
                                border: 'none',
                                color: '#fff',
                                width: 32,
                                height: 32,
                                borderRadius: '50%',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '1.2rem',
                              }}
                            >
                              ×
                            </button>
                          </div>

                          {/* Modal Content */}
                          <div style={{ 
                            padding: 24, 
                            overflowY: 'auto',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flex: 1,
                          }}>
                            {fileRef.type === 'image' ? (
                              <img
                                src={`${API}/files/${encodeURIComponent(fileRef.path)}`}
                                alt={fileName}
                                style={{
                                  maxWidth: '100%',
                                  maxHeight: '60vh',
                                  objectFit: 'contain',
                                  borderRadius: 8,
                                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                                }}
                              />
                            ) : fileRef.type === 'audio' ? (
                              <div style={{ width: '100%', maxWidth: 600 }}>
                                <AudioPlayer
                                  audioUrl={`${API}/files/${encodeURIComponent(fileRef.path)}`}
                                  duration={fileRef.metadata?.duration_seconds || 0}
                                />
                                <div style={{
                                  marginTop: 20,
                                  padding: '12px 16px',
                                  background: 'rgba(167, 139, 250, 0.1)',
                                  borderRadius: 8,
                                  border: '1px solid rgba(167, 139, 250, 0.2)',
                                  fontSize: '0.85rem',
                                  color: 'rgba(255, 255, 255, 0.7)',
                                  textAlign: 'center'
                                }}>
                                  🎙️ <strong>Audio File:</strong> {fileRef.metadata?.format || 'Unknown'} format, {fileRef.metadata?.sample_rate || 'N/A'}Hz
                                </div>
                              </div>
                            ) : (
                              <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '4rem', marginBottom: 16 }}>📄</div>
                                <div style={{ fontSize: '1.2rem', color: '#fff' }}>Document File</div>
                                <div style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.5)', marginTop: 8 }}>
                                  Preview not available for {fileRef.extension} files
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Modal Footer */}
                          <div style={{
                            padding: '12px 20px',
                            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                            display: 'flex',
                            justifyContent: 'flex-end',
                            background: 'rgba(255, 255, 255, 0.02)',
                          }}>
                            <button
                              onClick={() => window.open(`${API}/files/${encodeURIComponent(fileRef.path)}`, '_blank')}
                              style={{
                                padding: '8px 16px',
                                borderRadius: 6,
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                background: 'rgba(255, 255, 255, 0.05)',
                                color: '#fff',
                                fontSize: '0.85rem',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8
                              }}
                            >
                              <span>📥</span> Open in New Tab
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{
            display: 'flex',
            gap: 12,
            alignItems: 'flex-start',
          }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <svg viewBox="0 0 56 56" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
                <circle cx="22" cy="22" r="14" fill="none" stroke="white" strokeWidth="2.6" opacity="0.95"/>
                <line x1="22" y1="12" x2="15" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
                <line x1="22" y1="12" x2="29" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
                <line x1="15" y1="28" x2="29" y2="28" stroke="white" strokeWidth="0.8" opacity="0.5"/>
                <circle cx="22" cy="12" r="1.9" fill="white" opacity="0.95"/>
                <circle cx="15" cy="28" r="1.9" fill="white" opacity="0.95"/>
                <circle cx="29" cy="28" r="1.9" fill="white" opacity="0.95"/>
                <line x1="33" y1="33" x2="46" y2="46" stroke="white" strokeWidth="2.6" strokeLinecap="round" opacity="0.95"/>
              </svg>
            </div>
            <div style={{
              background: 'rgba(102, 126, 234, 0.1)',
              border: '1px solid rgba(102, 126, 234, 0.3)',
              borderRadius: 12,
              padding: '12px 16px',
              display: 'flex',
              gap: 8,
              alignItems: 'center',
            }}>
              <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
              <span style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.7)' }}>
                Thinking...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: 16,
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(0, 0, 0, 0.3)',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}>
        {/* Modality scope selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap' }}>
            Search in
          </span>
          {AGENT_MODALITIES.map(m => {
            const active = searchModalities.includes(m.id)
            return (
              <button
                key={m.id}
                onClick={() => toggleModality(m.id)}
                title={m.note ? `${m.label} (${m.note})` : m.label}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  padding: '3px 10px',
                  borderRadius: 99,
                  border: '1px solid',
                  fontSize: '0.72rem',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  transition: 'all 0.15s',
                  background: active ? 'rgba(102,126,234,0.2)' : 'transparent',
                  borderColor: active ? 'rgba(102,126,234,0.6)' : 'rgba(255,255,255,0.15)',
                  color: active ? '#a5b4fc' : 'rgba(255,255,255,0.4)',
                }}
              >
                <span>{m.icon}</span>
                <span>{m.label}</span>
                {m.note && active && (
                  <span style={{ opacity: 0.6, fontSize: '0.65rem' }}>({m.note})</span>
                )}
              </button>
            )
          })}
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything about your documents..."
            disabled={loading}
            style={{
              flex: 1,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 8,
              color: '#fff',
              fontSize: '0.9rem',
              padding: '12px 16px',
              fontFamily: 'inherit',
              resize: 'none',
              minHeight: 44,
              maxHeight: 120,
              outline: 'none',
            }}
            rows={1}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            style={{
              padding: '0 20px',
              borderRadius: 8,
              border: 'none',
              background: input.trim() && !loading
                ? 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)'
                : 'rgba(255, 255, 255, 0.1)',
              color: '#fff',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
              fontFamily: 'inherit',
              opacity: input.trim() && !loading ? 1 : 0.5,
              transition: 'all 0.2s',
            }}
          >
            Send
          </button>
        </div>
        <div style={{
          marginTop: 8,
          fontSize: '0.75rem',
          color: 'rgba(255, 255, 255, 0.4)',
        }}>
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  )
}
