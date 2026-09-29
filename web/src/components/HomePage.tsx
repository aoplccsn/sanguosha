import { useMemo, useState } from 'react'
import { useGame } from '../state/GameContext'

function roomFromUrl() {
  const pathMatch = window.location.pathname.match(/^\/room\/([A-Z0-9]+)/i)
  return (pathMatch?.[1] ?? new URLSearchParams(window.location.search).get('room') ?? '').toUpperCase()
}

export function HomePage() {
  const { state, actions } = useGame()
  const initialRoom = useMemo(roomFromUrl, [])
  const [name, setName] = useState(localStorage.getItem('sanguosha.web.nickname') ?? '')
  const [roomCode, setRoomCode] = useState(initialRoom)

  const remember = () => {
    const clean = name.trim() || '玩家'
    localStorage.setItem('sanguosha.web.nickname', clean)
    return clean
  }

  return <main className="home-page">
    <div className="ink-mist ink-mist-one" />
    <div className="ink-mist ink-mist-two" />
    <section className="home-panel paper-panel">
      <div className="seal">战</div>
      <p className="eyebrow">云端权威 · 五人身份局</p>
      <h1>三国杀</h1>
      <h2>Web Edition</h2>
      <p className="home-copy">打开网页，邀友入局。规则、身份与牌堆全部由服务器掌管。</p>
      <label className="field-label">玩家昵称
        <input aria-label="玩家昵称" maxLength={32} value={name} onChange={(event) => setName(event.target.value)} placeholder="请输入昵称" />
      </label>
      <div className="home-actions">
        <button className="brush-button primary" onClick={() => actions.createRoom(remember(), true)}>单人游戏</button>
        <button className="brush-button" onClick={() => actions.createRoom(remember())}>创建多人房间</button>
      </div>
      <div className="join-row">
        <input aria-label="房间码" value={roomCode} onChange={(event) => setRoomCode(event.target.value.toUpperCase())} placeholder="输入房间码" maxLength={8} />
        <button className="brush-button compact" disabled={!roomCode.trim()} onClick={() => actions.joinRoom(remember(), roomCode)}>加入房间</button>
      </div>
      {state.error && <div className="error-banner" role="alert">{state.error}<button onClick={actions.clearError}>×</button></div>}
      <footer>
        <span><i className={`connection-dot ${state.connection}`} /> {state.connection === 'connected' ? '服务器已连接' : '正在连接服务器'}</span>
        <span>v{__APP_VERSION__} · {__BUILD_COMMIT__.slice(0, 8)}</span>
      </footer>
    </section>
  </main>
}
