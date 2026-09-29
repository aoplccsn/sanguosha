import { useGame } from '../state/GameContext'
import { Timer } from './Timer'

const kingdomLabel: Record<string, string> = { wei: '魏', shu: '蜀', wu: '吴', qun: '群' }
const identityLabel: Record<string, string> = { lord: '主公', loyalist: '忠臣', rebel: '反贼', renegade: '内奸' }

export function PregamePage() {
  const { state, actions } = useGame()
  const draft = state.draft
  if (!draft) return <main className="pregame-page table-background"><div className="paper-panel loading-panel">等待服务器发放武将候选……</div></main>
  const selected = state.generals[state.selectedGeneral]
  return <main className="pregame-page table-background">
    <section className="pregame-shell paper-panel">
      <header className="pregame-header">
        <div className={`identity-reveal identity-${draft.identity}`}><span>你的身份</span><strong>{identityLabel[draft.identity] ?? draft.identity}</strong></div>
        <div><p className="eyebrow">十选一</p><h1>择将入局</h1><p>先查看技能，再确认选择。点击武将不会立即锁定。</p></div>
        <Timer remainingMs={draft.request.remaining_ms} />
      </header>
      <div className="general-grid">
        {draft.request.choices.map((id) => {
          const general = state.generals[id]
          return <button key={id} className={`general-card ${state.selectedGeneral === id ? 'selected' : ''}`} onClick={() => actions.selectGeneral(id)}>
            <img src={general?.portrait ?? '/assets/generals/default_general.png'} alt={general?.name ?? id} />
            <span className={`kingdom kingdom-${general?.kingdom ?? 'qun'}`}>{kingdomLabel[general?.kingdom ?? ''] ?? '群'}</span>
            <strong>{general?.name ?? id}</strong>
            <small>{general?.max_hp ?? '?'} 体力 · {general?.skills.map((skill) => skill.name).join(' / ') || '载入中'}</small>
          </button>
        })}
      </div>
      <aside className="general-detail">
        {selected ? <>
          <img src={selected.portrait} alt={selected.name} />
          <div><h2>{selected.name}<span>{kingdomLabel[selected.kingdom]}</span></h2><p>{selected.max_hp} 体力</p>
            {selected.skills.map((skill) => <section key={skill.id}><h3>{skill.name}<em>{skill.type}</em></h3><p>{skill.description}</p></section>)}
          </div>
        </> : <p>请选择一名武将查看技能详情。</p>}
      </aside>
      <div className="pregame-actions"><button className="brush-button primary" disabled={!selected} onClick={actions.confirmGeneral}>确认武将</button></div>
    </section>
  </main>
}
