import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { GameConnection, websocketUrl } from './GameConnection'

class FakeSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: FakeSocket[] = []
  readyState = FakeSocket.CONNECTING
  sent: string[] = []
  listeners = new Map<string, Array<(event: any) => void>>()

  constructor(public url: string) { FakeSocket.instances.push(this) }
  addEventListener(kind: string, listener: (event: any) => void) {
    this.listeners.set(kind, [...(this.listeners.get(kind) ?? []), listener])
  }
  emit(kind: string, event: any = {}) { this.listeners.get(kind)?.forEach((listener) => listener(event)) }
  send(value: string) { this.sent.push(value) }
  close() { this.readyState = 3; this.emit('close') }
}

describe('GameConnection', () => {
  it('uses same-origin WSS for an HTTPS Render page', () => {
    expect(websocketUrl('https:', 'sanguosha-web.onrender.com'))
      .toBe('wss://sanguosha-web.onrender.com/ws')
    expect(websocketUrl('http:', 'localhost:5173')).toBe('ws://localhost:5173/ws')
    expect(websocketUrl('https:', 'friends.example.b4a.run'))
      .toBe('wss://friends.example.b4a.run/ws')
    expect(websocketUrl('https:', 'game.example', 'ABC234'))
      .toBe('wss://game.example/room/ABC234')
  })
  beforeEach(() => {
    vi.useFakeTimers()
    FakeSocket.instances = []
    vi.stubGlobal('WebSocket', FakeSocket)
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('uses the current host, sends HELLO, dispatches messages and reconnects', () => {
    const connection = new GameConnection()
    const messages: Array<Record<string, unknown>> = []
    const statuses: string[] = []
    connection.subscribe((message) => messages.push(message))
    connection.subscribeStatus((status) => statuses.push(status))
    connection.connect()
    const first = FakeSocket.instances[0]
    expect(first.url).toContain('/ws')
    first.readyState = FakeSocket.OPEN
    first.emit('open')
    expect(JSON.parse(first.sent[0]).type).toBe('HELLO')
    first.emit('message', { data: JSON.stringify({ type: 'PONG' }) })
    expect(messages.at(-1)?.type).toBe('PONG')
    first.readyState = 3
    first.emit('close')
    expect(statuses).toContain('disconnected')
    vi.advanceTimersByTime(800)
    expect(FakeSocket.instances).toHaveLength(2)
  })

  it('opens a room route and sends the queued join after connecting', () => {
    const connection = new GameConnection()
    connection.openRoom('abc234', 'JOIN_ROOM', { room_code: 'ABC234', name: '玩家' })
    const socket = FakeSocket.instances[0]
    expect(socket.url).toContain('/room/ABC234')
    socket.readyState = FakeSocket.OPEN
    socket.emit('open')
    expect(socket.sent.map((item) => JSON.parse(item).type)).toEqual(['HELLO', 'JOIN_ROOM'])
  })

  it('rejoins the same seat after a WebSocket reconnect', () => {
    const connection = new GameConnection()
    connection.openRoom('ABC234', 'JOIN_ROOM', { room_code: 'ABC234', name: '玩家' })
    const first = FakeSocket.instances[0]
    first.readyState = FakeSocket.OPEN
    first.emit('open')
    first.emit('message', { data: JSON.stringify({
      type: 'WELCOME', room_code: 'ABC234', seat_id: 'p1', reconnect_token: 'secret',
    }) })
    first.close()
    vi.advanceTimersByTime(800)
    const second = FakeSocket.instances[1]
    second.readyState = FakeSocket.OPEN
    second.emit('open')
    expect(second.sent.map((item) => JSON.parse(item).type)).toEqual(['HELLO', 'RECONNECT'])
    expect(JSON.parse(second.sent[1]).token).toBe('secret')
  })
})
