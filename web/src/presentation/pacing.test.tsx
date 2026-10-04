import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { eventDuration, presentationPacing } from './pacing'
import { usePresentation } from './usePresentation'
import type { PublicEvent } from '../types'
afterEach(() => vi.useRealTimers())
const events = [1,2,3].map(n => ({event_id: String(n), kind:'CardUsedEvent'})) as PublicEvent[]
it('uses three ordered tiers only for semantic actions', () => {
  for (const kind of ['CardUsedEvent','SkillEvent','DamageDealtEvent','HpRecoveredEvent','JudgmentEvent','CardRespondedEvent','VirtualResponseEvent','DyingRequiredEvent','DiscardEvent','TurnStartedEvent']) {
    const event = {kind} as PublicEvent
    expect(eventDuration(event,'slow')).toBeGreaterThan(eventDuration(event,'normal'))
    expect(eventDuration(event,'normal')).toBeGreaterThan(eventDuration(event,'fast'))
  }
  expect(eventDuration({kind:'ProjectionUpdate'} as PublicEvent,'normal')).toBe(0)
})
it('holds key actions for the requested three speeds', () => {
  const card = { kind: 'CardUsedEvent' } as PublicEvent
  expect(eventDuration(card, 'slow')).toBe(3000)
  expect(eventDuration(card, 'normal')).toBe(2000)
  expect(eventDuration(card, 'fast')).toBe(900)
})
it('keeps event spacing when new events arrive, then immediately flushes for a human', () => {
  vi.useFakeTimers()
  const {result, rerender} = renderHook(({items,human}:{items:PublicEvent[],human?:string}) => usePresentation(items,'normal',human),{initialProps:{items:events.slice(0,2),human:undefined as string|undefined}})
  expect(result.current?.event_id).toBe('1')
  act(()=>vi.advanceTimersByTime(500))
  rerender({items:events,human:undefined})
  act(()=>vi.advanceTimersByTime(presentationPacing.normal.key-500))
  expect(result.current?.event_id).toBe('2')
  rerender({items:events,human:'human-response'})
  expect(result.current).toBeNull()
  act(()=>vi.advanceTimersByTime(10000))
  expect(result.current).toBeNull()
})
it('plays already queued events even if the retained public history rolls over', () => {
  vi.useFakeTimers()
  const {result,rerender}=renderHook(({items})=>usePresentation(items,'fast',undefined),{initialProps:{items:events}})
  rerender({items:[events[2]]})
  act(()=>vi.advanceTimersByTime(presentationPacing.fast.key))
  expect(result.current?.event_id).toBe('2')
})
