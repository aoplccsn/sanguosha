import { StrictMode } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { BackgroundMusic } from '../components/BackgroundMusic'

vi.mock('../bgmAsset', () => ({ BGM_AVAILABLE: true, BGM_URL: '/assets/audio/bgm/main_bgm.mp3' }))
const audio = { src: '', preload: '', paused: true, loop: false, muted: false, volume: 1,
  play: vi.fn(() => { audio.paused = false; return Promise.resolve() }),
  pause: vi.fn(() => { audio.paused = true }) }
const AudioMock = vi.fn(function () { return audio })
vi.stubGlobal('Audio', AudioMock)
beforeEach(() => { localStorage.clear() })

it('persists mute and volume and reuses one player across gestures and remounts', () => {
  vi.useFakeTimers()
  const first = render(<StrictMode><BackgroundMusic /></StrictMode>)
  expect(AudioMock).not.toHaveBeenCalled()
  fireEvent.pointerDown(document)
  fireEvent.keyDown(document, { key: 'Enter' })
  vi.advanceTimersByTime(1999)
  expect(AudioMock).not.toHaveBeenCalled()
  vi.advanceTimersByTime(1)
  expect(AudioMock).toHaveBeenCalledTimes(1)
  expect(audio.preload).toBe('none')
  expect(audio.src).toBe('/assets/audio/bgm/main_bgm.mp3')
  expect(audio.loop).toBe(true)
  expect(audio.volume).toBe(0.2)
  fireEvent.change(screen.getByRole('slider'), { target: { value: '0.35' } })
  fireEvent.click(screen.getByRole('button'))
  vi.advanceTimersByTime(2000)
  expect(JSON.parse(localStorage.getItem('sanguosha.bgm')!)).toEqual({ muted: true, volume: 0.35 })
  first.unmount()
  render(<BackgroundMusic />)
  expect(screen.getByRole('button')).toHaveTextContent('背景音乐 关')
  expect(screen.getByRole('slider')).toHaveValue('0.35')
  fireEvent.keyDown(document, { key: 'Enter' })
  fireEvent.click(screen.getByRole('button'))
  vi.advanceTimersByTime(2000)
  expect(audio.muted).toBe(false)
  expect(AudioMock).toHaveBeenCalledTimes(1)
  vi.useRealTimers()
})

const source = resolve(process.cwd(), '../assets/audio/bgm/main_bgm.mp3')
it.skipIf(!existsSync(source))('ships the supplied BGM through the existing assets pipeline', () => {
  expect(existsSync(resolve(process.cwd(), 'public/assets/audio/bgm/main_bgm.mp3'))).toBe(true)
  expect(existsSync(resolve(process.cwd(), 'public/assets/audio/bgm/main_bgm.wav'))).toBe(false)
})
