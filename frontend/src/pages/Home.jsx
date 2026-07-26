import { useState } from 'react'
import StatsPanel from '../components/StatsPanel'
import FolderManager from '../components/FolderManager'
import SearchBar from '../components/SearchBar'
import ResultCard from '../components/ResultCard'

export default function Home() {
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [activeTab, setActiveTab] = useState('search') // 'search' | 'folders'

  const tabs = [
    { id: 'search',  label: '🔍 Search' },
    { id: 'folders', label: '📁 Folders' },
  ]

  return (
    <div style={{
      minHeight: '100vh',
      padding: '0 0 80px',
      maxWidth: 820,
      margin: '0 auto',
    }}>
      {/* ── Top header ─────────────────────────────────────────────── */}
      <header style={{
        padding: '40px 24px 0',
        marginBottom: 32,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 14,
            background: 'linear-gradient(135deg, var(--accent-1), var(--accent-2))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.5rem',
            boxShadow: 'var(--shadow-glow)',
          }}>🧠</div>
          <div>
            <h1 style={{ fontSize: '1.6rem', background: 'linear-gradient(135deg, #a78bfa, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              LocalFind
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 1 }}>
              Local · Semantic · Private
            </p>
          </div>
        </div>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: 520 }}>
          Search your documents by <em>what they contain</em>, not their filenames.
          Powered by Ollama embeddings and ChromaDB — nothing leaves your machine.
        </p>
      </header>

      {/* ── Stats ──────────────────────────────────────────────────── */}
      <div style={{ padding: '0 24px', marginBottom: 28 }}>
        <StatsPanel />
      </div>

      {/* ── Tab bar ────────────────────────────────────────────────── */}
      <div style={{ padding: '0 24px', marginBottom: 20 }}>
        <div style={{
          display: 'inline-flex',
          background: 'var(--bg-glass)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          padding: 3,
          gap: 2,
        }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 20px',
                borderRadius: 7,
                border: 'none',
                fontFamily: 'Inter, sans-serif',
                fontSize: '0.85rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.15s',
                background: activeTab === tab.id
                  ? 'linear-gradient(135deg, var(--accent-1), var(--accent-2))'
                  : 'transparent',
                color: activeTab === tab.id ? '#fff' : 'var(--text-muted)',
                boxShadow: activeTab === tab.id ? '0 2px 10px var(--accent-glow)' : 'none',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Main content ────────────────────────────────────────────── */}
      <main style={{ padding: '0 24px' }}>

        {/* Search tab */}
        {activeTab === 'search' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Search bar card */}
            <div className="card">
              <SearchBar onResults={setSearchResults} onLoading={setSearching} />
            </div>

            {/* Results area */}
            {searching && !searchResults && (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
                <span className="spinner" style={{ width: 28, height: 28, borderTopColor: 'var(--accent-2)', borderWidth: 3 }} />
              </div>
            )}

            {searchResults && searchResults.error && (
              <div style={{
                background: 'var(--danger-light)', border: '1px solid rgba(239,68,68,0.25)',
                borderRadius: 'var(--radius-md)', padding: '14px 18px',
                color: 'var(--danger)', fontSize: '0.88rem',
              }}>
                ⚠ {searchResults.error}
              </div>
            )}

            {searchResults && !searchResults.error && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Result count header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    {searchResults.results.length > 0
                      ? <>{searchResults.results.length} result{searchResults.results.length !== 1 ? 's' : ''} for <em style={{ color: 'var(--text-secondary)' }}>"{searchResults.query}"</em></>
                      : <>No results for <em style={{ color: 'var(--text-secondary)' }}>"{searchResults.query}"</em></>
                    }
                  </span>
                </div>

                {searchResults.results.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon">🔎</span>
                    <span style={{ fontSize: '0.88rem' }}>Nothing found. Try different keywords or sync more folders.</span>
                  </div>
                ) : (
                  searchResults.results.map((result, i) => (
                    <ResultCard
                      key={`${result.file_path}-${result.chunk_index}`}
                      result={result}
                      query={searchResults.query}
                      index={i}
                    />
                  ))
                )}
              </div>
            )}

            {/* Initial empty state */}
            {!searchResults && !searching && (
              <div className="empty-state" style={{ padding: '60px 24px' }}>
                <span className="empty-icon">✨</span>
                <span style={{ fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                  Start typing to search your documents
                </span>
                <span style={{ fontSize: '0.8rem' }}>
                  Searches by meaning, not just keywords
                </span>
              </div>
            )}
          </div>
        )}

        {/* Folders tab */}
        {activeTab === 'folders' && (
          <FolderManager />
        )}
      </main>
    </div>
  )
}
