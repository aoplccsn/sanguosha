import { act, render, screen, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
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

it('ignores a StrictMode cleanup socket after its replacement connects', async () => {
  render(<StrictMode><GameProvider><App /></GameProvider></StrictMode>)
  expect(FakeSocket.instances).toHaveLength(2)
  const [old, current] = FakeSocket.instances
  act(() => {
    old.emit('error')
    old.emit('close')
    current.readyState = FakeSocket.OPEN
    current.emit('open')
  })
  await waitFor(() => expect(screen.getByText('服务器已连接')).toBeInTheDocument())
  expect(screen.queryByText('无法连接游戏服务器')).not.toBeInTheDocument()
})
