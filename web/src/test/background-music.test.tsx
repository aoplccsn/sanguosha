import { StrictMode } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { existsSync } from 'node:fs'
import { BackgroundMusic } from '../components/BackgroundMusic'

vi.mock('../bgmAsset', () => ({ BGM_AVAILABLE: true, BGM_URL: '/assets/audio/bgm/main_bgm.mp3' }))
const audio = { paused: true, loop: false, muted: false, volume: 1,
  play: vi.fn(() => { audio.paused = false; return Promise.resolve() }),
  pause: vi.fn(() => { audio.paused = true }) }
const AudioMock = vi.fn(function () { return audio })
vi.stubGlobal('Audio', AudioMock)
beforeEach(() => { localStorage.clear() })

it('persists mute and volume and reuses one player across gestures and remounts', () => {
  const first = render(<StrictMode><BackgroundMusic /></StrictMode>)
  expect(AudioMock).not.toHaveBeenCalled()
  fireEvent.pointerDown(document)
  expect(AudioMock).toHaveBeenCalledTimes(1)
  expect(audio.loop).toBe(true)
  expect(audio.volume).toBe(0.2)
  fireEvent.change(screen.getByRole('slider'), { target: { value: '0.35' } })
  fireEvent.click(screen.getByRole('button'))
  expect(JSON.parse(localStorage.getItem('sanguosha.bgm')!)).toEqual({ muted: true, volume: 0.35 })
  first.unmount()
  render(<BackgroundMusic />)
  expect(screen.getByRole('button')).toHaveTextContent('背景音乐 关')
  expect(screen.getByRole('slider')).toHaveValue('0.35')
  fireEvent.keyDown(document, { key: 'Enter' })
  fireEvent.click(screen.getByRole('button'))
  expect(audio.muted).toBe(false)
  expect(AudioMock).toHaveBeenCalledTimes(1)
})

const source = new URL('../../../assets/audio/bgm/main_bgm.mp3', import.meta.url)
it.skipIf(!existsSync(source))('ships the supplied BGM through the existing assets pipeline', () => {
  expect(existsSync(new URL('../../public/assets/audio/bgm/main_bgm.mp3', import.meta.url))).toBe(true)
})
