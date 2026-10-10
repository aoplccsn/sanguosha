import { tryLandscape } from './LandscapeGate'
import { useEffect, useMemo, useState } from 'react'
import { useGame } from '../state/GameContext'
import type { CSSProperties } from 'react'
import { DynamicPortrait } from './DynamicPortrait'
import { idlePortrait } from '../idlePortraits'
import { generalPortrait } from '../assets'
import { readVfxQuality } from '../vfx/CombatVFXRuntime'
import { homeHeroes, homeHeroOrder, defaultHomeHero } from '../homeHero'

function roomFromUrl() {
  const pathMatch = window.location.pathname.match(/^\/room\/([A-Z0-9]+)/i)
  return (pathMatch?.[1] ?? new URLSearchParams(window.location.search).get('room') ?? '').toUpperCase()
}

export function HomePage() {
  const { state, actions } = useGame()
  const initialRoom = useMemo(roomFromUrl, [])
  const [name, setName] = useState(localStorage.getItem('sanguosha.web.nickname') ?? '')
  const [roomCode, setRoomCode] = useState(initialRoom)
  const [modeId, setModeId] = useState<'military-five' | 'military-eight' | 'duel-1v1' | 'team-2v2'>('military-five')
  const [entering, setEntering] = useState(false)
  const [showTestMode, setShowTestMode] = useState(false)
  const [testCode, setTestCode] = useState('')
  const [testAuthorized, setTestAuthorized] = useState(false)
  const [testBusy, setTestBusy] = useState(false)
  const [testError, setTestError] = useState('')
  const [showJoin, setShowJoin] = useState(!!initialRoom)
  const [heroKey, setHeroKey] = useState<string>(defaultHomeHero)
  const [departingHero, setDepartingHero] = useState<string | null>(null)
  const [visible, setVisible] = useState(() => !document.hidden)
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const visibility = () => setVisible(!document.hidden)
    const motion = () => setReducedMotion(preference.matches)
    document.addEventListener('visibilitychange', visibility)
    preference.addEventListener?.('change', motion)
    return () => {
      document.removeEventListener('visibilitychange', visibility)
      preference.removeEventListener?.('change', motion)
    }
  }, [])

  const changeHero = (next: string) => {
    if (next === heroKey || departingHero) return
    setDepartingHero(reducedMotion ? null : heroKey)
    setHeroKey(next)
  }
  useEffect(() => {
    if (!visible || reducedMotion) return
    const timer = window.setTimeout(() => {
      setDepartingHero(heroKey)
      setHeroKey(homeHeroOrder[(homeHeroOrder.indexOf(heroKey as typeof homeHeroOrder[number]) + 1) % homeHeroOrder.length])
    }, 20_000)
    return () => window.clearTimeout(timer)
  }, [heroKey, visible, reducedMotion])
  useEffect(() => {
    if (!departingHero) return
    if (!visible || reducedMotion) { setDepartingHero(null); return }
    const timer = window.setTimeout(() => setDepartingHero(null), 700)
    return () => window.clearTimeout(timer)
  }, [departingHero, visible, reducedMotion])
  useEffect(() => {
    if (!visible || reducedMotion) return
    // Preload just the next poster, never the other four video files.
    const next = homeHeroes[homeHeroOrder[(homeHeroOrder.indexOf(heroKey as typeof homeHeroOrder[number]) + 1) % homeHeroOrder.length]]
    const link = document.createElement('link')
    link.rel = 'preload'; link.as = 'image'; link.href = generalPortrait(next.id, 'qun', {})
    document.head.appendChild(link)
    return () => link.remove()
  }, [heroKey, visible, reducedMotion])

  const authorizeTest = async () => {
    setTestBusy(true)
    setTestError('')
    try {
      const response = await fetch('/api/test-mode/authorize', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: testCode }),
      })
      if (!response.ok) throw new Error('access denied')
      setTestCode('')
      setTestAuthorized(true)
    } catch { setTestError('测试权限码无效或测试入口未启用。') }
    finally { setTestBusy(false) }
  }

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

  const hero = homeHeroes[heroKey]
  const heroIndex = homeHeroOrder.indexOf(heroKey as typeof homeHeroOrder[number])
  return <main className="home-page" data-hero={heroKey}
    style={{ '--hero-accent': hero.accent, '--hero-light': hero.light, '--scene-position': hero.scenePosition } as CSSProperties}>
    <div className="celestial-haze" aria-hidden="true" />
    {[departingHero, heroKey].filter((key): key is string => !!key).map(key => {
      const portrait = homeHeroes[key]
      return <div key={key} className={`home-hero ${key === departingHero ? 'hero-departing' : departingHero ? 'hero-arriving' : ''}`} aria-hidden="true">
        <DynamicPortrait staticPortrait={generalPortrait(portrait.id, 'qun', {})} idleVideo={idlePortrait(portrait.id)?.video}
          objectPosition={portrait.heroPosition} name={portrait.name} quality={readVfxQuality()} reducedMotion={reducedMotion} paused={key !== heroKey} />
      </div>
    })}
    <nav className="hero-controls" aria-label="首页神将轮换">
      <button aria-label="上一位神将" disabled={!!departingHero} onClick={() => changeHero(homeHeroOrder[(heroIndex + 4) % 5])}>‹</button>
      <div className="hero-dots">{homeHeroOrder.map(key => <button key={key} aria-label={`显示${homeHeroes[key].name}`}
        aria-pressed={key === heroKey} disabled={!!departingHero} onClick={() => changeHero(key)} />)}</div>
      <button aria-label="下一位神将" disabled={!!departingHero} onClick={() => changeHero(homeHeroOrder[(heroIndex + 1) % 5])}>›</button>
      <span>{hero.name}</span>
    </nav>
    <div className="ink-mist ink-mist-one" />
    <div className="ink-mist ink-mist-two" />
    <section className="home-panel paper-panel">
      <div className="seal">战</div>
      <p className="eyebrow">山河将起 · 群雄入局</p>
      <h1>三国杀</h1>
      <h2>Web Edition</h2>
      <p className="home-copy">执牌入局，与天下群雄一决高下。</p>
      <div className="player-plaque">
      <label className="field-label">玩家昵称
        <input aria-label="玩家昵称" maxLength={32} value={name} onChange={(event) => setName(event.target.value)} placeholder="请输入昵称" />
      </label>
      <label className="field-label">对局模式
        <select aria-label="对局模式" value={modeId} onChange={(event) => setModeId(event.target.value as 'military-five' | 'military-eight' | 'duel-1v1' | 'team-2v2')}>
          <option value="military-five">军五 · 5 人</option>
          <option value="military-eight">军八 · 8 人</option><option value="duel-1v1">1v1 对决 · 2 人</option><option value="team-2v2">2v2 小队战 · 4 人</option>
        </select>
      </label>
      </div>
      <div className="home-actions">
        <button className="brush-button primary" disabled={entering} onClick={() => { setEntering(true); void tryLandscape(); actions.createRoom(remember(), true, modeId) }}>{entering ? '正在进入…' : '单人游戏'}</button>
        <button className="brush-button" disabled={entering} onClick={() => { setEntering(true); actions.createRoom(remember(), false, modeId) }}>{entering ? '正在进入…' : '创建多人房间'}</button>
      </div>
      <details className="home-tools"><summary>更多工具</summary>
      <div className="test-mode-panel">
        <button type="button" className="brush-button subtle compact" onClick={() => setShowTestMode(!showTestMode)}>测试模式</button>
        {showTestMode && (testAuthorized ? <div>
          <span role="status">测试授权已通过，可自选武将。</span>
          <button className="brush-button compact" disabled={entering} onClick={() => { setEntering(true); void tryLandscape(); actions.createRoom(remember(), true, modeId, true) }}>创建测试房</button>
        </div> : <form onSubmit={(event) => { event.preventDefault(); void authorizeTest() }}>
          <label>测试权限码 <input aria-label="测试权限码" type="password" autoComplete="off" value={testCode} onChange={(event) => setTestCode(event.target.value)} /></label>
          <button className="brush-button compact" disabled={testBusy || !testCode} type="submit">验证</button>
          {testError && <span role="alert">{testError}</span>}
        </form>)}
      </div>
      {import.meta.env.DEV && <a className="god-preview-entry" href="/t11/god-lvbu-preview">God Lü Bu Presentation Preview · 神吕布视觉验收</a>}
      <a className="network-entry" href="/network-diagnostics" target="_blank" rel="noreferrer">网络诊断</a>
      <span className="build-info">v{__APP_VERSION__} · {__BUILD_COMMIT__.slice(0, 8)} · 协议 {state.serverVersion?.protocol_version ?? __PROTOCOL_VERSION__}</span>
      </details>
      <button className="join-toggle" aria-expanded={showJoin} aria-controls="home-join" onClick={() => setShowJoin(!showJoin)}>加入房间</button>
      {showJoin && <div className="join-row" id="home-join">
        <input aria-label="房间码" value={roomCode} onChange={(event) => setRoomCode(event.target.value.toUpperCase())} placeholder="输入房间码" maxLength={8} />
        <button className="brush-button compact" disabled={!roomCode.trim() || entering} onClick={() => { setEntering(true); actions.joinRoom(remember(), roomCode) }}>{entering ? '正在加入…' : '确认加入'}</button>
      </div>}
      {state.resumeSession && <div className="resume-panel" role="status">
        <span>检测到上次对局 · 房间 {state.resumeSession.roomCode}</span>
        <button className="brush-button compact" disabled={entering} onClick={() => { setEntering(true); actions.continueSession() }}>{entering ? '正在恢复…' : '继续对局'}</button>
        <button className="brush-button subtle compact" onClick={actions.discardSession}>放弃</button>
      </div>}
      {state.error && <div className="error-banner" role="alert">{state.error}<button onClick={actions.clearError}>×</button></div>}
      {state.updateAvailable && <div className="version-banner" role="status">新版本可用：v{state.serverVersion?.app_version}</div>}
      <footer>
        <span><i className={`connection-dot ${state.connection}`} /> {state.connection === 'connected' ? '服务器已连接' : state.connection === 'idle' ? '等待进入房间' : '正在连接服务器'}</span>
      </footer>
    </section>
  </main>
}
