import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { GameProvider } from './GameContext'

class FakeSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: FakeSocket[] = []
  readyState = 0
  sent: string[] = []
  listeners = new Map<string, Array<(event: any) => void>>()
  constructor(public url: string) { FakeSocket.instances.push(this) }
  addEventListener(kind: string, callback: (event: any) => void) {
    this.listeners.set(kind, [...(this.listeners.get(kind) ?? []), callback])
  }
  emit(kind: string, event: any = {}) { this.listeners.get(kind)?.forEach((listener) => listener(event)) }
  message(value: Record<string, unknown>) { this.emit('message', { data: JSON.stringify(value) }) }
  send(value: string) { this.sent.push(value) }
  close() { this.readyState = 3; this.emit('close') }
}

const dodge = { card_id: 'dodge-1', name: '闪', suit: '♥', rank: '2', definition_id: 'basic.dodge', category: 'basic', equipment_slot: '', details: '' }
const slash = { ...dodge, card_id: 'slash-1', name: '杀', definition_id: 'basic.slash' }
const player = { player_id: 'p1', name: '你 · 验收', character_name: '曹操', identity_label: '主公', hp: 4, max_hp: 4, hand_count: 2, alive: true, active: false, character_id: 'caocao', faction: '魏', chained: false, equipment: [], judgments: [], base_distance: null, effective_distance: null, attack_range: 1, skill_labels: [] }
const projection = { players: [player], hand: [dodge, slash], current_phase: 'play', turn_number: 1, deck_count: 100, discard_count: 0, result: null, discard_top: null, shared_cards: [] }
const response = (id: string) => ({ request_id: id, player_id: 'p1', request_type: 'respond_with_card', prompt: '请打出闪', choices: [], allowed_player_ids: [], required_definition_id: 'basic.dodge', eligible_card_ids: ['dodge-1'], allow_pass: true, min_count: 1, max_count: 1, subject_player_id: null, remaining_ms: 30000 })

beforeEach(() => {
  localStorage.clear()
  FakeSocket.instances = []
  vi.stubGlobal('WebSocket', FakeSocket)
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline'))))
})
afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })

function enterResponse(id = 'r1') {
  render(<GameProvider><App /></GameProvider>)
  const socket = FakeSocket.instances[0]
  act(() => {
    socket.readyState = FakeSocket.OPEN
    socket.emit('open')
    socket.message({ type: 'WELCOME', room_code: 'ABC234', seat_id: 'p1', reconnect_token: 'secret' })
    socket.message({ type: 'PROJECTION_UPDATE', projection })
    socket.message({ type: 'PENDING_REQUEST', request: response(id) })
  })
  return socket
}

it('first click selects, second click cancels, and illegal cards explain why', async () => {
  enterResponse()
  const card = screen.getByRole('button', { name: /闪/ })
  const confirm = screen.getByRole('button', { name: '确定' })
  await userEvent.click(card)
  expect(card).toHaveClass('selected')
  expect(confirm).toBeEnabled()
  await userEvent.click(card)
  expect(card).not.toHaveClass('selected')
  expect(confirm).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: /杀/ }))
  expect(screen.getByText('此牌不能用于当前响应')).toBeInTheDocument()
})

it('first confirm shows processing, blocks duplicates, and rejection restores action', async () => {
  const socket = enterResponse()
  await userEvent.click(screen.getByRole('button', { name: /闪/ }))
  await userEvent.click(screen.getByRole('button', { name: '确定' }))
  expect(screen.getByRole('button', { name: '正在提交…' })).toBeDisabled()
  expect(socket.sent.filter((raw) => JSON.parse(raw).type === 'SUBMIT_DECISION')).toHaveLength(1)
  act(() => socket.message({ type: 'ERROR', request_id: 'r1', message: 'rejected' }))
  expect(screen.getByRole('button', { name: '确定' })).toBeEnabled()
  expect(screen.getByText('rejected')).toBeInTheDocument()
})

it('replaced request clears selection and the next request accepts its first click', async () => {
  const socket = enterResponse()
  await userEvent.click(screen.getByRole('button', { name: /闪/ }))
  act(() => socket.message({ type: 'PENDING_REQUEST', request: response('r2') }))
  const card = screen.getByRole('button', { name: /闪/ })
  expect(card).not.toHaveClass('selected')
  expect(screen.getByRole('button', { name: '确定' })).toBeDisabled()
  await userEvent.click(card)
  expect(card).toHaveClass('selected')
  await userEvent.click(screen.getByRole('button', { name: '确定' }))
  expect(JSON.parse(socket.sent.at(-1)!).decision.request_id).toBe('r2')
})

it('projection revokes stale request and old rejection cannot overwrite the replacement', async () => {
  const socket = enterResponse()
  await userEvent.click(screen.getByRole('button', { name: /闪/ }))
  act(() => socket.message({ type: 'PROJECTION_UPDATE', active_request_id: 'r2', projection }))
  expect(screen.queryByRole('button', { name: '确定' })).not.toBeInTheDocument()
  act(() => socket.message({ type: 'PENDING_REQUEST', request: response('r2') }))
  act(() => socket.message({ type: 'ERROR', request_id: 'r1', message: 'stale request' }))
  expect(screen.getByRole('button', { name: '确定' })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: /闪/ }))
  expect(screen.getByRole('button', { name: /闪/ })).toHaveClass('selected')
  await userEvent.click(screen.getByRole('button', { name: '确定' }))
  expect(JSON.parse(socket.sent.at(-1)!).decision.request_id).toBe('r2')
})


it('clears acknowledged notices and never toasts repeated snapshots of the same request', () => {
 vi.useFakeTimers(); const socket=enterResponse()
 act(()=>{socket.message({type:'PENDING_REQUEST',request:response('r1')});socket.message({type:'PENDING_REQUEST',request:{...response('r1'),remaining_ms:10000}})})
 expect(screen.queryByText('当前响应已更新')).not.toBeInTheDocument()
 act(()=>socket.message({type:'ERROR',request_id:'r1',message:'stale request'}))
 expect(screen.getByText('当前响应已更新')).toBeInTheDocument()
 act(()=>vi.advanceTimersByTime(1200))
 expect(screen.queryByText('当前响应已更新')).not.toBeInTheDocument()
 vi.useRealTimers()
})
