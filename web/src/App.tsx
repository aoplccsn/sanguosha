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
    {state.connection === 'reconnecting' && <div role="status" className="connection-banner">连接中断，正在重新连接…</div>}
    {state.connection === 'offline' && <div role="alert" className="connection-banner">网络暂不可用，仍在尝试重新连接…</div>}
    {state.error.includes('服务器已重新启动') && <div role="alert" className="connection-banner">
      {state.error} <button onClick={actions.returnHome}>返回首页</button>
    </div>}
    {page}
  </>
}
