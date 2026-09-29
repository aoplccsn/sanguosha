import { HomePage } from './components/HomePage'
import { LobbyPage } from './components/LobbyPage'
import { PregamePage } from './components/PregamePage'
import { useGame } from './state/GameContext'
import './styles.css'

function GamePlaceholder() {
  const { state } = useGame()
  return <main className="table-background placeholder-page"><section className="paper-panel"><h1>牌桌正在展开</h1><p>第 {state.projection?.turn_number ?? 0} 回合 · {state.projection?.current_phase ?? '准备'}</p></section></main>
}

export default function App() {
  const { state } = useGame()
  if (state.page === 'lobby') return <LobbyPage />
  if (state.page === 'pregame') return <PregamePage />
  if (state.page === 'game') return <GamePlaceholder />
  return <HomePage />
}
