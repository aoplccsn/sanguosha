import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { GameProvider } from './GameContext'

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
  close() { this.readyState = 3 }
}

beforeEach(() => {
  localStorage.clear()
  FakeSocket.instances = []
  vi.stubGlobal('WebSocket', FakeSocket)
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline'))))
})

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

it('shows a return-home message when a saved room disappeared after restart', async () => {
  localStorage.setItem('sanguosha.web.session.v1', JSON.stringify({
    roomCode: 'ABC234', playerName: '房主', seatId: 'p1', reconnectToken: 'old-token',
  }))
  render(<GameProvider><App /></GameProvider>)
  const socket = FakeSocket.instances[0]
  act(() => {
    socket.readyState = FakeSocket.OPEN
    socket.emit('open')
    socket.emit('message', { data: JSON.stringify({ type: 'WELCOME', version: 2 }) })
  })
  expect(socket.sent.some((item) => JSON.parse(item).type === 'RECONNECT')).toBe(true)
  act(() => socket.emit('message', { data: JSON.stringify({ type: 'ERROR', message: 'room not found' }) }))
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('服务器已重新启动，本局已结束'))
  expect(screen.getByRole('button', { name: '返回首页' })).toBeInTheDocument()
  expect(localStorage.getItem('sanguosha.web.session.v1')).toBeNull()
})
