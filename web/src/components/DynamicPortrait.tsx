import { memo, useEffect, useRef, useState } from 'react'
import { defaultGeneralPortrait } from '../assets'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export type DynamicPortraitProps = {
  staticPortrait: string
  idleVideo?: string
  name: string
  quality: VfxQuality
  reducedMotion?: boolean
  paused?: boolean
  objectPosition?: string
}

export const DynamicPortrait = memo(function DynamicPortrait(props: DynamicPortraitProps) {
  // Changing character/source gives every resource its own failure and lifecycle state.
  return <PortraitMedia key={props.staticPortrait + ':' + (props.idleVideo ?? '')} {...props} />
})

function PortraitMedia({ staticPortrait, idleVideo, name, quality, reducedMotion, paused = false, objectPosition = 'center top' }: DynamicPortraitProps) {
  const host = useRef<HTMLSpanElement>(null)
  const video = useRef<HTMLVideoElement>(null)
  const [systemReduced, setSystemReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [inViewport, setInViewport] = useState(() => typeof IntersectionObserver === 'undefined')
  const [visible, setVisible] = useState(() => !document.hidden)
  const [failed, setFailed] = useState(false)
  const [ready, setReady] = useState(false)
  const [requested, setRequested] = useState(false)
  const enabled = !!idleVideo && quality !== 'low' && !(reducedMotion || systemReduced) && !failed
  const shouldPlay = enabled && inViewport && visible && !paused

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setSystemReduced(preference.matches)
    preference.addEventListener?.('change', update)
    return () => preference.removeEventListener?.('change', update)
  }, [])

  useEffect(() => {
    const update = () => setVisible(!document.hidden)
    document.addEventListener('visibilitychange', update)
    const observer = typeof IntersectionObserver === 'undefined' ? undefined : new IntersectionObserver(
      ([entry]) => setInViewport(entry.isIntersecting), { threshold: 0 })
    if (host.current) observer?.observe(host.current)
    return () => { observer?.disconnect(); document.removeEventListener('visibilitychange', update) }
  }, [])

  useEffect(() => {
    if (shouldPlay) setRequested(true)
    if (!enabled) { setRequested(false); setReady(false) }
  }, [shouldPlay, enabled])

  useEffect(() => {
    const node = video.current
    if (!node) return
    let active = true
    if (shouldPlay) {
      try {
        const promise = node.play()
        promise?.catch(() => { if (active) { setFailed(true); setReady(false) } })
      } catch { if (active) { setFailed(true); setReady(false) } }
    } else node.pause()
    return () => { active = false; node.pause() }
  }, [shouldPlay, requested])

  // Low/reduced-motion removes the element entirely, releasing its decoder.
  return <span ref={host} className="dynamic-portrait" style={{ pointerEvents: 'none' }}>
    <img src={staticPortrait} alt={name} style={{ objectPosition, pointerEvents: 'none' }}
      onError={(event) => {
        const node = event.currentTarget
        if (node.getAttribute('src') !== defaultGeneralPortrait) node.src = defaultGeneralPortrait
      }} />
    {enabled && requested && <video ref={video} src={idleVideo} poster={staticPortrait}
      autoPlay muted loop playsInline preload="metadata" aria-hidden="true"
      style={{ objectPosition, pointerEvents: 'none', opacity: ready ? 1 : 0 }}
      onPlaying={() => setReady(true)} onError={() => { setFailed(true); setReady(false) }} />}
  </span>
}
