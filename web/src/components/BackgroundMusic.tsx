import { useEffect, useState } from 'react'
import { BGM_AVAILABLE, BGM_URL } from '../bgmAsset'

const STORAGE_KEY = 'sanguosha.bgm'
let player: HTMLAudioElement | undefined
let interacted = false
let startTimer: ReturnType<typeof setTimeout> | undefined

function audioPlayer() {
  if (!player) {
    player = new Audio()
    player.preload = 'none'
    player.loop = true
  }
  return player
}

function requestPlayback() {
  const current = preferences()
  if (current.muted || startTimer !== undefined || (player && !player.paused)) return
  // Give portraits and the page entered by this gesture a head start.
  startTimer = setTimeout(() => {
    startTimer = undefined
    const latest = preferences()
    if (latest.muted) return
    const node = audioPlayer()
    node.volume = latest.volume
    node.muted = latest.muted
    if (!node.src) node.src = BGM_URL
    void node.play().catch(() => {})
  }, 2000)
}

function preferences(): { muted: boolean; volume: number } {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    return { muted: saved.muted === true,
      volume: typeof saved.volume === 'number' && Number.isFinite(saved.volume)
        ? Math.max(0, Math.min(1, saved.volume)) : 0.2 }
  } catch { return { muted: false, volume: 0.2 } }
}

export function BackgroundMusic() {
  const [settings, setSettings] = useState(preferences)
  useEffect(() => {
    if (!BGM_AVAILABLE) return
    const start = () => {
      interacted = true
      requestPlayback()
    }
    // Keep these listeners so a later gesture can retry a browser-rejected play.
    document.addEventListener('pointerdown', start)
    document.addEventListener('keydown', start)
    if (interacted) start()
    return () => {
      document.removeEventListener('pointerdown', start)
      document.removeEventListener('keydown', start)
    }
  }, [])

  const update = (next: typeof settings) => {
    setSettings(next)
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) } catch { /* Session settings still apply. */ }
    if (!BGM_AVAILABLE) return
    interacted = true
    if (player) {
      player.volume = next.volume
      player.muted = next.muted
    }
    if (next.muted) {
      if (startTimer !== undefined) clearTimeout(startTimer)
      startTimer = undefined
      player?.pause()
    } else requestPlayback()
  }

  return <div className="background-music">
    <button disabled={!BGM_AVAILABLE} aria-pressed={!settings.muted && BGM_AVAILABLE}
      title='背景音乐开关'
      onClick={() => update({ ...settings, muted: !settings.muted })}>
      背景音乐 {settings.muted ? '关' : '开'}
    </button>
    {BGM_AVAILABLE && <input aria-label="背景音乐音量" type="range" min="0" max="1" step="0.05"
      value={settings.volume} onChange={event => update({ ...settings, volume: Number(event.target.value) })} />}
  </div>
}
