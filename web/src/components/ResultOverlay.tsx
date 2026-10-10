import { generalPortrait } from '../assets'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export function ResultOverlay({ result, identity, godVictory = false, quality = 'medium', onHome, onReplay }: { result: string; identity?: string; godVictory?: boolean; quality?: VfxQuality; onHome(): void; onReplay(): void }) {
  const won = identity === '主公' || identity === '忠臣'
    ? result.includes('主公') || result.includes('忠臣')
    : identity === '反贼' ? result.includes('反贼') : identity === '内奸' ? result.includes('内奸') : ['玩家A', '玩家B', 'A队', 'B队'].includes(identity ?? '') && result.includes(identity ?? '')
  return <div className={'result-overlay ' + (won ? 'victory' : 'defeat')} role="dialog" aria-label="对局结果"><div>
    <p className="eyebrow">对局终了 · {identity ?? '身份未知'}</p>{won && godVictory && <div className="god-result-portrait"><img src={generalPortrait('forest_god_lvbu', 'qun', {})} alt="神吕布胜利" /></div>}<h1>{won ? '胜利' : '败北'}</h1><p>{result || '本局已经结束'}</p>
    <button className="brush-button primary" onClick={onReplay}>再来一局</button>
    <button className="brush-button subtle" onClick={onHome}>返回首页</button>
  </div></div>
}
