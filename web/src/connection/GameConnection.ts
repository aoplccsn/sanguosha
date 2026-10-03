type Listener = (message: Record<string, unknown>) => void
type Status = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
type StatusListener = (status: Status) => void

export function websocketUrl(protocol: string, host: string, roomCode = ''): string {
  const scheme = protocol === 'https:' ? 'wss:' : 'ws:'
  const path = roomCode ? `/room/${encodeURIComponent(roomCode)}` : '/ws'
  return String(new URL(path, `${scheme}//${host}`))
}

export class GameConnection {
  private socket: WebSocket | null = null
  private listeners = new Set<Listener>()
  private statusListeners = new Set<StatusListener>()
  private heartbeat: number | null = null
  private intentionallyClosed = false
  private reconnectDelay = 800
  private roomCode = ''
  private pendingMessage: { type: string; fields: Record<string, unknown> } | null = null
  private reconnectMessage: { type: string; fields: Record<string, unknown> } | null = null

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

  connect(roomCode = this.roomCode) {
    if (this.socket?.readyState === WebSocket.OPEN || this.socket?.readyState === WebSocket.CONNECTING) return
    this.roomCode = roomCode
    this.intentionallyClosed = false
    this.setStatus(this.reconnectDelay > 800 ? 'reconnecting' : 'connecting')
    this.socket = new WebSocket(websocketUrl(window.location.protocol, window.location.host, this.roomCode))
    this.socket.addEventListener('open', () => {
      this.reconnectDelay = 800
      this.setStatus('connected')
      this.send('HELLO')
      if (this.pendingMessage) {
        const pending = this.pendingMessage
        this.pendingMessage = null
        this.send(pending.type, pending.fields)
      } else if (this.reconnectMessage) {
        this.send(this.reconnectMessage.type, this.reconnectMessage.fields)
      }
      if (!__CLOUDFLARE_ROOMS__) {
        this.heartbeat = window.setInterval(() => this.send('PING'), 15000)
      }
    })
    this.socket.addEventListener('message', (event) => {
      try {
        const message = JSON.parse(String(event.data)) as Record<string, unknown>
        if (message.type === 'WELCOME' && message.room_code && message.reconnect_token) {
          this.reconnectMessage = { type: 'RECONNECT', fields: {
            room_code: String(message.room_code), token: String(message.reconnect_token), name: '玩家',
          } }
        }
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

  openRoom(roomCode: string, type: string, fields: Record<string, unknown>) {
    this.intentionallyClosed = true
    if (this.heartbeat !== null) window.clearInterval(this.heartbeat)
    this.heartbeat = null
    this.socket?.close()
    this.socket = null
    this.intentionallyClosed = false
    this.roomCode = roomCode.trim().toUpperCase()
    this.pendingMessage = { type, fields }
    this.reconnectMessage = null
    this.reconnectDelay = 800
    this.connect(this.roomCode)
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
    this.pendingMessage = null
    this.reconnectMessage = null
  }
}
