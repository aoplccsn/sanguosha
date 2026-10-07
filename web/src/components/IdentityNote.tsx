import { useState } from 'react'
import type { PlayerView } from '../types'

export function IdentityNote({ roomId, localId, player }: { roomId: string; localId: string; player: PlayerView }) {
  const key = `sanguosha.identity-note.v1:${roomId}:${localId}:${player.player_id}`
  const [note, setNote] = useState(() => {
    try { return localStorage.getItem(key) ?? '' } catch { return '' }
  })
  const [open, setOpen] = useState(false)
  if (!roomId || player.player_id === localId || !player.alive || player.identity_label !== '未知') return null
  function choose(value: string) {
    setNote(value); setOpen(false)
    try { if (value) localStorage.setItem(key, value); else localStorage.removeItem(key) } catch { /* Personal notes remain usable in memory. */ }
  }
  return <div className="identity-note" onClick={event => event.stopPropagation()}>
    <button className="identity-note-trigger" aria-label={`我的身份猜测：${player.name}`} aria-expanded={open} onClick={() => setOpen(!open)}><span>{note ? `${note}？` : '标记'}</span></button>
    {open && <div className="identity-note-menu" aria-label="我的身份猜测">{[['忠','忠臣'],['反','反贼'],['内','内奸'],['','清除']].map(([value,label]) => <button key={label} onClick={() => choose(value)}>{label}</button>)}</div>}
  </div>
}
