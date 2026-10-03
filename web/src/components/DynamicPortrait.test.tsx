import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DynamicPortrait } from './DynamicPortrait'
import { GeneralDetailPanel } from './GamePage'

vi.mock('../idlePortraits', () => ({ idlePortrait: (id: string) => id === 'forest_god_lvbu' ? { video: '/idle.mp4' } : undefined }))
let intersects: IntersectionObserverCallback
const disconnect = vi.fn()
const play = vi.fn(() => Promise.resolve())
const pause = vi.fn()
const base = { staticPortrait: '/static.png', idleVideo: '/idle.mp4', name: '神吕布', quality: 'high' as const }
function enter(value = true) { act(() => intersects([{ isIntersecting: value } as IntersectionObserverEntry], {} as IntersectionObserver)) }
beforeEach(() => {
  vi.clearAllMocks()
  play.mockImplementation(() => Promise.resolve())
  Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, value: play })
  Object.defineProperty(HTMLMediaElement.prototype, 'pause', { configurable: true, value: pause })
  Object.defineProperty(document, 'hidden', { configurable: true, value: false })
  vi.stubGlobal('IntersectionObserver', class { constructor(cb: IntersectionObserverCallback) { intersects = cb } observe() {} disconnect = disconnect })
})
describe('native idle portrait', () => {
  it('loads only upon entering viewport, uses native loop and reveals on playing', () => {
    const { container } = render(<DynamicPortrait {...base} />)
    expect(container.querySelector('video')).toBeNull()
    enter()
    const node = container.querySelector('video')!
    expect(node).toHaveAttribute('preload', 'metadata')
    expect(node.loop && node.autoplay && node.muted && node.playsInline).toBe(true)
    expect(node.style.opacity).toBe('0')
    fireEvent.playing(node)
    expect(node.style.opacity).toBe('1')
    expect(node.style.pointerEvents).toBe('none')
    expect(screen.getByAltText('神吕布')).toHaveAttribute('src', '/static.png')
  })
  it('uses static without video', () => { const { container } = render(<DynamicPortrait {...base} idleVideo={undefined} />); enter(); expect(container.querySelector('video')).toBeNull() })
  it.each(['low', 'medium', 'high'] as const)('respects %s quality', (quality) => { const { container } = render(<DynamicPortrait {...base} quality={quality} />); enter(); expect(!!container.querySelector('video')).toBe(quality !== 'low') })
  it('uses static for reduced motion', () => { const { container } = render(<DynamicPortrait {...base} reducedMotion />); enter(); expect(container.querySelector('video')).toBeNull(); expect(play).not.toHaveBeenCalled() })
  it('responds to live system reduced-motion changes', () => {
    let update!: () => void
    const preference = { matches: false, addEventListener: vi.fn((_kind, listener) => { update = listener }), removeEventListener: vi.fn() }
    const media = vi.spyOn(window, 'matchMedia').mockReturnValue(preference as any)
    const { container, unmount } = render(<DynamicPortrait {...base} reducedMotion={false} />)
    enter(); expect(container.querySelector('video')).toBeTruthy()
    act(() => { preference.matches = true; update() })
    expect(container.querySelector('video')).toBeNull()
    act(() => { preference.matches = false; update() })
    expect(container.querySelector('video')).toBeTruthy()
    unmount(); expect(preference.removeEventListener).toHaveBeenCalled(); media.mockRestore()
  })
  it('removes decoder when quality becomes Low', () => { const { container, rerender } = render(<DynamicPortrait {...base} />); enter(); rerender(<DynamicPortrait {...base} quality="low" />); expect(container.querySelector('video')).toBeNull(); expect(pause).toHaveBeenCalled() })
  it('falls back on loading/decode error without removing static', () => { const { container } = render(<DynamicPortrait {...base} />); enter(); fireEvent.error(container.querySelector('video')!); expect(container.querySelector('video')).toBeNull(); expect(screen.getByAltText('神吕布')).toBeVisible() })
  it('catches play rejection and stays static', async () => { play.mockRejectedValue(new Error('blocked')); const { container } = render(<DynamicPortrait {...base} />); enter(); await waitFor(() => expect(container.querySelector('video')).toBeNull()); expect(screen.getByAltText('神吕布')).toBeVisible() })
  it('catches synchronous play failure', () => { play.mockImplementation(() => { throw new Error('unsupported') }); const { container } = render(<DynamicPortrait {...base} />); enter(); expect(container.querySelector('video')).toBeNull() })
  it('pauses off viewport and resumes in viewport', () => { render(<DynamicPortrait {...base} />); enter(); play.mockClear(); pause.mockClear(); enter(false); expect(pause).toHaveBeenCalled(); expect(play).not.toHaveBeenCalled(); enter(); expect(play).toHaveBeenCalledOnce() })
  it('pauses hidden and only resumes eligible portraits', () => { render(<DynamicPortrait {...base} />); enter(); play.mockClear(); Object.defineProperty(document, 'hidden', { configurable: true, value: true }); fireEvent(document, new Event('visibilitychange')); expect(pause).toHaveBeenCalled(); expect(play).not.toHaveBeenCalled(); enter(false); Object.defineProperty(document, 'hidden', { configurable: true, value: false }); fireEvent(document, new Event('visibilitychange')); expect(play).not.toHaveBeenCalled(); enter(); expect(play).toHaveBeenCalledOnce() })
  it('does not load while initially hidden', () => { Object.defineProperty(document, 'hidden', { configurable: true, value: true }); const { container } = render(<DynamicPortrait {...base} />); enter(); expect(container.querySelector('video')).toBeNull() })
  it('disconnects and ignores rejected play promises after unmount', async () => { let reject!: (reason: Error) => void; play.mockImplementation(() => new Promise<void>((_, fail) => { reject = fail })); const remove = vi.spyOn(document, 'removeEventListener'); const { unmount } = render(<DynamicPortrait {...base} />); enter(); unmount(); await act(async () => reject(new Error('abort'))); expect(disconnect).toHaveBeenCalled(); expect(remove).toHaveBeenCalledWith('visibilitychange', expect.any(Function)); expect(pause).toHaveBeenCalled() })
  it('resets failure when character source changes', () => { const { container, rerender } = render(<DynamicPortrait {...base} />); enter(); fireEvent.error(container.querySelector('video')!); rerender(<DynamicPortrait {...base} idleVideo="/next.mp4" />); enter(); expect(container.querySelector('video')).toHaveAttribute('src', '/next.mp4') })
  it('GeneralDetail uses dynamic media and stable fallback', () => { const player = { character_id: 'forest_god_lvbu', character_name: '神吕布', faction: '神', hp: 5, max_hp: 5, identity_label: '主公', skill_labels: [] } as any; const { container } = render(<GeneralDetailPanel player={player} quality="high" onClose={() => {}} />); enter(); expect(container.querySelector('video')).toBeTruthy(); fireEvent.error(container.querySelector('video')!); expect(screen.getByAltText('神吕布')).toBeVisible() })
  it('falls back from a missing static to default only once', () => { render(<DynamicPortrait {...base} idleVideo={undefined} />); const img = screen.getByAltText('神吕布'); fireEvent.error(img); expect(img).toHaveAttribute('src', '/assets/generals/default_general.png'); fireEvent.error(img); expect(img).toHaveAttribute('src', '/assets/generals/default_general.png') })
})
