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

  it('uses the current host and stops reconnecting while no room was requested', () => {
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
    expect(statuses.at(-1)).toBe('idle')
    vi.advanceTimersByTime(800)
    expect(FakeSocket.instances).toHaveLength(1)
  })

  it('opens a room route and sends the queued join after connecting', () => {
    const connection = new GameConnection()
    connection.openRoom('abc234', 'JOIN_ROOM', { room_code: 'ABC234', name: '玩家' })
    const socket = FakeSocket.instances[0]
    expect(socket.url).toContain('/room/ABC234')
    socket.readyState = FakeSocket.OPEN
    socket.emit('open')
    expect(socket.sent.map((item) => JSON.parse(item).type)).toEqual(['HELLO', 'PING', 'JOIN_ROOM'])
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
    expect(second.sent.map((item) => JSON.parse(item).type)).toEqual(['HELLO', 'PING', 'RECONNECT'])
    expect(JSON.parse(second.sent[2]).token).toBe('secret')
  })

  it('ignores errors and closes from a socket replaced by a room connection', () => {
    const connection = new GameConnection()
    const statuses: string[] = []
    const messages: Array<Record<string, unknown>> = []
    connection.subscribeStatus((status) => statuses.push(status))
    connection.subscribe((message) => messages.push(message))
    connection.openRoom('ABC234', 'JOIN_ROOM', { name: '甲' })
    const old = FakeSocket.instances[0]
    connection.openRoom('EFG567', 'JOIN_ROOM', { name: '乙' })
    const current = FakeSocket.instances[1]
    old.emit('error')
    old.emit('close')
    current.readyState = FakeSocket.OPEN
    current.emit('open')
    expect(statuses.at(-1)).toBe('connected')
    expect(messages).toEqual([])
    vi.advanceTimersByTime(9000)
    expect(FakeSocket.instances).toHaveLength(2)
  })

  it('treats a transport error as recoverable and clears the state on reconnect', () => {
    const connection = new GameConnection()
    const statuses: string[] = []
    const messages: Array<Record<string, unknown>> = []
    connection.subscribeStatus((status) => statuses.push(status))
    connection.subscribe((message) => messages.push(message))
    connection.openRoom('ABC234', 'JOIN_ROOM', { name: '甲', room_code: 'ABC234' })
    const first = FakeSocket.instances[0]
    first.emit('error')
    expect(statuses.at(-1)).toBe('reconnecting')
    expect(messages).toEqual([])
    vi.advanceTimersByTime(800)
    const next = FakeSocket.instances[1]
    next.readyState = FakeSocket.OPEN
    next.emit('open')
    expect(statuses.at(-1)).toBe('connected')
  })

  it('retries the pending join if the socket drops before admission is confirmed', () => {
    const connection = new GameConnection()
    connection.openRoom('ABC234', 'JOIN_ROOM', { name: '甲', room_code: 'ABC234' })
    const first = FakeSocket.instances[0]
    first.readyState = FakeSocket.OPEN
    first.emit('open')
    first.close()
    vi.advanceTimersByTime(800)
    const second = FakeSocket.instances[1]
    second.readyState = FakeSocket.OPEN
    second.emit('open')
    expect(second.sent.map((item) => JSON.parse(item).type)).toEqual(['HELLO', 'PING', 'JOIN_ROOM'])
  })
})

it('times out a stuck handshake, stops after six failures and allows explicit retry', () => {
 vi.useFakeTimers();FakeSocket.instances=[];vi.stubGlobal('WebSocket',FakeSocket)
 const connection=new GameConnection();const statuses:string[]=[];connection.subscribeStatus(status=>statuses.push(status))
 connection.openRoom('ABC234','JOIN_ROOM',{name:'测试'})
 vi.advanceTimersByTime(120000)
 expect(statuses.at(-1)).toBe('offline');expect(FakeSocket.instances).toHaveLength(6)
 connection.retry();expect(FakeSocket.instances).toHaveLength(7)
 connection.disconnect();vi.useRealTimers();vi.unstubAllGlobals()
})


it('waits for restored snapshot after authenticated welcome and bounds open-but-stale recovery', () => {
 vi.useFakeTimers(); FakeSocket.instances=[]; vi.stubGlobal('WebSocket',FakeSocket)
 const connection=new GameConnection();const statuses:string[]=[];connection.subscribeStatus(s=>statuses.push(s))
 connection.openRoom('ABC234','JOIN_ROOM',{name:'玩家'})
 let socket=FakeSocket.instances.at(-1)!;socket.readyState=1;socket.emit('open')
 socket.emit('message',{data:JSON.stringify({type:'WELCOME',room_code:'ABC234',seat_id:'p1',reconnect_token:'token'})})
 socket.close();vi.advanceTimersByTime(800)
 socket=FakeSocket.instances.at(-1)!;socket.readyState=1;socket.emit('open')
 expect(statuses.at(-1)).toBe('reconnecting')
 socket.emit('message',{data:JSON.stringify({type:'WELCOME',room_code:'ABC234',seat_id:'p1',reconnect_token:'token'})})
 expect(statuses.at(-1)).toBe('reconnecting')
 socket.emit('message',{data:JSON.stringify({type:'PROJECTION_UPDATE',projection:{}})})
 expect(statuses.at(-1)).toBe('connected')
 socket.close()
 for(let i=0;i<5;i++) { vi.advanceTimersByTime(8000);socket=FakeSocket.instances.at(-1)!; if(socket.readyState===0){socket.readyState=1;socket.emit('open')} vi.advanceTimersByTime(8000) }
 expect(statuses.at(-1)).toBe('offline')
 connection.disconnect();vi.useRealTimers();vi.unstubAllGlobals()
})
