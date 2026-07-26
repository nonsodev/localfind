// Central API helper.
//
// Every backend call should go through `api()` so that:
//   - Each request/response/error is logged to the browser console (with timing),
//     so you can see exactly what's happening instead of guessing.
//   - Failures throw a structured ApiError instead of being swallowed — callers
//     show the message to the user rather than failing silently.
//   - Backend up/down transitions are broadcast once (onBackendStatus), so the
//     UI can show an "offline" banner without every component polling.

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status   // 0 = network/unreachable
    this.data = data
  }
}

const statusListeners = new Set()

/** Subscribe to backend online/offline changes. Returns an unsubscribe fn. */
export function onBackendStatus(cb) {
  statusListeners.add(cb)
  return () => statusListeners.delete(cb)
}

let lastOnline = null
function emitStatus(online) {
  if (online === lastOnline) return   // only fire on actual transitions
  lastOnline = online
  statusListeners.forEach(cb => {
    try { cb(online) } catch (e) { console.error('[api] status listener threw', e) }
  })
}

/** Build a URL for direct browser use (e.g. <img>/<video> src). */
export function fileUrl(path) {
  return `${API_BASE}/files/${encodeURIComponent(path)}`
}

/**
 * Fetch JSON from the backend. Resolves to parsed data, or throws ApiError.
 * Logs the request, the outcome, and how long it took.
 */
export async function api(path, opts = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const method = (opts.method || 'GET').toUpperCase()
  const t0 = performance.now()
  console.debug(`[api] → ${method} ${url}`)

  let res
  try {
    res = await fetch(url, opts)
  } catch (err) {
    const ms = (performance.now() - t0).toFixed(0)
    console.error(`[api] ✗ ${method} ${url} — network error after ${ms}ms`, err)
    emitStatus(false)
    throw new ApiError('Backend is not reachable', 0, err)
  }

  const ms = (performance.now() - t0).toFixed(0)
  emitStatus(true)

  let data = null
  if ((res.headers.get('content-type') || '').includes('application/json')) {
    data = await res.json().catch(() => null)
  }

  if (!res.ok) {
    const detail = data?.detail || data?.error || res.statusText || `HTTP ${res.status}`
    console.error(`[api] ✗ ${method} ${url} — ${res.status} (${ms}ms):`, detail)
    throw new ApiError(detail, res.status, data)
  }

  console.debug(`[api] ← ${method} ${url} — ${res.status} (${ms}ms)`)
  return data
}
