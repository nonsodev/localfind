import { useState, useEffect } from 'react'

const API = '/api'

function StatItem({ icon, label, value, accent }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 6,
      padding: '16px 20px',
      background: accent ? 'var(--accent-light)' : 'var(--bg-glass-hover)',
      border: `1px solid ${accent ? 'rgba(124,58,237,0.25)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-md)',
      flex: 1,
      minWidth: 100,
    }}>
      <span style={{ fontSize: '1.3rem' }}>{icon}</span>
      <span style={{
        fontSize: '1.5rem', fontWeight: 700,
        color: accent ? 'var(--accent-2)' : 'var(--text-primary)',
        lineHeight: 1,
      }}>
        {value ?? '—'}
      </span>
      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
        {label}
      </span>
    </div>
  )
}

export default function StatsPanel() {
  const [stats, setStats] = useState(null)
  const [backendOk, setBackendOk] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [statsRes, healthRes] = await Promise.all([
          fetch(`${API}/stats`),
          fetch(`${API}/health`),
        ])
        if (statsRes.ok) setStats(await statsRes.json())
        setBackendOk(healthRes.ok)
      } catch (_) {
        setBackendOk(false)
      }
    }
    fetchStats()
    const iv = setInterval(fetchStats, 5000)
    return () => clearInterval(iv)
  }, [])

  const formatDate = (iso) => {
    if (!iso) return 'Never'
    try {
      return new Date(iso + 'Z').toLocaleString(undefined, {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    } catch { return iso }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Backend status indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {backendOk === null && (
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Connecting…</span>
        )}
        {backendOk === true && (
          <>
            <span className="pulse-dot" />
            <span style={{ fontSize: '0.78rem', color: 'var(--success)' }}>Backend online</span>
          </>
        )}
        {backendOk === false && (
          <>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: 'var(--danger)', display: 'inline-block',
            }} />
            <span style={{ fontSize: '0.78rem', color: 'var(--danger)' }}>
              Backend offline — start with <code style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem' }}>uvicorn main:app --reload</code>
            </span>
          </>
        )}
      </div>

      {/* Stat tiles */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <StatItem icon="📁" label="Folders" value={stats?.total_folders} />
        <StatItem icon="📄" label="Files" value={stats?.total_files} />
        <StatItem icon="🧩" label="Chunks" value={stats?.total_chunks} accent />
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 6,
          padding: '16px 20px',
          background: 'var(--bg-glass-hover)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          flex: 1, minWidth: 140,
        }}>
          <span style={{ fontSize: '1.3rem' }}>🕐</span>
          <span style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1 }}>
            {formatDate(stats?.last_sync)}
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Last Sync
          </span>
        </div>
      </div>
    </div>
  )
}
