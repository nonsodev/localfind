import { useState, useRef } from 'react'
import { api } from '../api'

const MODALITY_OPTIONS = [
  { id: 'all', label: 'All', icon: '✨' },
  { id: 'text', label: 'Text', icon: '📄' },
  { id: 'image', label: 'Images', icon: '🖼️' },
  { id: 'audio', label: 'Audio', icon: '🎵' },
  { id: 'video', label: 'Video', icon: '🎬' },
]

export default function MultimodalSearchBar({ onResults, onLoading }) {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [modalities, setModalities] = useState('all')
  const [groupBySource, setGroupBySource] = useState(false)
  const [videoSpeech, setVideoSpeech] = useState(false)
  const [searching, setSearching] = useState(false)
  const debounceRef = useRef(null)

  const doSearch = async (q, k, mods, group = groupBySource, speech = videoSpeech) => {
    if (!q.trim()) {
      onResults(null)
      return
    }
    setSearching(true)
    onLoading(true)
    try {
      let path = `/search?q=${encodeURIComponent(q)}&top_k=${k}`
      // Add modality filter if not "all"
      if (mods !== 'all') {
        path += `&modalities=${mods}`
      }
      // "One result per file" diversity filter (opt-in)
      if (group) {
        path += `&group_by_source=true`
      }
      // Search what's SAID in videos too, not just what's shown (opt-in)
      if (speech) {
        path += `&include_video_speech=true`
      }
      onResults(await api(path))
    } catch (e) {
      onResults({ query: q, results: {}, error: e.message || 'Search failed' })
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
    debounceRef.current = setTimeout(() => doSearch(val, topK, modalities), 450)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      clearTimeout(debounceRef.current)
      doSearch(query, topK, modalities)
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

  const handleModalityChange = (mod) => {
    setModalities(mod)
    if (query.trim()) {
      doSearch(query, topK, mod)
    }
  }

  const handleGroupToggle = () => {
    const next = !groupBySource
    setGroupBySource(next)
    if (query.trim()) {
      doSearch(query, topK, modalities, next)
    }
  }

  const handleVideoSpeechToggle = () => {
    const next = !videoSpeech
    setVideoSpeech(next)
    if (query.trim()) {
      doSearch(query, topK, modalities, groupBySource, next)
    }
  }

  // The speech toggle only matters when video results are in play.
  const videoInScope = modalities === 'all' || modalities === 'video'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Search input */}
      <div style={{ position: 'relative' }}>
        <span style={{
          position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
          fontSize: '1rem', opacity: 0.4, pointerEvents: 'none',
        }}>🔍</span>

        <input
          id="search-input"
          className="input"
          placeholder="Search across text, images, audio, and video… e.g. 'sunset beach', 'the revenue slide'"
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

      {/* Modality filters */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          Search in
        </label>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {MODALITY_OPTIONS.map(opt => (
            <button
              key={opt.id}
              id={`modality-btn-${opt.id}`}
              onClick={() => handleModalityChange(opt.id)}
              style={{
                padding: '6px 14px',
                borderRadius: 99,
                border: '1px solid',
                fontSize: '0.78rem',
                cursor: 'pointer',
                fontFamily: 'inherit',
                transition: 'all 0.15s',
                background: modalities === opt.id ? 'var(--accent-light)' : 'transparent',
                borderColor: modalities === opt.id ? 'var(--accent-1)' : 'var(--border)',
                color: modalities === opt.id ? 'var(--accent-2)' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span>{opt.icon}</span>
              <span>{opt.label}</span>
            </button>
          ))}
        </div>

        {/* Search what's said in videos, not just what's shown */}
        {videoInScope && (
          <button
            id="video-speech-btn"
            onClick={handleVideoSpeechToggle}
            title="Also search what's SAID in videos (the spoken transcript), not just what's shown on screen."
            style={{
              marginLeft: 'auto',
              padding: '6px 14px',
              borderRadius: 99,
              border: '1px solid',
              fontSize: '0.78rem',
              cursor: 'pointer',
              fontFamily: 'inherit',
              transition: 'all 0.15s',
              background: videoSpeech ? 'var(--accent-light)' : 'transparent',
              borderColor: videoSpeech ? 'var(--accent-1)' : 'var(--border)',
              color: videoSpeech ? 'var(--accent-2)' : 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              whiteSpace: 'nowrap',
            }}
          >
            <span>🗣️</span>
            <span>Speech in videos</span>
          </button>
        )}

        {/* One-result-per-file diversity filter */}
        <button
          id="group-by-source-btn"
          onClick={handleGroupToggle}
          title="Show each file only once, at its best-matching moment — so one video/podcast/document can't fill every slot."
          style={{
            marginLeft: videoInScope ? 0 : 'auto',
            padding: '6px 14px',
            borderRadius: 99,
            border: '1px solid',
            fontSize: '0.78rem',
            cursor: 'pointer',
            fontFamily: 'inherit',
            transition: 'all 0.15s',
            background: groupBySource ? 'var(--accent-light)' : 'transparent',
            borderColor: groupBySource ? 'var(--accent-1)' : 'var(--border)',
            color: groupBySource ? 'var(--accent-2)' : 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            whiteSpace: 'nowrap',
          }}
        >
          <span>{groupBySource ? '☑' : '☐'}</span>
          <span>One result per file</span>
        </button>
      </div>

      {/* Results count options */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          Results per type
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          {[3, 5, 10].map(n => (
            <button
              key={n}
              id={`top-k-btn-${n}`}
              onClick={() => { setTopK(n); if (query) doSearch(query, n, modalities) }}
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
