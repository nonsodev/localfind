const FILE_TYPE_CONFIG = {
  pdf:  { label: 'PDF',  color: '#f87171', bg: 'rgba(239, 68, 68, 0.12)',  icon: '📄' },
  docx: { label: 'DOCX', color: '#60a5fa', bg: 'rgba(59, 130, 246, 0.12)', icon: '📝' },
  doc:  { label: 'DOC',  color: '#60a5fa', bg: 'rgba(59, 130, 246, 0.12)', icon: '📝' },
  text: { label: 'TXT',  color: '#34d399', bg: 'rgba(16, 185, 129, 0.12)', icon: '📃' },
}

function getFileConfig(fileType) {
  return FILE_TYPE_CONFIG[fileType] || FILE_TYPE_CONFIG.text
}

const STOP_WORDS = new Set([
  'a','an','the','and','or','but','in','on','at','to','for','of','with',
  'is','are','was','were','be','been','being','have','has','had','do','does',
  'did','will','would','could','should','may','might','can','what','which',
  'who','this','that','these','those','how','why','when','where','its','it',
  'not','from','by','as','if','than','then','there','their','they','we',
  'you','into','about','between','through','before','after','each','also',
  'just','more','some','such','very','your','our','his','her','them','both',
])

function highlightText(text, query) {
  if (!query || !text) return text
  const words = query
    .trim()
    .split(/\s+/)
    .map(w => w.replace(/[^a-zA-Z0-9]/g, ''))
    .filter(w => w.length >= 4 && !STOP_WORDS.has(w.toLowerCase()))
  if (!words.length) return text
  const regex = new RegExp(
    `(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi'
  )
  const parts = text.split(regex)
  return parts.map((part, i) =>
    regex.test(part)
      ? <mark key={i} style={{ background: 'var(--accent-light)', color: 'var(--accent-2)', borderRadius: 3, padding: '0 2px' }}>{part}</mark>
      : part
  )
}

export default function ResultCard({ result, query, index }) {
  const config = getFileConfig(result.file_type)
  const scorePercent = Math.round(result.score * 100)

  return (
    <div
      className="fade-up"
      style={{
        animationDelay: `${index * 0.04}s`,
        background: 'var(--bg-glass)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '18px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        transition: 'border-color var(--transition), box-shadow var(--transition)',
        cursor: 'default',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = 'var(--border-strong)'
        e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,0.4)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'var(--border)'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        {/* File icon */}
        <div style={{
          width: 36, height: 36, borderRadius: 8, flexShrink: 0,
          background: config.bg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1.1rem',
        }}>
          {config.icon}
        </div>

        {/* File info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
              {result.file_name}
            </span>
            <span className="badge" style={{ background: config.bg, color: config.color }}>
              {config.label}
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
              chunk #{result.chunk_index + 1}
            </span>
          </div>

          <div style={{
            fontSize: '0.72rem', color: 'var(--text-muted)',
            marginTop: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}
            title={result.file_path}
          >
            {result.file_path}
          </div>
        </div>
      </div>

      {/* Score bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', width: 28, flexShrink: 0 }}>
          {scorePercent}%
        </span>
        <div className="score-bar-track">
          <div
            className="score-bar-fill"
            style={{ width: `${scorePercent}%` }}
          />
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', flexShrink: 0 }}>
          relevance
        </span>
      </div>

      {/* Text snippet */}
      <div style={{
        background: 'rgba(255,255,255,0.025)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px 14px',
        fontSize: '0.83rem',
        lineHeight: 1.7,
        color: 'var(--text-secondary)',
        display: '-webkit-box',
        WebkitLineClamp: 5,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {highlightText(result.text, query)}
      </div>
    </div>
  )
}
