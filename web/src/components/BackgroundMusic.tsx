import { useEffect, useState } from 'react'
import { BGM_AVAILABLE, BGM_TRACKS, type BgmScene } from '../bgmAsset'

const STORAGE_KEY = 'sanguosha.bgm'
const players: Partial<Record<BgmScene, HTMLAudioElement>> = {}
const gains: Record<BgmScene, number> = { lobby: 0, battle: 0 }
let interacted = false
let desired: BgmScene = 'lobby'
let startTimer: ReturnType<typeof setTimeout> | undefined
let fadeTimer: ReturnType<typeof setInterval> | undefined
let generation = 0
let pending: BgmScene | undefined
let mounted = false

function preferences(): { muted: boolean; volume: number } {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    return { muted: saved.muted === true,
      volume: typeof saved.volume === 'number' && Number.isFinite(saved.volume)
        ? Math.max(0, Math.min(1, saved.volume)) : 0.2 }
  } catch { return { muted: false, volume: 0.2 } }
}
let settings = preferences()

function applyVolumes() {
  for (const scene of ['lobby', 'battle'] as const) {
    const node = players[scene]
    if (node) { node.volume = settings.volume * gains[scene]; node.muted = settings.muted }
  }
}
function cancelTransition() {
  generation++
  pending = undefined
  clearTimeout(startTimer); startTimer = undefined
  clearInterval(fadeTimer); fadeTimer = undefined
}
function pauseAll() {
  cancelTransition()
  Object.values(players).forEach(node => node.pause())
}
function audioPlayer(scene: BgmScene) {
  if (!players[scene]) {
    const node = new Audio()
    node.preload = 'none'; node.loop = true; node.src = BGM_TRACKS[scene]
    players[scene] = node
  }
  return players[scene]!
}
function requestPlayback(delay = 0) {
  if (!BGM_AVAILABLE || !interacted || settings.muted || document.hidden || pending === desired || startTimer !== undefined) return
  if (players[desired] && !players[desired]!.paused) {
    if (fadeTimer !== undefined) return
    if (gains[desired] === 1) {
      const other: BgmScene = desired === 'lobby' ? 'battle' : 'lobby'
      gains[other] = 0; players[other]?.pause(); applyVolumes()
      return
    }
  }
  cancelTransition()
  const token = generation
  startTimer = setTimeout(() => {
    startTimer = undefined
    if (token !== generation || settings.muted || document.hidden) return
    const scene = desired
    const node = audioPlayer(scene)
    const other: BgmScene = scene === 'lobby' ? 'battle' : 'lobby'
    const hasOutgoing = players[other] && !players[other]!.paused && gains[other] > 0
    if (!hasOutgoing) { gains[scene] = 1; gains[other] = 0; players[other]?.pause() }
    applyVolumes()
    pending = scene
    // Only fade the previous track once the browser has accepted the new play.
    void node.play().then(() => {
      if (token !== generation) {
        if (!mounted || settings.muted || document.hidden || gains[scene] === 0) node.pause()
        return
      }
      pending = undefined
      const initial = { ...gains }
      const started = Date.now()
      if (!hasOutgoing) return
      fadeTimer = setInterval(() => {
        const progress = Math.min(1, (Date.now() - started) / 1200)
        gains[scene] = initial[scene] + (1 - initial[scene]) * progress
        gains[other] = initial[other] * (1 - progress)
        applyVolumes()
        if (progress === 1) {
          players[other]?.pause()
          clearInterval(fadeTimer); fadeTimer = undefined
        }
      }, 40)
    }).catch(() => {
      if (token === generation) pending = undefined
      // A subsequent user gesture retries an autoplay rejection.
    })
  }, delay)
}

export function BackgroundMusic({ scene = 'lobby' }: { scene?: BgmScene }) {
  const [current, setCurrent] = useState(preferences)
  useEffect(() => {
    desired = scene
    settings = preferences()
    cancelTransition()
    applyVolumes()
    requestPlayback(Object.values(players).some(node => !node.paused) ? 0 : 2000)
  }, [scene])
  useEffect(() => {
    mounted = true
    if (!BGM_AVAILABLE) return
    const start = () => {
      interacted = true
      requestPlayback(Object.values(players).some(node => !node.paused) ? 0 : 2000)
    }
    const visibility = () => { if (document.hidden) pauseAll(); else requestPlayback() }
    document.addEventListener('pointerdown', start)
    document.addEventListener('keydown', start)
    document.addEventListener('visibilitychange', visibility)
    if (interacted) requestPlayback(2000)
    return () => {
      mounted = false
      document.removeEventListener('pointerdown', start)
      document.removeEventListener('keydown', start)
      document.removeEventListener('visibilitychange', visibility)
      pauseAll()
    }
  }, [])

  const update = (next: typeof current) => {
    setCurrent(next); settings = next
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) } catch { /* Session settings still apply. */ }
    interacted = true
    applyVolumes()
    if (next.muted) pauseAll()
    else requestPlayback(2000)
  }

  return <div className="background-music" data-scene={scene}>
    <button disabled={!BGM_AVAILABLE} aria-pressed={!current.muted && BGM_AVAILABLE}
      title="背景音乐开关" onClick={() => update({ ...current, muted: !current.muted })}>
      背景音乐 {current.muted ? '关' : '开'}
    </button>
    {BGM_AVAILABLE && <input aria-label="背景音乐音量" type="range" min="0" max="1" step="0.05"
      value={current.volume} onChange={event => update({ ...current, volume: Number(event.target.value) })} />}
  </div>
}
