import { StrictMode } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

vi.mock('../bgmAsset', () => ({ BGM_AVAILABLE: true, BGM_TRACKS: {
  lobby: '/assets/audio/bgm/lobby_bgm.wav', battle: '/assets/audio/bgm/main_bgm.mp3',
} }))
const audios: any[] = []
const AudioMock = vi.fn(function () {
  const audio = { src: '', preload: '', paused: true, loop: false, muted: false, volume: 1,
    play: vi.fn(() => { audio.paused = false; return Promise.resolve() }),
    pause: vi.fn(() => { audio.paused = true }) }
  audios.push(audio)
  return audio
})
beforeEach(() => {
  vi.resetModules(); vi.useFakeTimers(); audios.length = 0; AudioMock.mockClear()
  vi.stubGlobal('Audio', AudioMock); localStorage.clear()
  Object.defineProperty(document, 'hidden', { configurable: true, value: false })
})
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })
const tick = async (ms: number) => act(async () => { await vi.advanceTimersByTimeAsync(ms) })

it('persists shared settings and reuses players across StrictMode remounts', async () => {
  const { BackgroundMusic } = await import('../components/BackgroundMusic')
  const first = render(<StrictMode><BackgroundMusic /></StrictMode>)
  expect(AudioMock).not.toHaveBeenCalled()
  fireEvent.pointerDown(document); fireEvent.keyDown(document, { key: 'Enter' })
  await tick(1999); expect(AudioMock).not.toHaveBeenCalled()
  await tick(1); expect(AudioMock).toHaveBeenCalledTimes(1)
  expect(audios[0]).toMatchObject({ preload: 'none', src: '/assets/audio/bgm/lobby_bgm.wav', loop: true, volume: .2 })
  fireEvent.change(screen.getByRole('slider'), { target: { value: '.35' } })
  fireEvent.click(screen.getByRole('button'))
  expect(audios[0].paused).toBe(true)
  first.unmount()
  render(<BackgroundMusic />)
  expect(screen.getByRole('button')).toHaveTextContent('背景音乐 关')
  expect(screen.getByRole('slider')).toHaveValue('0.35')
  fireEvent.click(screen.getByRole('button')); await tick(2000)
  expect(audios[0].muted).toBe(false)
  expect(audios[0].volume).toBe(.35)
  expect(AudioMock).toHaveBeenCalledTimes(1)
})

it('crossfades over 1200ms, handles rapid returns, and never stacks loops', async () => {
  const { BackgroundMusic } = await import('../components/BackgroundMusic')
  const view = render(<BackgroundMusic />)
  fireEvent.pointerDown(document); await tick(2000)
  view.rerender(<BackgroundMusic scene="battle" />); await tick(600)
  expect(audios).toHaveLength(2)
  expect(audios[0].volume).toBeCloseTo(.1)
  expect(audios[1].volume).toBeCloseTo(.1)
  // Normal game gestures must not restart the fade.
  fireEvent.pointerDown(document); await tick(600)
  expect(audios[0].paused).toBe(true)
  expect(audios[1].volume).toBe(.2)
  view.rerender(<BackgroundMusic />); await tick(320)
  view.rerender(<BackgroundMusic scene="battle" />); await tick(240)
  view.rerender(<BackgroundMusic />); await tick(1240)
  expect(audios[0].volume).toBe(.2); expect(audios[1].paused).toBe(true)
  expect(AudioMock).toHaveBeenCalledTimes(2)
  view.rerender(<BackgroundMusic scene="battle" />); await tick(400)
  fireEvent.click(screen.getByRole('button')); await tick(2000)
  expect(audios.every(a => a.paused && a.muted)).toBe(true)
  view.rerender(<BackgroundMusic />); await tick(2500)
  expect(audios.every(a => a.paused)).toBe(true)
})

it('pauses hidden and does not create another player on reconnect', async () => {
  const { BackgroundMusic } = await import('../components/BackgroundMusic')
  const view = render(<BackgroundMusic scene="battle" />)
  fireEvent.keyDown(document); await tick(2000)
  Object.defineProperty(document, 'hidden', { configurable: true, value: true })
  fireEvent(document, new Event('visibilitychange')); await tick(5000)
  expect(audios[0].paused).toBe(true)
  view.rerender(<BackgroundMusic scene="battle" />)
  Object.defineProperty(document, 'hidden', { configurable: true, value: false })
  fireEvent(document, new Event('visibilitychange')); await tick(40)
  expect(audios[0].paused).toBe(false); expect(AudioMock).toHaveBeenCalledTimes(1)
})

it('retries rejected autoplay and cancels a late accepted play after mute', async () => {
  const { BackgroundMusic } = await import('../components/BackgroundMusic')
  render(<BackgroundMusic />)
  fireEvent.pointerDown(document); await tick(2000)
  audios[0].pause()
  audios[0].play.mockRejectedValueOnce(new Error('autoplay'))
  fireEvent.pointerDown(document); await tick(2000)
  expect(audios[0].paused).toBe(true)
  let accept!: () => void
  audios[0].play.mockImplementationOnce(() => new Promise<void>(resolve => { accept = () => { audios[0].paused = false; resolve() } }))
  fireEvent.pointerDown(document); await tick(2000)
  fireEvent.click(screen.getByRole('button'))
  await act(async () => accept())
  expect(audios[0].paused).toBe(true)
})

it('ships both tracks and excludes the uncompressed battle source', () => {
  for (const name of ['main_bgm.mp3', 'lobby_bgm.wav']) {
    expect(existsSync(resolve(process.cwd(), '../assets/audio/bgm', name))).toBe(true)
    expect(existsSync(resolve(process.cwd(), 'public/assets/audio/bgm', name))).toBe(true)
  }
  expect(existsSync(resolve(process.cwd(), 'public/assets/audio/bgm/main_bgm.wav'))).toBe(false)
})
