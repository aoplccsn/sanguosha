import { NetworkDiagnostics } from './components/NetworkDiagnostics'
import { HomePage } from './components/HomePage'
import { LobbyPage } from './components/LobbyPage'
import { PregamePage } from './components/PregamePage'
import { GamePage } from './components/GamePage'
import { GodShowcase } from './components/GodShowcase'
import { useGame } from './state/GameContext'
import './styles.css'
import './god-lvbu-motion.css'

export default function App() {
  const { state, connection } = useGame()
  if (window.location.pathname === '/network-diagnostics') return <NetworkDiagnostics />
  if (import.meta.env.DEV && window.location.pathname === '/t11/god-lvbu-preview') return <GodShowcase />
  const page = state.page === 'lobby' ? <LobbyPage />
    : state.page === 'pregame' ? <PregamePage />
      : state.page === 'game' ? <GamePage /> : <HomePage />
  return <>
    {state.page !== 'home' && state.connection === 'reconnecting' && <div role="status" className="connection-banner">连接波动，正在恢复…</div>}
    {state.connection === 'offline' && <div role="alert" className="connection-banner">无法建立实时连接。<button onClick={() => connection.retry()}>重新检测</button> <a href="/network-diagnostics" target="_blank" rel="noreferrer">网络诊断</a></div>}
    {state.notice && <div role="status" className="game-notice">{state.notice}</div>}
    {page}
  </>
}
