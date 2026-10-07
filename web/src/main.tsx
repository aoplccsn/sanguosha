import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { BackgroundMusic } from './components/BackgroundMusic'
import { GameProvider } from './state/GameContext'

document.documentElement.style.setProperty('--table-background',
  `url('/assets/backgrounds/table/ink_wash_v1.${import.meta.env.PROD ? 'webp' : 'png'}')`)

createRoot(document.getElementById('root')!).render(
  <StrictMode><BackgroundMusic /><GameProvider><App /></GameProvider></StrictMode>,
)
