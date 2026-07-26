import { useState } from 'react'
import AudioPlayer from './AudioPlayer'

const MODALITY_CONFIG = {
  text: {
    label: 'Text',
    color: '#34d399',
    bg: 'rgba(52, 211, 153, 0.15)',
    icon: '📄',
    gradient: 'linear-gradient(135deg, #34d399 0%, #10b981 100%)',
  },
  image: {
    label: 'Image',
    color: '#f472b6',
    bg: 'rgba(244, 114, 182, 0.15)',
    icon: '🖼️',
    gradient: 'linear-gradient(135deg, #f472b6 0%, #ec4899 100%)',
  },
  audio: {
    label: 'Audio',
    color: '#a78bfa',
    bg: 'rgba(167, 139, 250, 0.15)',
    icon: '🎙️',
    gradient: 'linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%)',
  },
  audio_transcript: {
    label: 'Audio',
    color: '#a78bfa',
    bg: 'rgba(167, 139, 250, 0.15)',
    icon: '🎙️',
    gradient: 'linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%)',
  },
  video: {
    label: 'Video',
    color: '#60a5fa',
    bg: 'rgba(96, 165, 250, 0.15)',
    icon: '🎬',
    gradient: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)',
  },
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
      ? <mark key={i} style={{
          background: 'rgba(102, 126, 234, 0.3)',
          color: '#a5b4fc',
          borderRadius: 4,
          padding: '2px 4px',
          fontWeight: 600,
        }}>{part}</mark>
      : part
  )
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatTimestamp(seconds) {
  if (!seconds && seconds !== 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function openFile(filePath) {
  // Try to open file in system default application
  window.open(`file://${filePath}`, '_blank')
}

export default function MultimodalResultCard({ result, query, index, onSelect }) {
  const [imageError, setImageError] = useState(false)
  const [imageExpanded, setImageExpanded] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const [videoPlaying, setVideoPlaying] = useState(false)
  
  const modality = result.modality || 'text'
  // Normalize the granular modalities to their display group.
  const displayModality =
    modality === 'audio_transcript' ? 'audio'
    : (modality === 'video_frame' || modality === 'video_transcript') ? 'video'
    : modality
  const modalityConfig = MODALITY_CONFIG[modality] || MODALITY_CONFIG[displayModality] || MODALITY_CONFIG.text
  const scorePercent = Math.round(result.score * 100)

  // Render based on modality
  const renderContent = () => {
    if (displayModality === 'image') {
      const caption = result.metadata?.has_caption ? result.text : null
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: caption ? '12px 12px 0 0' : 12,
            overflow: 'hidden',
            position: 'relative',
            cursor: 'pointer',
          }}
          onClick={() => setImageExpanded(!imageExpanded)}
          >
            {!imageError ? (
              <>
                <img
                  src={`/api/files/${encodeURIComponent(result.file_path)}`}
                  alt={result.file_name}
                  onError={() => setImageError(true)}
                  style={{
                    width: '100%',
                    height: imageExpanded ? 'auto' : 240,
                    maxHeight: imageExpanded ? 600 : 240,
                    objectFit: imageExpanded ? 'contain' : 'cover',
                    display: 'block',
                    background: 'rgba(0, 0, 0, 0.5)',
                    transition: 'all 0.3s ease',
                  }}
                />
                {/* Expand indicator */}
                <div style={{
                  position: 'absolute',
                  top: 12,
                  right: 12,
                  background: 'rgba(0, 0, 0, 0.7)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: 8,
                  padding: '6px 12px',
                  fontSize: '0.75rem',
                  color: '#fff',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}>
                  {imageExpanded ? '🔽 Click to collapse' : '🔼 Click to expand'}
                </div>

                {/* Image metadata overlay */}
                {result.metadata && (
                  <div style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    background: 'linear-gradient(to top, rgba(0,0,0,0.9), transparent)',
                    padding: '32px 16px 12px',
                    fontSize: '0.75rem',
                    color: 'rgba(255,255,255,0.9)',
                    display: 'flex',
                    gap: 16,
                    fontWeight: 500,
                  }}>
                    {result.metadata.width && result.metadata.height && (
                      <span>📐 {result.metadata.width} × {result.metadata.height}</span>
                    )}
                    {result.metadata.format && (
                      <span>🖼️ {result.metadata.format}</span>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div style={{
                padding: '60px 20px',
                textAlign: 'center',
                color: 'rgba(255, 255, 255, 0.5)',
                fontSize: '0.9rem',
              }}>
                <div style={{ fontSize: '3rem', marginBottom: 12 }}>🖼️</div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{result.file_name}</div>
                {result.metadata?.width && result.metadata?.height && (
                  <div style={{ fontSize: '0.8rem' }}>
                    {result.metadata.width} × {result.metadata.height}
                  </div>
                )}
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: 'rgba(255, 255, 255, 0.3)' }}>
                  Image preview unavailable
                </div>
              </div>
            )}
          </div>

          {/* AI-generated caption */}
          {caption && (
            <div style={{
              background: 'rgba(244, 114, 182, 0.08)',
              border: '1px solid rgba(244, 114, 182, 0.2)',
              borderTop: 'none',
              borderRadius: '0 0 12px 12px',
              padding: '10px 14px',
              display: 'flex',
              gap: 8,
              alignItems: 'flex-start',
            }}>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                color: '#f472b6',
                background: 'rgba(244, 114, 182, 0.15)',
                border: '1px solid rgba(244, 114, 182, 0.3)',
                borderRadius: 6,
                padding: '2px 7px',
                flexShrink: 0,
                letterSpacing: '0.3px',
                marginTop: 1,
              }}>
                AI caption
              </span>
              <p style={{
                margin: 0,
                fontSize: '0.82rem',
                lineHeight: 1.55,
                color: 'rgba(255, 255, 255, 0.65)',
                fontStyle: 'italic',
              }}>
                {caption}
              </p>
            </div>
          )}
        </div>
      )
    }

    if (displayModality === 'audio') {
      const startTime = result.metadata?.start_time || 0;
      const endTime = result.metadata?.end_time || 0;
      const duration = result.metadata?.duration || 0;
      const audioUrl = `/api/files/${encodeURIComponent(result.file_path)}`;
      
      return (
        <div>
          {/* Enhanced Audio Player with Waveform */}
          <AudioPlayer
            audioUrl={audioUrl}
            startTime={startTime}
            endTime={endTime}
            duration={duration}
          />
          
          {/* Transcript text */}
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: 12,
            padding: '16px 18px',
            marginTop: 16,
            fontSize: '0.9rem',
            lineHeight: 1.8,
            color: 'rgba(255, 255, 255, 0.8)',
            fontStyle: 'italic',
          }}>
            "{result.text}"
          </div>
          
          {/* Audio metadata badges */}
          {result.metadata && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
              gap: 12,
              marginTop: 16,
            }}>
              {result.metadata.language && (
                <div style={{
                  background: 'rgba(167, 139, 250, 0.1)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  fontSize: '0.8rem',
                  color: '#c4b5fd',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}>
                  <span>🌐</span>
                  <span>{result.metadata.language.toUpperCase()}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )
    }

    if (displayModality === 'video') {
      // A video result is a single moment: the matched keyframe (what's on screen)
      // or a matched line of speech (what was said). We show the still frame first
      // and let you press play — the video opens seeked to that moment via #t=.
      // No range is shown; a video result is a point in time, not a span.
      const isFrame = modality === 'video_frame'
      const seekTime = isFrame
        ? (result.metadata?.timestamp || 0)
        : (result.metadata?.start_time || 0)
      const videoUrl = `/api/files/${encodeURIComponent(result.file_path)}#t=${Math.floor(seekTime)}`
      const framePath = result.metadata?.frame_path
      const frameThumb = framePath ? `/api/files/${encodeURIComponent(framePath)}` : null
      const caption = isFrame && result.metadata?.has_caption ? result.text : null

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', background: '#000' }}>
            {videoPlaying ? (
              <video
                key={videoUrl}
                src={videoUrl}
                controls
                autoPlay
                style={{ width: '100%', maxHeight: 320, display: 'block', background: '#000' }}
              />
            ) : (
              <div
                onClick={() => setVideoPlaying(true)}
                style={{ position: 'relative', cursor: 'pointer' }}
                title={`Play from ${formatTimestamp(seekTime)}`}
              >
                {frameThumb ? (
                  <img
                    src={frameThumb}
                    alt={`${result.file_name} at ${formatTimestamp(seekTime)}`}
                    style={{ width: '100%', maxHeight: 320, objectFit: 'cover', display: 'block' }}
                  />
                ) : (
                  <div style={{
                    height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'rgba(255,255,255,0.35)', fontSize: '2.5rem',
                  }}>🎬</div>
                )}
                {/* Play overlay */}
                <div style={{
                  position: 'absolute', inset: 0, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(0,0,0,0.15)',
                }}>
                  <div style={{
                    width: 60, height: 60, borderRadius: '50%',
                    background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(6px)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1.5rem', color: '#fff', paddingLeft: 4,
                  }}>▶</div>
                </div>
              </div>
            )}

            {!videoPlaying && (
              <div style={{
                position: 'absolute',
                top: 12,
                left: 12,
                background: 'rgba(0, 0, 0, 0.75)',
                backdropFilter: 'blur(10px)',
                borderRadius: 8,
                padding: '6px 12px',
                fontSize: '0.78rem',
                color: '#fff',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                pointerEvents: 'none',
              }}>
                {isFrame ? '🎬' : '🗣️'} {formatTimestamp(seekTime)}
              </div>
            )}
          </div>

          {(caption || !isFrame) && (
            <div style={{
              background: isFrame ? 'rgba(96, 165, 250, 0.08)' : 'rgba(0, 0, 0, 0.3)',
              border: isFrame ? '1px solid rgba(96, 165, 250, 0.2)' : 'none',
              borderRadius: 12,
              padding: '12px 16px',
              display: 'flex',
              gap: 8,
              alignItems: 'flex-start',
            }}>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                color: '#60a5fa',
                background: 'rgba(96, 165, 250, 0.15)',
                border: '1px solid rgba(96, 165, 250, 0.3)',
                borderRadius: 6,
                padding: '2px 7px',
                flexShrink: 0,
                letterSpacing: '0.3px',
                marginTop: 1,
                whiteSpace: 'nowrap',
              }}>
                {isFrame ? 'Frame' : 'Speech'} · {formatTimestamp(seekTime)}
              </span>
              <p style={{
                margin: 0,
                fontSize: '0.85rem',
                lineHeight: 1.6,
                color: 'rgba(255, 255, 255, 0.75)',
                fontStyle: 'italic',
              }}>
                {isFrame ? caption : <>"{highlightText(result.text, query)}"</>}
              </p>
            </div>
          )}
        </div>
      )
    }

    // Text modality (default)
    return (
      <div style={{
        background: 'rgba(0, 0, 0, 0.3)',
        borderRadius: 12,
        padding: '16px 18px',
        fontSize: '0.9rem',
        lineHeight: 1.8,
        color: 'rgba(255, 255, 255, 0.8)',
        maxHeight: 200,
        overflow: 'auto',
      }}>
        {highlightText(result.text, query)}
      </div>
    )
  }

  return (
    <div
      className="fade-up"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        animationDelay: `${(index % 6) * 0.05}s`,
        background: 'rgba(255, 255, 255, 0.05)',
        backdropFilter: 'blur(20px)',
        border: `1px solid ${isHovered ? modalityConfig.color + '80' : 'rgba(255, 255, 255, 0.1)'}`,
        borderRadius: 20,
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        cursor: 'default',
        boxShadow: isHovered 
          ? `0 12px 40px ${modalityConfig.color}40, 0 0 0 1px ${modalityConfig.color}40`
          : '0 4px 16px rgba(0, 0, 0, 0.3)',
        transform: isHovered ? 'translateY(-4px)' : 'none',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        {/* Icon */}
        <div style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          flexShrink: 0,
          background: modalityConfig.gradient,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.3rem',
          boxShadow: `0 4px 16px ${modalityConfig.color}40`,
        }}>
          {modalityConfig.icon}
        </div>

        {/* File info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 6 }}>
            <span style={{
              fontWeight: 700,
              fontSize: '1rem',
              color: '#fff',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {result.file_name}
            </span>
            <span style={{
              background: modalityConfig.bg,
              color: modalityConfig.color,
              padding: '4px 10px',
              borderRadius: 8,
              fontSize: '0.7rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}>
              {modalityConfig.label}
            </span>
            {modality === 'text' && result.chunk_index !== undefined && (
              <span style={{
                fontSize: '0.7rem',
                color: 'rgba(255, 255, 255, 0.4)',
                fontWeight: 600,
              }}>
                Chunk #{result.chunk_index + 1}
              </span>
            )}
          </div>

          {/* Clickable file path */}
          <button
            onClick={() => openFile(result.file_path)}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              fontSize: '0.75rem',
              color: 'rgba(255, 255, 255, 0.4)',
              cursor: 'pointer',
              textAlign: 'left',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              width: '100%',
              fontFamily: 'monospace',
              transition: 'color 0.2s',
            }}
            onMouseEnter={(e) => e.target.style.color = modalityConfig.color}
            onMouseLeave={(e) => e.target.style.color = 'rgba(255, 255, 255, 0.4)'}
            title={`Click to open: ${result.file_path}`}
          >
            📁 {result.file_path}
          </button>
        </div>
      </div>

      {/* Score bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{
          fontSize: '0.8rem',
          color: 'rgba(255, 255, 255, 0.5)',
          fontWeight: 700,
          minWidth: 40,
        }}>
          {scorePercent}%
        </span>
        <div style={{
          flex: 1,
          height: 8,
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: 99,
          overflow: 'hidden',
        }}>
          <div
            style={{
              width: `${scorePercent}%`,
              height: '100%',
              background: modalityConfig.gradient,
              borderRadius: 99,
              transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: `0 0 12px ${modalityConfig.color}80`,
            }}
          />
        </div>
        <span style={{
          fontSize: '0.75rem',
          color: 'rgba(255, 255, 255, 0.4)',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          Match
        </span>
      </div>

      {/* Content */}
      {renderContent()}
    </div>
  )
}
