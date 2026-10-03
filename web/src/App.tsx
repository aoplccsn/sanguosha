import { HomePage } from './components/HomePage'
import { LobbyPage } from './components/LobbyPage'
import { PregamePage } from './components/PregamePage'
import { GamePage } from './components/GamePage'
import { GodShowcase } from './components/GodShowcase'
import { useGame } from './state/GameContext'
import './styles.css'
import './god-lvbu-motion.css'

export default function App() {
  const { state, actions } = useGame()
  if (import.meta.env.DEV && window.location.pathname === '/t11/god-lvbu-preview') return <GodShowcase />
  const page = state.page === 'lobby' ? <LobbyPage />
    : state.page === 'pregame' ? <PregamePage />
      : state.page === 'game' ? <GamePage /> : <HomePage />
  return <>
    {state.page !== 'home' && state.connection === 'reconnecting' && <div role="status" className="connection-banner">连接波动，正在恢复…</div>}
    {state.page !== 'home' && state.connection === 'offline' && <div role="alert" className="connection-banner">无法连接到房间，仍在尝试恢复…</div>}
    {state.notice && <div role="status" className="game-notice">{state.notice}</div>}
    {state.error.includes('服务器已重新启动') && <div role="alert" className="connection-banner">
      {state.error} <button onClick={actions.returnHome}>返回首页</button>
    </div>}
    {page}
  </>
}
