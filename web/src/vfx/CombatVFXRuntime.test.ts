import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CombatVFXRuntime, readVfxQuality, saveVfxQuality } from './CombatVFXRuntime'

const context = {
  setTransform: vi.fn(), clearRect: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(),
  lineTo: vi.fn(), stroke: vi.fn(), arc: vi.fn(), fill: vi.fn(), ellipse: vi.fn(),
}
let nextFrame: FrameRequestCallback | undefined
let frameId = 0
let cancelled: number[] = []

function boardWithPlayers() {
  const board = document.createElement('div')
  board.className = 'game-board'
  for (const [id, x] of [['p1', 100], ['p2', 350]] as const) {
    const player = document.createElement('article')
    player.dataset.playerId = id
    player.className = id === 'p1' ? 'player-self' : ''
    const portrait = document.createElement('button')
    portrait.className = 'portrait-button'
    portrait.getBoundingClientRect = () => ({ left: x, top: 50, width: 60, height: 80 } as DOMRect)
    player.append(portrait)
    board.append(player)
  }
  board.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 600 } as DOMRect)
  const canvas = document.createElement('canvas')
  board.append(canvas)
  document.body.append(board)
  return { board, canvas }
}

describe('CombatVFXRuntime', () => {
  beforeEach(() => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context as unknown as CanvasRenderingContext2D)
    vi.stubGlobal('matchMedia', () => ({ matches: false }))
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => { nextFrame = callback; return ++frameId })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => { cancelled.push(id) })
    Object.defineProperty(document, 'hidden', { configurable: true, value: false })
  })
  afterEach(() => {
    document.body.innerHTML = ''
    nextFrame = undefined
    cancelled = []
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('keeps one animation loop for beam and effects and releases it on teardown', () => {
    const { board, canvas } = boardWithPlayers()
    const runtime = new CombatVFXRuntime(canvas, board, 'medium')
    runtime.setBeam(['p2'], 'attack')
    const scheduled = frameId
    runtime.trigger('slash', 'p1', 'p2')
    expect(frameId).toBe(scheduled)
    nextFrame?.(performance.now() + 20)
    expect(context.lineTo).toHaveBeenCalled()
    runtime.destroy()
    expect(cancelled).toContain(frameId)
  })

  it('pauses on a hidden tab and clears pending effects', () => {
    const { board, canvas } = boardWithPlayers()
    const runtime = new CombatVFXRuntime(canvas, board, 'low')
    runtime.trigger('impact', 'p1', 'p2')
    const active = frameId
    Object.defineProperty(document, 'hidden', { configurable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(cancelled).toContain(active)
    runtime.destroy()
  })

  it('persists the selected quality without accepting unknown values', () => {
    saveVfxQuality('high')
    expect(readVfxQuality()).toBe('high')
    localStorage.setItem('sanguosha.vfx.quality.v1', 'unknown')
    expect(readVfxQuality()).toBe('medium')
  })
})
