import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { eventDuration, presentationPacing } from './pacing'
import { usePresentation } from './usePresentation'
import type { PublicEvent } from '../types'
afterEach(() => vi.useRealTimers())
const events = [1,2,3].map(n => ({event_id: String(n), kind:'CardUsedEvent'})) as PublicEvent[]
it('uses three ordered tiers only for semantic actions', () => {
  for (const kind of ['CardUsedEvent','SkillEvent','DamageDealtEvent','HpRecoveredEvent','JudgmentEvent','CardRespondedEvent','VirtualResponseEvent','DyingRequiredEvent','DiscardEvent']) {
    const event = {kind} as PublicEvent
    expect(eventDuration(event,'slow')).toBeGreaterThan(eventDuration(event,'normal'))
    expect(eventDuration(event,'normal')).toBeGreaterThan(eventDuration(event,'fast'))
  }
  expect(eventDuration({kind:'ProjectionUpdate'} as PublicEvent,'normal')).toBe(0)
})
it('holds key actions for the requested three speeds', () => {
  const card = { kind: 'CardUsedEvent' } as PublicEvent
  expect(eventDuration(card, 'slow')).toBe(6300)
  expect(eventDuration(card, 'normal')).toBe(4500)
  expect(eventDuration(card, 'fast')).toBe(2475)
})
it('paces actual AI decisions by complexity independently of action dwell', () => {
  for (const [complexity, duration] of [['simple', 1800], ['ordinary', 2400], ['complex', 3000]] as const) {
    const event = { kind: 'AIThinkingEvent', complexity }
    expect(eventDuration(event, 'normal')).toBe(duration)
    expect(eventDuration(event, 'slow')).toBe(Math.round(duration * 1.4))
    expect(eventDuration(event, 'fast')).toBe(Math.round(duration * .55))
  }
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

it('reveals then targets without delaying protocol state, and preserves a reveal during repeated human updates', () => {
  vi.useFakeTimers()
  const slash: PublicEvent = {kind:'CardUsedEvent',event_id:'slash',target_ids:['p2'],definition_id:'basic.slash'}
  const {result,rerender}=renderHook(({items,human}:{items:PublicEvent[],human?:string})=>usePresentation(items,'normal',human),{initialProps:{items:[slash],human:undefined as string|undefined}})
  expect(result.current?.presentation_phase).toBe('target')
  act(()=>vi.advanceTimersByTime(4400))
  expect(result.current?.event_id).toBe('slash')
  act(()=>vi.advanceTimersByTime(100))
  expect(result.current).toBeNull()
  const next = {...slash,event_id:'human-slash'}
  rerender({items:[slash,next],human:'response'})
  rerender({items:[slash,next,{kind:'BeforeDamageEvent'}],human:'response'})
  expect(result.current?.event_id).toBe('human-slash')
})
it('does not queue a second thinking delay when the server supplies live waiting state', () => {
  vi.useFakeTimers()
  const {result}=renderHook(()=>usePresentation([{kind:'AIThinkingEvent',thinking_ms:3200},{kind:'CardUsedEvent',event_id:'action'}],'normal',undefined,true))
  expect(result.current?.event_id).toBe('action')
})

it('keeps an AI response card when the next human projection arrives in a separate message', () => {
  vi.useFakeTimers()
  const response: PublicEvent = {kind:'CardRespondedEvent',event_id:'ai-dodge',definition_id:'basic.dodge'}
  const {result,rerender}=renderHook(({human}:{human?:string})=>usePresentation([response],'normal',human),{initialProps:{human:undefined as string|undefined}})
  expect(result.current?.event_id).toBe('ai-dodge')
  rerender({human:'next-play'})
  expect(result.current?.event_id).toBe('ai-dodge')
})

it('retains a Slash when the immediate human request arrives after its public event', () => {
 vi.useFakeTimers()
 const slash: PublicEvent = {kind:'CardUsedEvent',event_id:'incoming-slash',definition_id:'basic.slash',target_ids:['p2']}
 const {result,rerender}=renderHook(({human}:{human?:string})=>usePresentation([slash],'normal',human,true),{initialProps:{human:undefined as string|undefined}})
 rerender({human:'human-dodge'})
 expect(result.current?.event_id).toBe('incoming-slash')
 expect(result.current?.presentation_phase).toBe('target')
 act(()=>vi.advanceTimersByTime(4000))
 expect(result.current?.event_id).toBe('incoming-slash')
})

it('public reveals and discards survive fast snapshots and human requests, deduplicated by event ID',()=>{
 vi.useFakeTimers()
 const reveal={kind:'CardRevealedEvent',event_id:'reveal',cards:[]}
 const discard={kind:'DiscardEvent',event_id:'discard',cards:[]}
 const {result,rerender}=renderHook(({items,human}:{items:PublicEvent[],human?:string})=>usePresentation(items,'normal',human),{initialProps:{items:[reveal],human:undefined as string|undefined}})
 act(()=>vi.advanceTimersByTime(500))
 rerender({items:[{...reveal},discard],human:'new-request'})
 expect(result.current?.event_id).toBe('reveal')
 act(()=>vi.advanceTimersByTime(1500))
 expect(result.current?.event_id).toBe('discard')
 act(()=>vi.advanceTimersByTime(2000))
 expect(result.current).toBeNull()
})

it('keeps final retrial and delayed outcome visible before an actionable human prompt', () => {
  vi.useFakeTimers()
  const judged: PublicEvent = {kind:'JudgmentRevealedEvent',event_id:'final-retrial'}
  const outcome: PublicEvent = {kind:'DelayedResultEvent',event_id:'delayed-outcome',message:'skip'}
  expect(eventDuration(outcome,'fast')).toBeGreaterThan(0)
  const {result,rerender}=renderHook(({items,human}:{items:PublicEvent[],human?:string})=>usePresentation(items,'normal',human),{initialProps:{items:[judged,outcome],human:'next-request' as string|undefined}})
  expect(result.current?.event_id).toBe('final-retrial')
  act(()=>vi.advanceTimersByTime(eventDuration(judged,'normal')))
  expect(result.current?.event_id).toBe('delayed-outcome')
  rerender({items:[judged,outcome],human:'next-request'})
  expect(result.current?.event_id).toBe('delayed-outcome')
})
