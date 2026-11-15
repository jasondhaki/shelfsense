import type { ServerMessage } from '../types/contracts'

const PING_MS = 20_000
const MAX_BACKOFF_S = 15

function wsUrl(): string {
  const env = import.meta.env.VITE_WS_URL
  if (env) return env
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws/sim`
}

/** Connects to /ws/sim and reconnects with exponential backoff (1, 2, 4, 8 … 15 s).
 *  Returns a function that closes the socket for good. */
export function connectSim(handlers: {
  onMessage: (m: ServerMessage) => void
  onOpen: () => void
  onClose: () => void
}): () => void {
  let socket: WebSocket | null = null
  let attempt = 0
  let stopped = false
  let ping: number | undefined
  let retry: number | undefined

  const open = () => {
    socket = new WebSocket(wsUrl())
    socket.onopen = () => {
      attempt = 0
      handlers.onOpen()
      ping = window.setInterval(() => socket?.send('ping'), PING_MS)
    }
    socket.onmessage = (e: MessageEvent<string>) => {
      handlers.onMessage(JSON.parse(e.data) as ServerMessage)
    }
    socket.onclose = () => {
      window.clearInterval(ping)
      if (stopped) return
      handlers.onClose()
      const delay = Math.min(2 ** attempt, MAX_BACKOFF_S) * 1000
      attempt += 1
      retry = window.setTimeout(open, delay)
    }
  }

  open()
  return () => {
    stopped = true
    window.clearInterval(ping)
    window.clearTimeout(retry)
    socket?.close()
  }
}
