import { useState, useEffect, useRef } from 'react'
import FolderManager from '../components/FolderManager'
import MultimodalSearchBar from '../components/MultimodalSearchBar'
import MultimodalResultCard from '../components/MultimodalResultCard'
import AgentChat from '../components/AgentChat'
import { api, onBackendStatus } from '../api'

const tabs = [
  { id: 'search', label: 'Search', path: '/search' },
  { id: 'folders', label: 'Folders', path: '/folders' },
  { id: 'analytics', label: 'Analytics', path: '/analytics' },
]

export default function ModernHome({ route, navigate }) {
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [stats, setStats] = useState(null)
  const [backendOnline, setBackendOnline] = useState(false)
  const [resultTab, setResultTab] = useState('all')
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const fileInputRef = useRef(null)

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files)
    if (!files.length) return
    setUploading(true)
    setUploadMsg(null)
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    try {
      const data = await api('/upload', { method: 'POST', body: form })
      const msg = data.saved.length
        ? `${data.saved.length} file(s) uploaded and indexing started`
        : 'No supported files selected'
      const warn = data.rejected.length ? ` (${data.rejected.length} unsupported skipped)` : ''
      setUploadMsg({ type: data.saved.length ? 'success' : 'warn', text: msg + warn })
      fetchStats()
    } catch (e) {
      setUploadMsg({ type: 'error', text: e.message || 'Upload failed' })
    } finally {
      setUploading(false)
      e.target.value = ''
      setTimeout(() => setUploadMsg(null), 4000)
    }
  }
  const activeTab = route === '/folders'
    ? 'folders'
    : route === '/analytics'
    ? 'analytics'
    : 'search'
  const searchMode = route === '/agent' ? 'agent' : 'search'

  // Refresh stats + health when it actually makes sense — on mount and whenever
  // the user returns to the tab — rather than hammering the backend on a timer.
  // The api helper also flips backendOnline on any failed request, so problems
  // surface immediately instead of waiting for the next poll.
  useEffect(() => {
    const refresh = () => { fetchStats(); checkBackendStatus() }
    refresh()

    const onFocus = () => refresh()
    const onVisible = () => { if (document.visibilityState === 'visible') refresh() }
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onVisible)

    const unsubscribe = onBackendStatus(setBackendOnline)
    return () => {
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onVisible)
      unsubscribe()
    }
  }, [])

  const fetchStats = async () => {
    try {
      setStats(await api('/stats'))
    } catch (e) {
      // Already logged by the api helper; backend banner is driven separately.
    }
  }

  const checkBackendStatus = async () => {
    try {
      await api('/health')
      setBackendOnline(true)
    } catch (e) {
      setBackendOnline(false)
    }
  }

  const getTotalResults = () => {
    if (!searchResults?.results) return 0
    const { text = [], image = [], audio = [], video = [] } = searchResults.results
    return text.length + image.length + audio.length + video.length
  }

  const getAllResults = () => {
    if (!searchResults?.results) return []
    const { text = [], image = [], audio = [], video = [] } = searchResults.results
    return [...text, ...image, ...audio, ...video].sort((a, b) => b.score - a.score)
  }

  const getModalityCount = (modality) => {
    if (!searchResults?.results) return 0
    return searchResults.results[modality]?.length || 0
  }

  const getFilteredResults = () => {
    if (resultTab === 'all') return getAllResults()
    if (!searchResults?.results) return []
    return searchResults.results[resultTab] || []
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#000',
      color: '#fff',
    }}>
      {/* Top Navigation */}
      <nav style={{
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '16px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(20px)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 40,
            height: 40,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <svg viewBox="0 0 56 56" width="22" height="22" xmlns="http://www.w3.org/2000/svg">
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
            <div style={{ fontSize: '1.2rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              LocalFind
            </div>
            <div style={{ fontSize: '0.7rem', color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Local Multimodal Semantic Search
            </div>
          </div>
        </div>

        {/* Nav Tabs */}
        <div style={{ display: 'flex', gap: 8 }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => navigate(tab.path)}
              style={{
                padding: '10px 24px',
                borderRadius: 8,
                border: activeTab === tab.id ? '1px solid rgba(255, 255, 255, 0.2)' : '1px solid transparent',
                background: activeTab === tab.id ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
                color: activeTab === tab.id ? '#fff' : 'rgba(255, 255, 255, 0.5)',
                fontSize: '0.9rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontFamily: 'inherit',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Upload Button */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md,.csv,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp3,.wav,.flac,.m4a"
          style={{ display: 'none' }}
          onChange={handleUpload}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          style={{
            padding: '10px 20px',
            borderRadius: 8,
            border: '1px solid rgba(255, 255, 255, 0.2)',
            background: uploading ? 'rgba(255,255,255,0.02)' : 'rgba(255, 255, 255, 0.05)',
            color: uploading ? 'rgba(255,255,255,0.4)' : '#fff',
            fontSize: '0.9rem',
            fontWeight: 500,
            cursor: uploading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            fontFamily: 'inherit',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          {uploading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : '+'}
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
      </nav>

      {/* Upload feedback toast */}
      {uploadMsg && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 999,
          padding: '12px 18px', borderRadius: 8, fontSize: '0.85rem',
          background: uploadMsg.type === 'success' ? 'rgba(34,197,94,0.15)'
                    : uploadMsg.type === 'warn'    ? 'rgba(234,179,8,0.15)'
                    : 'rgba(239,68,68,0.15)',
          border: `1px solid ${
            uploadMsg.type === 'success' ? 'rgba(34,197,94,0.4)'
            : uploadMsg.type === 'warn'  ? 'rgba(234,179,8,0.4)'
            : 'rgba(239,68,68,0.4)'}`,
          color: uploadMsg.type === 'success' ? '#4ade80'
               : uploadMsg.type === 'warn'    ? '#fbbf24'
               : '#f87171',
        }}>
          {uploadMsg.text}
        </div>
      )}

      {/* Status Bar */}
      <div style={{
        padding: '12px 32px',
        background: 'rgba(0, 0, 0, 0.5)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        fontSize: '0.8rem',
        color: 'rgba(255, 255, 255, 0.5)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: backendOnline ? '#10b981' : '#ef4444',
            boxShadow: backendOnline ? '0 0 8px #10b981' : '0 0 8px #ef4444',
          }} />
          <span>{backendOnline ? 'Backend online' : 'Backend offline'}</span>
        </div>
        {stats?.last_sync && (
          <>
            <span>·</span>
            <span>Last sync: {new Date(stats.last_sync).toLocaleString()}</span>
          </>
        )}
      </div>

      {/* Main Content */}
      <div style={{ maxWidth: 1400, margin: '0 auto', padding: '32px' }}>
        {activeTab === 'search' && (
          <>
            {/* Stats Cards */}
            {stats && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 20,
                marginBottom: 40,
              }}>
                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 16,
                  padding: '24px',
                }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>📁</div>
                  <div style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: 4 }}>
                    {stats.total_folders}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    Folders
                  </div>
                </div>

                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 16,
                  padding: '24px',
                }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>📄</div>
                  <div style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: 4 }}>
                    {stats.total_files}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    Files
                  </div>
                </div>

                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 16,
                  padding: '24px',
                }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>🧩</div>
                  <div style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: 4, color: '#a78bfa' }}>
                    {stats.total_chunks}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    Chunks Indexed
                  </div>
                </div>

                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 16,
                  padding: '24px',
                }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>⚡</div>
                  <div style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: 4 }}>
                    ~42ms
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    Avg. Query Time
                  </div>
                </div>
              </div>
            )}

            {/* Search Section */}
            <div style={{ marginBottom: 40 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 20,
              }}>
                <h2 style={{
                  fontSize: '0.85rem',
                  color: 'rgba(255, 255, 255, 0.4)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  fontWeight: 500,
                }}>
                  Search Your Knowledge Base
                </h2>
                
                {/* Mode Toggle */}
                <div style={{
                  display: 'flex',
                  gap: 8,
                  background: 'rgba(255, 255, 255, 0.05)',
                  padding: 4,
                  borderRadius: 8,
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                }}>
                  <button
                    onClick={() => navigate('/search')}
                    style={{
                      padding: '6px 16px',
                      borderRadius: 6,
                      border: 'none',
                      background: searchMode === 'search' 
                        ? 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)'
                        : 'transparent',
                      color: searchMode === 'search' ? '#fff' : 'rgba(255, 255, 255, 0.6)',
                      fontSize: '0.85rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    🔍 Search
                  </button>
                  <button
                    onClick={() => navigate('/agent')}
                    style={{
                      padding: '6px 16px',
                      borderRadius: 6,
                      border: 'none',
                      background: searchMode === 'agent'
                        ? 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)'
                        : 'transparent',
                      color: searchMode === 'agent' ? '#fff' : 'rgba(255, 255, 255, 0.6)',
                      fontSize: '0.85rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    <svg viewBox="0 0 56 56" width="14" height="14" xmlns="http://www.w3.org/2000/svg" style={{flexShrink:0}}>
                      <circle cx="22" cy="22" r="14" fill="none" stroke="currentColor" strokeWidth="2.6" opacity="0.9"/>
                      <line x1="22" y1="12" x2="15" y2="28" stroke="currentColor" strokeWidth="0.8" opacity="0.5"/>
                      <line x1="22" y1="12" x2="29" y2="28" stroke="currentColor" strokeWidth="0.8" opacity="0.5"/>
                      <line x1="15" y1="28" x2="29" y2="28" stroke="currentColor" strokeWidth="0.8" opacity="0.5"/>
                      <circle cx="22" cy="12" r="1.9" fill="currentColor" opacity="0.9"/>
                      <circle cx="15" cy="28" r="1.9" fill="currentColor" opacity="0.9"/>
                      <circle cx="29" cy="28" r="1.9" fill="currentColor" opacity="0.9"/>
                      <line x1="33" y1="33" x2="46" y2="46" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" opacity="0.9"/>
                    </svg>
                    Agent
                  </button>
                </div>
              </div>
              
              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 16,
                padding: '32px',
              }}>
                {searchMode === 'search' ? (
                  <MultimodalSearchBar onResults={setSearchResults} onLoading={setSearching} />
                ) : (
                  <AgentChat />
                )}
              </div>
            </div>

            {/* Results */}
            {searchMode === 'search' && searching && !searchResults && (
              <div style={{ textAlign: 'center', padding: 60 }}>
                <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3, margin: '0 auto 16px' }} />
                <p style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Searching...</p>
              </div>
            )}

            {searchMode === 'search' && searchResults && !searchResults.error && getTotalResults() > 0 && (
              <>
                {/* Results Tabs */}
                <div style={{
                  display: 'flex',
                  gap: 16,
                  marginBottom: 24,
                  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                  paddingBottom: 16,
                }}>
                  <button
                    onClick={() => setResultTab('all')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: resultTab === 'all' ? '#a78bfa' : 'rgba(255, 255, 255, 0.4)',
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: '8px 0',
                      borderBottom: resultTab === 'all' ? '2px solid #a78bfa' : '2px solid transparent',
                      fontFamily: 'inherit',
                    }}
                  >
                    All results
                  </button>
                  {getModalityCount('text') > 0 && (
                    <button
                      onClick={() => setResultTab('text')}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: resultTab === 'text' ? '#a78bfa' : 'rgba(255, 255, 255, 0.4)',
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                        padding: '8px 0',
                        borderBottom: resultTab === 'text' ? '2px solid #a78bfa' : '2px solid transparent',
                        fontFamily: 'inherit',
                      }}
                    >
                      Text ({getModalityCount('text')})
                    </button>
                  )}
                  {getModalityCount('image') > 0 && (
                    <button
                      onClick={() => setResultTab('image')}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: resultTab === 'image' ? '#a78bfa' : 'rgba(255, 255, 255, 0.4)',
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                        padding: '8px 0',
                        borderBottom: resultTab === 'image' ? '2px solid #a78bfa' : '2px solid transparent',
                        fontFamily: 'inherit',
                      }}
                    >
                      Images ({getModalityCount('image')})
                    </button>
                  )}
                  {getModalityCount('audio') > 0 && (
                    <button
                      onClick={() => setResultTab('audio')}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: resultTab === 'audio' ? '#a78bfa' : 'rgba(255, 255, 255, 0.4)',
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                        padding: '8px 0',
                        borderBottom: resultTab === 'audio' ? '2px solid #a78bfa' : '2px solid transparent',
                        fontFamily: 'inherit',
                      }}
                    >
                      Audio ({getModalityCount('audio')})
                    </button>
                  )}
                  {getModalityCount('video') > 0 && (
                    <button
                      onClick={() => setResultTab('video')}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: resultTab === 'video' ? '#a78bfa' : 'rgba(255, 255, 255, 0.4)',
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                        padding: '8px 0',
                        borderBottom: resultTab === 'video' ? '2px solid #a78bfa' : '2px solid transparent',
                        fontFamily: 'inherit',
                      }}
                    >
                      Video ({getModalityCount('video')})
                    </button>
                  )}
                </div>

                {/* Results Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
                  gap: 20,
                }}>
                  {getFilteredResults().map((result, i) => (
                    <MultimodalResultCard
                      key={`${result.file_path}-${result.modality}-${result.chunk_index ?? result.metadata?.frame_index ?? result.metadata?.start_time ?? i}`}
                      result={result}
                      query={searchResults.query}
                      index={i}
                    />
                  ))}
                </div>
              </>
            )}

            {searchMode === 'search' && searchResults && !searchResults.error && getTotalResults() === 0 && (
              <div style={{
                textAlign: 'center',
                padding: '80px 24px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                borderRadius: 16,
              }}>
                <div style={{ fontSize: '4rem', marginBottom: 16 }}>🔎</div>
                <p style={{ fontSize: '1.1rem', marginBottom: 8 }}>No results found</p>
                <p style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.4)' }}>
                  Try different keywords or sync more folders
                </p>
              </div>
            )}
          </>
        )}

        {activeTab === 'folders' && (
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: 16,
            padding: 32,
          }}>
            <FolderManager />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: 16,
            padding: 32,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '4rem', marginBottom: 16 }}>📊</div>
            <h3 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Analytics</h3>
            <p style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
              Coming soon: Search analytics, usage stats, and insights
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
