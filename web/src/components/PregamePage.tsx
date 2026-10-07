import { useState } from 'react'
import { useGame } from '../state/GameContext'
import { DynamicPortrait } from './DynamicPortrait'
import { idlePortrait } from '../idlePortraits'
import { readVfxQuality } from '../vfx/CombatVFXRuntime'
import { Timer } from './Timer'
import { skillTypeLabel } from '../labels'
import { defaultGeneralPortrait, generalPortrait } from '../assets'

const kingdomLabel: Record<string, string> = { wei: '魏', shu: '蜀', wu: '吴', qun: '群' }
const identityLabel: Record<string, string> = { lord: '主公', loyalist: '忠臣', rebel: '反贼', renegade: '内奸' }

export function PregamePage() {
  const { state, actions } = useGame()
  const draft = state.draft
  const [search, setSearch] = useState('')
  if (!draft) return <main className="pregame-page table-background"><div className="paper-panel loading-panel">等待服务器发放武将候选……</div></main>
  if (draft.request.choices.some((id) => !state.generals[id])) return <main className="pregame-page table-background"><div className="paper-panel loading-panel">武将资料载入中……<button onClick={() => window.location.reload()}>重新载入</button></div></main>
  const selected = state.generals[state.selectedGeneral]
  const choices = draft.test_room ? draft.request.choices.filter((id) => {
    const general = state.generals[id]
    return general.name.includes(search.trim()) || general.skills.some((skill) => skill.name.includes(search.trim()))
  }) : draft.request.choices
  return <main className="pregame-page table-background">
    <section className="pregame-shell paper-panel">
      <header className="pregame-header">
        <div className={`identity-reveal identity-${draft.identity}`}><span>你的身份</span><strong>{identityLabel[draft.identity] ?? draft.identity}</strong></div>
        <div><p className="eyebrow">{draft.test_room ? "测试房 · 自选武将" : "十选一"}</p><h1>择将入局</h1><p>先查看技能，再确认选择。点击武将不会立即锁定。</p></div>
        {state.decisionAccepted === draft.request.request_id
          ? <span role="status">已确认，等待其他玩家…</span>
          : <Timer remainingMs={draft.request.remaining_ms} />}
      </header>
      {draft.test_room && <label className="field-label">搜索武将或技能
        <input aria-label="搜索武将或技能" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="输入武将名或技能名" />
      </label>}
      <div className="general-grid">
        {choices.map((id) => {
          const general = state.generals[id]
          return <button key={id} disabled={!!state.decisionProcessing || !!state.decisionAccepted} className={`general-card ${state.selectedGeneral === id ? 'selected' : ''}`} onClick={() => actions.selectGeneral(id)}>
            <img src={general ? generalPortrait(id, general.kingdom, state.generals) : defaultGeneralPortrait} alt={general?.name ?? id} />
            <span className={`kingdom kingdom-${general?.kingdom ?? 'qun'}`}>{kingdomLabel[general?.kingdom ?? ''] ?? '群'}</span>
            <strong>{general?.name ?? id}</strong>
            <small>{general?.max_hp ?? '?'} 体力 · {general?.skills.map((skill) => skill.name).join(' / ') || '载入中'}</small>
          </button>
        })}
      </div>
      <aside className="general-detail">
        {selected ? <>
          <DynamicPortrait staticPortrait={generalPortrait(selected.id, selected.kingdom, state.generals)} idleVideo={idlePortrait(selected.id)?.video} objectPosition={idlePortrait(selected.id)?.objectPosition} name={selected.name} quality={readVfxQuality()} />
          <div><h2>{selected.name}<span>{kingdomLabel[selected.kingdom]}</span></h2><p>{selected.max_hp} 体力</p>
            {selected.skills.map((skill) => <section key={skill.id}><h3>{skill.name}<em>{skillTypeLabel(skill.type)}</em></h3><p>{skill.description}</p></section>)}
          </div>
        </> : <p>请选择一名武将查看技能详情。</p>}
      </aside>
      <div className="pregame-actions"><button className="brush-button primary" disabled={!selected || !!state.decisionProcessing || !!state.decisionAccepted} onClick={actions.confirmGeneral}>{state.decisionAccepted ? '已确认' : state.decisionProcessing ? '正在提交…' : '确认武将'}</button></div>
    </section>
  </main>
}
