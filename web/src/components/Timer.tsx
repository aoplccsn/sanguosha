import { useEffect, useState } from 'react'

export function Timer({ remainingMs, totalMs = remainingMs, warnAt = 5 }: { remainingMs: number; totalMs?: number; warnAt?: number }) {
  const [remaining, setRemaining] = useState(Math.max(0, remainingMs))
  useEffect(() => {
    setRemaining(Math.max(0, remainingMs))
    const started = performance.now()
    const timer = window.setInterval(() => setRemaining(Math.max(0, remainingMs - (performance.now() - started))), 100)
    return () => window.clearInterval(timer)
  }, [remainingMs])
  const seconds = Math.ceil(remaining / 1000)
  const percent = Math.max(0, Math.min(100, totalMs ? remaining / totalMs * 100 : 0))
  return <div className={`timer ${seconds <= warnAt ? 'urgent' : ''}`} aria-label={`剩余 ${seconds} 秒`}>
    <span>{(remaining / 1000).toFixed(1)}s</span><div><i style={{ width: `${percent}%` }} /></div>
  </div>
}
