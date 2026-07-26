import { useState, useRef, useEffect } from 'react'

const API = '/api'

export default function SearchBar({ onResults, onLoading }) {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [searching, setSearching] = useState(false)
  const debounceRef = useRef(null)

  const doSearch = async (q, k) => {
    if (!q.trim()) {
      onResults(null)
      return
    }
    setSearching(true)
    onLoading(true)
    try {
      const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}&top_k=${k}`)
      if (res.ok) {
        const data = await res.json()
        onResults(data)
      } else {
        onResults({ query: q, results: [], error: 'Search failed' })
      }
    } catch (_) {
      onResults({ query: q, results: [], error: 'Cannot connect to backend' })
    } finally {
      setSearching(false)
      onLoading(false)
    }
  }

  const handleChange = (e) => {
    const val = e.target.value
    setQuery(val)
    clearTimeout(debounceRef.current)
    if (!val.trim()) { onResults(null); return }
    debounceRef.current = setTimeout(() => doSearch(val, topK), 450)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      clearTimeout(debounceRef.current)
      doSearch(query, topK)
    }
    if (e.key === 'Escape') {
      setQuery('')
      onResults(null)
    }
  }

  const clearSearch = () => {
    setQuery('')
    onResults(null)
    clearTimeout(debounceRef.current)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Search input */}
      <div style={{ position: 'relative' }}>
        <span style={{
          position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
          fontSize: '1rem', opacity: 0.4, pointerEvents: 'none',
        }}>🔍</span>

        <input
          id="search-input"
          className="input"
          placeholder="Search your documents… e.g. 'quarterly revenue', 'king and kingdom'"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          style={{
            paddingLeft: 42,
            paddingRight: query ? 100 : 14,
            fontSize: '1rem',
            height: 52,
            fontFamily: 'Inter, sans-serif',
          }}
          autoFocus
        />

        <div style={{
          position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          {searching && <span className="spinner" style={{ borderTopColor: 'var(--accent-2)' }} />}
          {query && !searching && (
            <button
              id="clear-search-btn"
              onClick={clearSearch}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-muted)', fontSize: '1rem', lineHeight: 1,
                padding: 2,
              }}
            >✕</button>
          )}
        </div>
      </div>

      {/* Options row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          Results
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          {[3, 5, 10].map(n => (
            <button
              key={n}
              id={`top-k-btn-${n}`}
              onClick={() => { setTopK(n); if (query) doSearch(query, n) }}
              style={{
                padding: '4px 12px',
                borderRadius: 99,
                border: '1px solid',
                fontSize: '0.78rem',
                cursor: 'pointer',
                fontFamily: 'inherit',
                transition: 'all 0.15s',
                background: topK === n ? 'var(--accent-light)' : 'transparent',
                borderColor: topK === n ? 'var(--accent-1)' : 'var(--border)',
                color: topK === n ? 'var(--accent-2)' : 'var(--text-muted)',
              }}
            >{n}</button>
          ))}
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
          Press <kbd style={{
            background: 'var(--bg-glass-hover)', border: '1px solid var(--border)',
            borderRadius: 4, padding: '1px 5px', fontSize: '0.72rem',
          }}>Enter</kbd> to search
        </span>
      </div>
    </div>
  )
}
