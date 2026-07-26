import { useState } from 'react'
import StatsPanel from '../components/StatsPanel'
import FolderManager from '../components/FolderManager'
import MultimodalSearchBar from '../components/MultimodalSearchBar'
import MultimodalResultCard from '../components/MultimodalResultCard'

export default function MultimodalHome() {
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [activeTab, setActiveTab] = useState('search')
  const [selectedResult, setSelectedResult] = useState(null)

  const tabs = [
    { id: 'search',  label: '🔍 Search', icon: '🔍' },
    { id: 'folders', label: '📁 Folders', icon: '📁' },
  ]

  const getTotalResults = () => {
    if (!searchResults?.results) return 0
    const { text = [], image = [], audio = [] } = searchResults.results
    return text.length + image.length + audio.length
  }

  const getAllResults = () => {
    if (!searchResults?.results) return []
    const { text = [], image = [], audio = [] } = searchResults.results
    return [...text, ...image, ...audio].sort((a, b) => b.score - a.score)
  }

  const getModalityCount = (modality) => {
    if (!searchResults?.results) return 0
    return searchResults.results[modality]?.length || 0
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Animated background gradient orbs */}
      <div style={{
        position: 'fixed',
        top: '-50%',
        left: '-50%',
        width: '200%',
        height: '200%',
        background: 'radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.1) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(99, 102, 241, 0.1) 0%, transparent 50%)',
        animation: 'rotate 30s linear infinite',
        pointerEvents: 'none',
      }} />

      <div style={{
        position: 'relative',
        zIndex: 1,
        maxWidth: 1200,
        margin: '0 auto',
        padding: '0 24px 80px',
      }}>
        {/* Header */}
        <header style={{
          padding: '48px 0 40px',
          textAlign: 'center',
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 16,
            marginBottom: 16,
            background: 'rgba(255, 255, 255, 0.03)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 24,
            padding: '12px 32px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          }}>
            <div style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.8rem',
              boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
            }}>
              🧠
            </div>
            <div style={{ textAlign: 'left' }}>
              <h1 style={{
                fontSize: '2rem',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                margin: 0,
                letterSpacing: '-0.02em',
              }}>
                LocalFind
              </h1>
              <p style={{
                fontSize: '0.85rem',
                color: 'rgba(255, 255, 255, 0.5)',
                margin: '4px 0 0',
                fontWeight: 500,
              }}>
                Multimodal Semantic Search
              </p>
            </div>
          </div>

          <p style={{
            color: 'rgba(255, 255, 255, 0.7)',
            fontSize: '1rem',
            maxWidth: 600,
            margin: '0 auto',
            lineHeight: 1.6,
          }}>
            Search across <strong style={{ color: '#667eea' }}>text</strong>, <strong style={{ color: '#f472b6' }}>images</strong>, and <strong style={{ color: '#a78bfa' }}>audio</strong> using natural language
          </p>
        </header>

        {/* Stats */}
        <div style={{ marginBottom: 32 }}>
          <StatsPanel />
        </div>

        {/* Tabs */}
        <div style={{ marginBottom: 32, display: 'flex', justifyContent: 'center' }}>
          <div style={{
            display: 'inline-flex',
            background: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 16,
            padding: 4,
            gap: 4,
          }}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: '12px 28px',
                  borderRadius: 12,
                  border: 'none',
                  fontFamily: 'Inter, sans-serif',
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                  background: activeTab === tab.id
                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                    : 'transparent',
                  color: activeTab === tab.id ? '#fff' : 'rgba(255, 255, 255, 0.6)',
                  boxShadow: activeTab === tab.id ? '0 4px 16px rgba(102, 126, 234, 0.4)' : 'none',
                  transform: activeTab === tab.id ? 'translateY(-1px)' : 'none',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <main>
          {activeTab === 'search' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
              {/* Search Bar */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.05)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 24,
                padding: 32,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
              }}>
                <MultimodalSearchBar onResults={setSearchResults} onLoading={setSearching} />
              </div>

              {/* Loading */}
              {searching && !searchResults && (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 16,
                  padding: 60,
                }}>
                  <div className="spinner" style={{
                    width: 40,
                    height: 40,
                    borderWidth: 4,
                    borderTopColor: '#667eea',
                  }} />
                  <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '0.95rem' }}>
                    Searching across all modalities...
                  </p>
                </div>
              )}

              {/* Error */}
              {searchResults && searchResults.error && (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.1)',
                  backdropFilter: 'blur(20px)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 16,
                  padding: 20,
                  color: '#fca5a5',
                  fontSize: '0.95rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                }}>
                  <span style={{ fontSize: '1.5rem' }}>⚠️</span>
                  <span>{searchResults.error}</span>
                </div>
              )}

              {/* Results */}
              {searchResults && !searchResults.error && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                  {/* Results Header */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 16,
                    padding: '0 8px',
                  }}>
                    <div>
                      <h2 style={{
                        fontSize: '1.5rem',
                        fontWeight: 700,
                        color: '#fff',
                        margin: '0 0 8px',
                      }}>
                        {getTotalResults() > 0 ? (
                          <>Found {getTotalResults()} result{getTotalResults() !== 1 ? 's' : ''}</>
                        ) : (
                          <>No results found</>
                        )}
                      </h2>
                      <p style={{
                        fontSize: '0.9rem',
                        color: 'rgba(255, 255, 255, 0.5)',
                        margin: 0,
                      }}>
                        for "<span style={{ color: '#667eea', fontWeight: 600 }}>{searchResults.query}</span>"
                      </p>
                    </div>

                    {getTotalResults() > 0 && (
                      <div style={{
                        display: 'flex',
                        gap: 12,
                        flexWrap: 'wrap',
                      }}>
                        {getModalityCount('text') > 0 && (
                          <div style={{
                            background: 'rgba(52, 211, 153, 0.1)',
                            border: '1px solid rgba(52, 211, 153, 0.3)',
                            borderRadius: 12,
                            padding: '8px 16px',
                            fontSize: '0.85rem',
                            color: '#6ee7b7',
                            fontWeight: 600,
                          }}>
                            📄 {getModalityCount('text')} text
                          </div>
                        )}
                        {getModalityCount('image') > 0 && (
                          <div style={{
                            background: 'rgba(244, 114, 182, 0.1)',
                            border: '1px solid rgba(244, 114, 182, 0.3)',
                            borderRadius: 12,
                            padding: '8px 16px',
                            fontSize: '0.85rem',
                            color: '#f9a8d4',
                            fontWeight: 600,
                          }}>
                            🖼️ {getModalityCount('image')} image{getModalityCount('image') !== 1 ? 's' : ''}
                          </div>
                        )}
                        {getModalityCount('audio') > 0 && (
                          <div style={{
                            background: 'rgba(167, 139, 250, 0.1)',
                            border: '1px solid rgba(167, 139, 250, 0.3)',
                            borderRadius: 12,
                            padding: '8px 16px',
                            fontSize: '0.85rem',
                            color: '#c4b5fd',
                            fontWeight: 600,
                          }}>
                            🎵 {getModalityCount('audio')} audio
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Results Grid */}
                  {getTotalResults() === 0 ? (
                    <div style={{
                      textAlign: 'center',
                      padding: '80px 24px',
                      background: 'rgba(255, 255, 255, 0.03)',
                      backdropFilter: 'blur(20px)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: 24,
                    }}>
                      <div style={{ fontSize: '4rem', marginBottom: 16 }}>🔎</div>
                      <p style={{ fontSize: '1.1rem', color: 'rgba(255, 255, 255, 0.7)', marginBottom: 8 }}>
                        No results found
                      </p>
                      <p style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.5)' }}>
                        Try different keywords or sync more folders
                      </p>
                    </div>
                  ) : (
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))',
                      gap: 20,
                    }}>
                      {getAllResults().map((result, i) => (
                        <MultimodalResultCard
                          key={`${result.file_path}-${result.chunk_index || 0}-${result.modality}`}
                          result={result}
                          query={searchResults.query}
                          index={i}
                          onSelect={() => setSelectedResult(result)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Empty State */}
              {!searchResults && !searching && (
                <div style={{
                  textAlign: 'center',
                  padding: '100px 24px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  backdropFilter: 'blur(20px)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: 24,
                }}>
                  <div style={{ fontSize: '5rem', marginBottom: 24 }}>✨</div>
                  <h3 style={{
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: '#fff',
                    marginBottom: 12,
                  }}>
                    Start searching
                  </h3>
                  <p style={{
                    fontSize: '1rem',
                    color: 'rgba(255, 255, 255, 0.6)',
                    marginBottom: 32,
                    maxWidth: 500,
                    margin: '0 auto 32px',
                  }}>
                    Search by meaning across text documents, images, and audio files
                  </p>
                  <div style={{
                    display: 'flex',
                    gap: 16,
                    justifyContent: 'center',
                    flexWrap: 'wrap',
                    fontSize: '0.85rem',
                    color: 'rgba(255, 255, 255, 0.4)',
                  }}>
                    <span>Try: <strong style={{ color: '#667eea' }}>"sunset beach"</strong></span>
                    <span>·</span>
                    <span><strong style={{ color: '#f472b6' }}>"jazz piano"</strong></span>
                    <span>·</span>
                    <span><strong style={{ color: '#a78bfa' }}>"machine learning"</strong></span>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'folders' && (
            <div style={{
              background: 'rgba(255, 255, 255, 0.05)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 24,
              padding: 32,
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            }}>
              <FolderManager />
            </div>
          )}
        </main>
      </div>

      {/* CSS Animation */}
      <style>{`
        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
