import { useGame } from '../state/GameContext'

export function LobbyPage() {
  const { state, actions } = useGame()
  const lobby = state.lobby
  if (!lobby) return null
  const self = lobby.seats.find((seat) => seat.seat_id === state.seatId)
  const isHost = lobby.host_id === state.seatId
  const guestsReady = lobby.seats
    .filter((seat) => seat.controller_type === 'HUMAN' && seat.seat_id !== lobby.host_id)
    .every((seat) => seat.ready)

  const copyCode = async () => {
    await navigator.clipboard?.writeText(state.roomCode)
  }
  const copyInvite = async () => {
    await navigator.clipboard?.writeText(new URL('/room/' + state.roomCode, window.location.origin).toString())
  }

  return <main className="lobby-page table-background">
    <section className="lobby-shell paper-panel">
      <header className="lobby-header">
        <div><p className="eyebrow">群雄候场</p><h1>多人房间</h1></div>
        <div className="room-code-box"><span>房间码</span><strong>{state.roomCode}</strong><button onClick={copyCode}>复制房间码</button><button onClick={copyInvite}>复制邀请链接</button></div>
      </header>
      <div className="lobby-options">
        <label>模式 <select aria-label="房间模式" value={lobby.mode_id} disabled={!isHost || !['OPEN', 'READY'].includes(lobby.phase)} onChange={(event) => actions.configureRoom(event.target.value)}><option value="military-five">军五 · 5 人</option><option value="military-eight">军八 · 8 人</option></select></label>
      </div>
      <div className="seat-grid">
        {lobby.seats.map((seat, index) => <article className={`lobby-seat ${seat.controller_type.toLowerCase()} ${seat.connected ? '' : 'offline'}`} key={seat.seat_id}>
          <div className="seat-number">{index + 1}</div>
          <div className="seat-avatar">{seat.controller_type === 'EMPTY' ? '空' : seat.controller_type === 'AI' ? '机' : seat.player_name.slice(0, 1)}</div>
          <h3>{seat.controller_type === 'EMPTY' ? '等待入席' : seat.player_name}</h3>
          <p>{seat.controller_type === 'HUMAN' ? '真人' : seat.controller_type === 'AI' ? '电脑' : '空位'}</p>
          <div className="seat-badges">
            {seat.seat_id === lobby.host_id && <span className="host-badge">房主</span>}
            {seat.controller_type === 'HUMAN' && <span className={seat.ready || seat.seat_id === lobby.host_id ? 'ready' : 'waiting'}>{seat.seat_id === lobby.host_id ? '主持' : seat.ready ? '已准备' : '未准备'}</span>}
            {seat.controller_type !== 'EMPTY' && <span>{seat.connected ? '在线' : '断线'}</span>}
          </div>
          {isHost && seat.controller_type === 'HUMAN' && seat.seat_id !== lobby.host_id && <button className="brush-button subtle compact" onClick={() => actions.kickPlayer(seat.seat_id)}>移出</button>}
        </article>)}
      </div>
      <p className="lobby-note">开始时不足 {lobby.seat_count} 人的座位将由 AI 自动补齐。</p>
      <div className="lobby-actions">
        <button className="brush-button subtle" onClick={actions.returnHome}>返回首页</button>
        {isHost
          ? <button className="brush-button primary" disabled={!guestsReady} onClick={actions.startGame}>开始游戏</button>
          : <button className={`brush-button ${self?.ready ? 'subtle' : 'primary'}`} onClick={() => actions.setReady(!self?.ready)}>{self?.ready ? '取消准备' : '准备'}</button>}
      </div>
      {state.error && <div className="error-banner" role="alert">{state.error}</div>}
    </section>
  </main>
}
