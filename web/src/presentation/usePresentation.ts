import { useEffect, useRef, useState } from 'react'
import type { PublicEvent } from '../types'
import { eventDuration, type GameSpeed } from './pacing'

// Intake is independent of the playback timer: incoming projections/events cannot
// restart the dwell time. Human decisions flush playback, never the protocol path.
export function usePresentation(events: PublicEvent[], speed: GameSpeed, humanRequest: string | undefined) {
  const queue = useRef<PublicEvent[]>([])
  const seen = useRef(new Set<PublicEvent>())
  const timer = useRef<number | undefined>(undefined)
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
    const fresh = events.filter(event => !seen.current.has(event))
    fresh.forEach(event => seen.current.add(event))
    if (seen.current.size > 1024) seen.current = new Set(events)
    if (humanRequest) {
      if (timer.current !== undefined) window.clearTimeout(timer.current)
      timer.current = undefined
      queue.current = []
      currentRef.current = null
      // The prompt is immediate; a newly received action can remain visible
      // alongside it. Thinking and queued history are always cleared.
      const action = humanRequest === 'connection-reset' ? undefined
        : [...fresh].reverse().find(event => /CardUsed|Responded|VirtualResponse/.test(String(event.kind)))
      currentRef.current = action ?? null
      setCurrent(action ?? null)
      if (action) timer.current = window.setTimeout(() => advance.current(), eventDuration(action, speedRef.current))
      return
    }
    queue.current.push(...fresh.filter(event => eventDuration(event, speedRef.current) > 0))
    if (timer.current === undefined && queue.current.length) advance.current()
  }, [events, humanRequest])
  useEffect(() => {
    if (timer.current !== undefined && currentRef.current) {
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => advance.current(), eventDuration(currentRef.current, speed))
    }
  }, [speed])
  useEffect(() => () => { if (timer.current !== undefined) window.clearTimeout(timer.current) }, [])
  return current
}
