import { useEffect, useRef, useState } from 'react'
import type { PublicEvent } from '../types'
import { eventDuration, type GameSpeed } from './pacing'

// Intake is independent of the playback timer: incoming projections/events cannot
// restart the dwell time. Human decisions flush playback, never the protocol path.
export function usePresentation(events: PublicEvent[], speed: GameSpeed, humanRequest: string | undefined, authoritativeWaiting = false) {
  const queue = useRef<PublicEvent[]>([])
  const seen = useRef(new Set<PublicEvent>())
  const timer = useRef<number | undefined>(undefined)
  const previousHuman = useRef<string | undefined>(undefined)
  const speedRef = useRef(speed)
  speedRef.current = speed
  const [current, setCurrent] = useState<PublicEvent | null>(null)
  const currentRef = useRef<PublicEvent | null>(null)
  const advance = useRef<() => void>(() => {})
  advance.current = () => {
    timer.current = undefined
    const next = queue.current.shift()
    if (!next) { currentRef.current = null; setCurrent(null); return }
    currentRef.current = next
    setCurrent(next)
    timer.current = window.setTimeout(() => advance.current(), eventDuration(next, speedRef.current))
  }
  useEffect(() => {
    const incoming = events.filter(event => !seen.current.has(event))
    // Target declaration belongs to its original reveal, not a second action.
    const fresh = incoming.filter(event => !(event.kind === 'TrickTargetsDeclaredEvent' && incoming.some(
      other => other.kind === 'CardUsedEvent' && other.root_id && other.root_id === event.root_id)))
    incoming.forEach(event => seen.current.add(event))
    if (seen.current.size > 1024) seen.current = new Set(events)
    const changedHuman = humanRequest !== previousHuman.current
    previousHuman.current = humanRequest
    if (humanRequest) {
      const newAction = [...fresh].some(event => /CardUsed|TrickTargetsDeclared|Responded|VirtualResponse|Skill/.test(String(event.kind)))
      if (!changedHuman && !newAction && humanRequest !== 'connection-reset') return
      const retained = currentRef.current
      if (timer.current !== undefined) window.clearTimeout(timer.current)
      timer.current = undefined
      queue.current = []
      currentRef.current = null
      // The prompt is immediate; a newly received action can remain visible
      // alongside it. Thinking and queued history are always cleared.
      const action = humanRequest === 'connection-reset' ? undefined
        : [...fresh].reverse().find(event => /CardUsed|TrickTargetsDeclared|Responded|VirtualResponse|Skill/.test(String(event.kind)))
          ?? (changedHuman && (/Responded|VirtualResponse/.test(String(retained?.kind)) || (retained?.definition_id && /CardUsed|TrickTargetsDeclared|Skill/.test(String(retained?.kind)))) ? retained ?? undefined : undefined)
      const reveal = action ? { ...action, presentation_phase: 'reveal' } : null
      if (reveal && Array.isArray(action?.target_ids) && action.target_ids.length) reveal.presentation_phase = 'target'
      currentRef.current = reveal
      setCurrent(reveal)
      if (action) timer.current = window.setTimeout(() => advance.current(), eventDuration(action, speedRef.current))
      return
    }
    queue.current.push(...fresh.filter(event => eventDuration(event, speedRef.current) > 0 && !(authoritativeWaiting && event.kind === 'AIThinkingEvent')).flatMap(event => {
      const reveal = { ...event, presentation_phase: /CardUsed|TrickTargetsDeclared|Skill/.test(String(event.kind)) ? 'reveal' : /Responded|VirtualResponse/.test(String(event.kind)) ? 'response' : 'result' }
      return /CardUsed|TrickTargetsDeclared|Skill/.test(String(event.kind)) && Array.isArray(event.target_ids) && event.target_ids.length
        ? [{ ...reveal, presentation_phase: 'target' }] : [reveal]
    }))
    if (timer.current === undefined && queue.current.length) advance.current()
  }, [events, humanRequest, authoritativeWaiting])
  useEffect(() => {
    if (timer.current !== undefined && currentRef.current) {
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => advance.current(), eventDuration(currentRef.current, speed))
    }
  }, [speed])
  useEffect(() => () => { if (timer.current !== undefined) window.clearTimeout(timer.current) }, [])
  return current
}
