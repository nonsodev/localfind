import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

export default function FolderManager() {
  const [folders, setFolders] = useState([])
  const [pathInput, setPathInput] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')
  const [backendDown, setBackendDown] = useState(false)

  const fetchFolders = useCallback(async () => {
    try {
      setFolders(await api('/folders'))
      setBackendDown(false)
    } catch (e) {
      // Only flag as "backend down" for actual network failures (status 0).
      // HTTP errors (4xx/5xx) mean the backend is reachable but something else
      // went wrong — show the real error instead of a misleading "not running" message.
      if (e.status === 0) {
        setBackendDown(true)
      } else {
        setBackendDown(false)
        setError(e.message || 'Failed to load folders')
      }
    }
  }, [])

  // Load once on mount
  useEffect(() => { fetchFolders() }, [fetchFolders])

  // Poll only while a sync is in progress
  const isSyncing = folders.some(f => f.sync_status === 'syncing')
  useEffect(() => {
    if (!isSyncing) return
    const iv = setInterval(fetchFolders, 2000)
    return () => clearInterval(iv)
  }, [isSyncing, fetchFolders])

  const addFolder = async () => {
    const path = pathInput.trim()
    if (!path) return
    setAdding(true)
    setError('')
    try {
      await api('/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      setPathInput('')
      await fetchFolders()
    } catch (e) {
      setError(e.status === 0
        ? 'Backend is not running — start it with: uvicorn main:app --reload'
        : (e.message || 'Failed to add folder'))
    } finally {
      setAdding(false)
    }
  }

  const deleteFolder = async (id) => {
    if (!confirm('Remove this folder from the index?')) return
    try {
      await api(`/folders/${id}`, { method: 'DELETE' })
      await fetchFolders()
    } catch (e) {
      setError(e.message || 'Failed to remove folder')
    }
  }

  const syncFolder = async (id) => {
    try {
      await api(`/sync/${id}`, { method: 'POST' })
      await fetchFolders()
    } catch (e) {
      setError(e.message || 'Failed to start sync')
    }
  }

  const getSyncBadge = (status, progress) => {
    if (status === 'syncing') {
      const label = progress?.total > 0 ? `${progress.done} / ${progress.total}` : 'Syncing…'
      return <span className="badge badge-syncing"><span className="spinner" style={{ width: 10, height: 10 }} /> {label}</span>
    }
    if (status === 'done')  return <span className="badge badge-done">✓ Synced</span>
    if (status === 'error') return <span className="badge badge-error">⚠ Error</span>
    return <span className="badge badge-idle">Idle</span>
  }

  const getTypeBadge = (fname) => {
    if (!fname) return null
    const ext = fname.split('.').pop().toLowerCase()
    if (ext === 'pdf')             return <span className="badge badge-pdf">PDF</span>
    if (['docx','doc'].includes(ext)) return <span className="badge badge-docx">DOCX</span>
    return <span className="badge badge-text">TXT</span>
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 38, height: 38, borderRadius: 10, flexShrink: 0,
          background: 'linear-gradient(135deg, var(--accent-1), var(--accent-2))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1.1rem',
        }}>📁</div>
        <div>
          <h2 style={{ fontSize: '1.05rem', marginBottom: 1 }}>Indexed Folders</h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Add folder paths to index. Sync re-indexes changed files only.
          </p>
        </div>
      </div>

      <hr className="divider" style={{ margin: 0 }} />

      {/* Add folder input */}
      <div style={{ display: 'flex', gap: 10 }}>
        <input
          id="folder-path-input"
          className="input"
          placeholder="/Users/you/Documents/projects"
          value={pathInput}
          onChange={e => { setPathInput(e.target.value); setError('') }}
          onKeyDown={e => e.key === 'Enter' && addFolder()}
          style={{ flex: 1 }}
        />
        <button
          id="add-folder-btn"
          className="btn btn-primary"
          onClick={addFolder}
          disabled={adding || !pathInput.trim()}
        >
          {adding ? <span className="spinner" /> : '+'}
          Add
        </button>
      </div>

      {backendDown && (
        <div style={{
          background: 'rgba(234,179,8,0.08)', border: '1px solid rgba(234,179,8,0.3)',
          borderRadius: 'var(--radius-md)', padding: '10px 14px',
          color: '#ca8a04', fontSize: '0.83rem', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span>⚠</span>
          <span>Backend is not running. Start it with: <code style={{ fontFamily: 'monospace' }}>uvicorn main:app --reload</code></span>
        </div>
      )}

      {error && (
        <div style={{
          background: 'var(--danger-light)', border: '1px solid rgba(239,68,68,0.25)',
          borderRadius: 'var(--radius-md)', padding: '10px 14px',
          color: 'var(--danger)', fontSize: '0.83rem',
        }}>
          ⚠ {error}
        </div>
      )}

      {/* Folder list */}
      {folders.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">🗂️</span>
          <span style={{ fontSize: '0.88rem' }}>No folders added yet. Add a path above to get started.</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {folders.map(f => (
            <div key={f.id} className="fade-up" style={{
              background: 'var(--bg-glass-hover)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '14px 16px',
              display: 'flex', flexDirection: 'column', gap: 10,
            }}>
              {/* Path + badges */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <code style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '0.8rem', color: 'var(--text-primary)',
                    display: 'block', wordBreak: 'break-all',
                  }}>{f.path}</code>
                  <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {f.file_count} file{f.file_count !== 1 ? 's' : ''}
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>·</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {f.chunk_count} chunks
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>·</span>
                    {getSyncBadge(f.sync_status, f.sync_progress)}
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <button
                    id={`sync-btn-${f.id}`}
                    className="btn btn-ghost btn-sm"
                    onClick={() => syncFolder(f.id)}
                    disabled={f.sync_status === 'syncing'}
                    title="Sync folder"
                  >
                    {f.sync_status === 'syncing' ? <span className="spinner" /> : '↻'}
                    Sync
                  </button>
                  <button
                    id={`delete-folder-btn-${f.id}`}
                    className="btn btn-danger btn-sm"
                    onClick={() => deleteFolder(f.id)}
                    title="Remove folder"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Progress bar — shown while syncing */}
              {f.sync_status === 'syncing' && f.sync_progress?.total > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{
                    height: 4,
                    background: 'rgba(255,255,255,0.08)',
                    borderRadius: 99,
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.round((f.sync_progress.done / f.sync_progress.total) * 100)}%`,
                      background: 'linear-gradient(90deg, var(--accent-1), var(--accent-2))',
                      borderRadius: 99,
                      transition: 'width 0.4s ease',
                    }} />
                  </div>
                  {f.sync_progress.current_file && (
                    <p style={{
                      margin: 0,
                      fontSize: '0.72rem',
                      color: 'var(--text-muted)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {f.sync_progress.current_file}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
