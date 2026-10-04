import { useEffect, useMemo, useState } from 'react'
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
  const [modeId, setModeId] = useState<'military-five' | 'military-eight'>('military-five')
  const [allowGods, setAllowGods] = useState(false)
  const [entering, setEntering] = useState(false)

  useEffect(() => { if (state.error || state.connection === 'offline' || state.connection === 'fatal') setEntering(false) }, [state.error, state.connection])
  useEffect(() => {
    if (!state.error) return
    const timer = window.setTimeout(actions.clearError, 5000)
    return () => window.clearTimeout(timer)
  }, [state.error, actions])

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
      <p className="eyebrow">云端权威 · 身份局</p>
      <h1>三国杀</h1>
      <h2>Web Edition</h2>
      <p className="home-copy">打开网页，邀友入局。规则、身份与牌堆全部由服务器掌管。</p>
      <label className="field-label">玩家昵称
        <input aria-label="玩家昵称" maxLength={32} value={name} onChange={(event) => setName(event.target.value)} placeholder="请输入昵称" />
      </label>
      <label className="field-label">对局模式
        <select aria-label="对局模式" value={modeId} onChange={(event) => setModeId(event.target.value as 'military-five' | 'military-eight')}>
          <option value="military-five">军五 · 5 人</option>
          <option value="military-eight">军八 · 8 人</option>
        </select>
      </label>
      <label className="field-label"><input type="checkbox" checked={allowGods} onChange={(event) => setAllowGods(event.target.checked)} /> 允许神将进入候选池</label>
      <div className="home-actions">
        <button className="brush-button primary" disabled={entering} onClick={() => { setEntering(true); actions.createRoom(remember(), true, modeId, allowGods) }}>{entering ? '正在进入…' : '单人游戏'}</button>
        <button className="brush-button" disabled={entering} onClick={() => { setEntering(true); actions.createRoom(remember(), false, modeId, allowGods) }}>{entering ? '正在进入…' : '创建多人房间'}</button>
      </div>
      {import.meta.env.DEV && <a className="god-preview-entry" href="/t11/god-lvbu-preview">God Lü Bu Presentation Preview · 神吕布视觉验收</a>}
      <div className="join-row">
        <input aria-label="房间码" value={roomCode} onChange={(event) => setRoomCode(event.target.value.toUpperCase())} placeholder="输入房间码" maxLength={8} />
        <button className="brush-button compact" disabled={!roomCode.trim() || entering} onClick={() => { setEntering(true); actions.joinRoom(remember(), roomCode) }}>{entering ? '正在加入…' : '加入房间'}</button>
      </div>
      {state.resumeSession && <div className="resume-panel" role="status">
        <span>检测到上次对局 · 房间 {state.resumeSession.roomCode}</span>
        <button className="brush-button compact" disabled={entering} onClick={() => { setEntering(true); actions.continueSession() }}>{entering ? '正在恢复…' : '继续对局'}</button>
        <button className="brush-button subtle compact" onClick={actions.discardSession}>放弃</button>
      </div>}
      {state.error && <div className="error-banner" role="alert">{state.error}<button onClick={actions.clearError}>×</button></div>}
      {state.updateAvailable && <div className="version-banner" role="status">新版本可用：v{state.serverVersion?.app_version}</div>}
      <a className="network-entry" href="/network-diagnostics" target="_blank" rel="noreferrer">网络诊断</a>
      <footer>
        <span><i className={`connection-dot ${state.connection}`} /> {state.connection === 'connected' ? '服务器已连接' : state.connection === 'idle' ? '等待进入房间' : '正在连接服务器'}</span>
        <span>v{__APP_VERSION__} · {__BUILD_COMMIT__.slice(0, 8)} · 协议 {state.serverVersion?.protocol_version ?? __PROTOCOL_VERSION__}</span>
      </footer>
    </section>
  </main>
}
