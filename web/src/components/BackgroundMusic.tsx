import { useEffect, useState } from 'react'
import { BGM_AVAILABLE, BGM_URL } from '../bgmAsset'

const STORAGE_KEY = 'sanguosha.bgm'
let player: HTMLAudioElement | undefined
let interacted = false

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
      player ??= new Audio(BGM_URL)
      player.loop = true
      const current = preferences()
      player.volume = current.volume
      player.muted = current.muted
      if (!current.muted && player.paused) void player.play().catch(() => {})
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
    player ??= new Audio(BGM_URL)
    player.loop = true
    player.volume = next.volume
    player.muted = next.muted
    if (next.muted) player.pause()
    else if (player.paused) void player.play().catch(() => {})
  }

  return <div className="background-music">
    <button disabled={!BGM_AVAILABLE} aria-pressed={!settings.muted && BGM_AVAILABLE}
      title={BGM_AVAILABLE ? '背景音乐开关' : '缺少音频资源：main_bgm.mp3'}
      onClick={() => update({ ...settings, muted: !settings.muted })}>
      背景音乐 {BGM_AVAILABLE ? settings.muted ? '关' : '开' : '缺少音频'}
    </button>
    {BGM_AVAILABLE && <input aria-label="背景音乐音量" type="range" min="0" max="1" step="0.05"
      value={settings.volume} onChange={event => update({ ...settings, volume: Number(event.target.value) })} />}
  </div>
}
