type Listener = (message: Record<string, unknown>) => void
type Status = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
type StatusListener = (status: Status) => void

export function websocketUrl(protocol: string, host: string): string {
  const scheme = protocol === 'https:' ? 'wss:' : 'ws:'
  return String(new URL('/ws', `${scheme}//${host}`))
}

export class GameConnection {
  private socket: WebSocket | null = null
  private listeners = new Set<Listener>()
  private statusListeners = new Set<StatusListener>()
  private heartbeat: number | null = null
  private intentionallyClosed = false
  private reconnectDelay = 800

  subscribe(listener: Listener) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  subscribeStatus(listener: StatusListener) {
    this.statusListeners.add(listener)
    return () => this.statusListeners.delete(listener)
  }

  private setStatus(status: Status) {
    this.statusListeners.forEach((listener) => listener(status))
  }

  connect() {
    if (this.socket?.readyState === WebSocket.OPEN || this.socket?.readyState === WebSocket.CONNECTING) return
    this.intentionallyClosed = false
    this.setStatus(this.reconnectDelay > 800 ? 'reconnecting' : 'connecting')
    this.socket = new WebSocket(websocketUrl(window.location.protocol, window.location.host))
    this.socket.addEventListener('open', () => {
      this.reconnectDelay = 800
      this.setStatus('connected')
      this.send('HELLO')
      this.heartbeat = window.setInterval(() => this.send('PING'), 15000)
    })
    this.socket.addEventListener('message', (event) => {
      try {
        const message = JSON.parse(String(event.data)) as Record<string, unknown>
        this.listeners.forEach((listener) => listener(message))
      } catch {
        this.listeners.forEach((listener) => listener({ type: 'ERROR', message: '服务器消息格式错误' }))
      }
    })
    this.socket.addEventListener('close', () => {
      if (this.heartbeat !== null) window.clearInterval(this.heartbeat)
      this.heartbeat = null
      this.setStatus('disconnected')
      if (!this.intentionallyClosed) {
        const delay = this.reconnectDelay
        this.reconnectDelay = Math.min(this.reconnectDelay * 1.7, 8000)
        window.setTimeout(() => this.connect(), delay)
      }
    })
    this.socket.addEventListener('error', () => {
      this.listeners.forEach((listener) => listener({ type: 'ERROR', message: '无法连接游戏服务器' }))
    })
  }

  send(type: string, fields: Record<string, unknown> = {}) {
    if (this.socket?.readyState !== WebSocket.OPEN) return false
    this.socket.send(JSON.stringify({ type, version: __PROTOCOL_VERSION__, ...fields }))
    return true
  }

  disconnect() {
    this.intentionallyClosed = true
    if (this.heartbeat !== null) window.clearInterval(this.heartbeat)
    this.socket?.close()
    this.socket = null
  }
}
