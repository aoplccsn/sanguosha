import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { GameProvider } from './state/GameContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode><GameProvider><App /></GameProvider></StrictMode>,
)
