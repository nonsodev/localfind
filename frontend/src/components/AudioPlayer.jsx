import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.js'

export default function AudioPlayer({ audioUrl, startTime = 0, endTime = 0, duration = 0 }) {
  const containerRef = useRef(null)
  const wavesurferRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!containerRef.current) return

    // Create WaveSurfer instance
    const wavesurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor: 'rgba(167, 139, 250, 0.3)',
      progressColor: 'rgba(167, 139, 250, 0.8)',
      cursorColor: '#a78bfa',
      barWidth: 2,
      barRadius: 3,
      cursorWidth: 2,
      height: 80,
      barGap: 2,
      normalize: true,
      backend: 'WebAudio',
    })

    wavesurferRef.current = wavesurfer

    // Load audio
    wavesurfer.load(audioUrl)

    // Add regions plugin for highlighting matched segment
    const regions = wavesurfer.registerPlugin(RegionsPlugin.create())

    // Event listeners
    wavesurfer.on('ready', () => {
      setIsLoading(false)
      
      // Add green highlighted region for matched segment
      if (startTime !== undefined && endTime !== undefined && endTime > startTime) {
        regions.addRegion({
          start: startTime,
          end: endTime,
          color: 'rgba(16, 185, 129, 0.3)', // Green highlight
          drag: false,
          resize: false,
        })
        
        // Auto-seek to matched segment start
        wavesurfer.seekTo(startTime / wavesurfer.getDuration())
      }
    })

    wavesurfer.on('play', () => setIsPlaying(true))
    wavesurfer.on('pause', () => setIsPlaying(false))
    wavesurfer.on('timeupdate', (time) => setCurrentTime(time))

    // Cleanup
    return () => {
      wavesurfer.destroy()
    }
  }, [audioUrl, startTime, endTime])

  const togglePlayPause = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause()
    }
  }

  const jumpToMatch = () => {
    if (wavesurferRef.current && startTime !== undefined) {
      wavesurferRef.current.seekTo(startTime / wavesurferRef.current.getDuration())
      wavesurferRef.current.play()
    }
  }

  const formatTime = (seconds) => {
    if (!seconds && seconds !== 0) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div style={{
      background: 'rgba(0, 0, 0, 0.3)',
      borderRadius: 12,
      padding: 20,
    }}>
      {/* Waveform container */}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          marginBottom: 16,
          opacity: isLoading ? 0.5 : 1,
          transition: 'opacity 0.3s',
        }}
      />

      {isLoading && (
        <div style={{
          textAlign: 'center',
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: '0.85rem',
          marginBottom: 12,
        }}>
          Loading audio...
        </div>
      )}

      {/* Controls */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 16,
      }}>
        {/* Play/Pause button */}
        <button
          onClick={togglePlayPause}
          disabled={isLoading}
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            border: '2px solid #a78bfa',
            background: isPlaying ? '#a78bfa' : 'transparent',
            color: '#fff',
            fontSize: '1.2rem',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
            opacity: isLoading ? 0.5 : 1,
          }}
        >
          {isPlaying ? '⏸' : '▶️'}
        </button>

        {/* Jump to match button */}
        {startTime !== undefined && endTime !== undefined && endTime > startTime && (
          <button
            onClick={jumpToMatch}
            disabled={isLoading}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: '1px solid rgba(16, 185, 129, 0.5)',
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#10b981',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.2s',
              fontFamily: 'inherit',
              opacity: isLoading ? 0.5 : 1,
            }}
            onMouseEnter={(e) => !isLoading && (e.target.style.background = 'rgba(16, 185, 129, 0.25)')}
            onMouseLeave={(e) => (e.target.style.background = 'rgba(16, 185, 129, 0.15)')}
          >
            🎯 Jump to Match
          </button>
        )}

        {/* Time display */}
        <div style={{
          marginLeft: 'auto',
          fontSize: '0.85rem',
          color: 'rgba(255, 255, 255, 0.7)',
          fontFamily: 'monospace',
          fontWeight: 600,
        }}>
          {formatTime(currentTime)} / {formatTime(duration || wavesurferRef.current?.getDuration() || 0)}
        </div>
      </div>

      {/* Matched segment info */}
      {startTime !== undefined && endTime !== undefined && endTime > startTime && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 8,
          padding: '12px 16px',
        }}>
          <div style={{
            fontSize: '0.75rem',
            color: '#10b981',
            fontWeight: 600,
            marginBottom: 4,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            🎯 Matched Segment (Green Region)
          </div>
          <div style={{
            fontSize: '0.85rem',
            color: '#6ee7b7',
            fontWeight: 500,
          }}>
            {formatTime(startTime)} → {formatTime(endTime)}
          </div>
        </div>
      )}
    </div>
  )
}
