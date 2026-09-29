import { HomePage } from './components/HomePage'
import { LobbyPage } from './components/LobbyPage'
import { PregamePage } from './components/PregamePage'
import { GamePage } from './components/GamePage'
import { useGame } from './state/GameContext'
import './styles.css'

export default function App() {
  const { state } = useGame()
  if (state.page === 'lobby') return <LobbyPage />
  if (state.page === 'pregame') return <PregamePage />
  if (state.page === 'game') return <GamePage />
  return <HomePage />
}
