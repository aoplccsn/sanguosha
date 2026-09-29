import { useEffect, useState } from 'react'

export function Timer({ remainingMs }: { remainingMs: number }) {
  const [remaining, setRemaining] = useState(Math.max(0, remainingMs))
  useEffect(() => {
    setRemaining(Math.max(0, remainingMs))
    const started = performance.now()
    const timer = window.setInterval(() => setRemaining(Math.max(0, remainingMs - (performance.now() - started))), 100)
    return () => window.clearInterval(timer)
  }, [remainingMs])
  const seconds = Math.ceil(remaining / 1000)
  const percent = Math.max(0, Math.min(100, remainingMs ? remaining / remainingMs * 100 : 0))
  return <div className={`timer ${seconds <= 5 ? 'urgent' : ''}`} aria-label={`剩余 ${seconds} 秒`}>
    <span>{seconds}</span><div><i style={{ width: `${percent}%` }} /></div>
  </div>
}
