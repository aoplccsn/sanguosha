import { HomePage } from './components/HomePage'
import { LobbyPage } from './components/LobbyPage'
import { PregamePage } from './components/PregamePage'
import { GamePage } from './components/GamePage'
import { useGame } from './state/GameContext'
import './styles.css'

export default function App() {
  const { state, actions } = useGame()
  const page = state.page === 'lobby' ? <LobbyPage />
    : state.page === 'pregame' ? <PregamePage />
      : state.page === 'game' ? <GamePage /> : <HomePage />
  return <>
    {state.connection !== 'connected' && <div role="status" className="connection-banner">连接中断，正在重新连接…</div>}
    {state.error.includes('服务器已重启') && <div role="alert" className="connection-banner">
      {state.error} <button onClick={actions.returnHome}>返回首页</button>
    </div>}
    {page}
  </>
}
