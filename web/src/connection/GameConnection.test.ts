import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { GameConnection } from './GameConnection'

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
})
