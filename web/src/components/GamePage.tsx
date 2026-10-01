import { useEffect, useState } from 'react'
import type { CardView, GeneralInfo, PendingRequest, PlayerView, PublicEvent, PortraitState } from '../types'
import { useGame } from '../state/GameContext'
import { Timer } from './Timer'
import { CombatVFXLayer } from './CombatVFXLayer'
import { GodPortrait, type GodPortraitMode } from './GodPortrait'
import { readVfxQuality, saveVfxQuality, type VfxQuality } from '../vfx/CombatVFXRuntime'

const positions = ['north-west', 'north', 'north-east', 'east']
const phaseNames: Record<string, string> = {
  start: '开始', judgment: '判定', draw: '摸牌', play: '出牌', discard: '弃牌', finish: '结束',
}

function assetForCard(card: CardView) {
  if (card.definition_id === 'basic.slash') return '/assets/cards/basic/slash.png'
  if (card.definition_id === 'basic.dodge') return '/assets/cards/basic/dodge.png'
  if (card.definition_id === 'basic.peach') return '/assets/cards/basic/peach.png'
  if (/^(basic|trick|delayed)\./.test(card.definition_id)) {
    return '/assets/cards/military/' + card.definition_id + '.png'
  }
  if (card.definition_id.startsWith('equipment.')) {
    return '/assets/cards/military/' + card.definition_id + '-v2.png'
  }
  return '/assets/cards/default_card.png'
}

function portraitFor(player: PlayerView) {
  const kingdom = ({ 魏: 'wei', 蜀: 'shu', 吴: 'wu', 群: 'qun' } as Record<string, string>)[player.faction] ?? 'qun'
  return '/assets/generals/' + kingdom + '/' + player.character_id + '.png'
}

export function portraitState(player: PlayerView, selected: boolean, selectable: boolean, responding: boolean): PortraitState {
  return { currentTurn: player.active, selectableTarget: selectable, selectedTarget: selected,
    waitingResponse: responding, damaged: false, healing: false, dying: player.alive && player.hp <= 0,
    dead: !player.alive, chained: player.chained, faceDown: player.face_up === false,
    judgment: false }
}

function PlayerPanel({ player, position, selected, selectable, responding, eventKind, eventCue, vfxQuality, onSelect, onDetail }: {
  player: PlayerView
  position: string
  selected: boolean
  selectable: boolean
  responding: boolean
  eventKind?: string
  eventCue?: PublicEvent
  vfxQuality: VfxQuality
  onSelect(): void
  onDetail(): void
}) {
  const portrait = portraitState(player, selected, selectable, responding)
  const godMode: GodPortraitMode = portrait.dying ? 'dying' : eventKind?.includes('Damage') ? 'hit' : eventKind?.includes('CardUsed') ? 'attack' : 'idle'
  const classes = 'player-panel player-' + position
    + (player.active ? ' active' : '')
    + (selected ? ' selected-target' : '')
    + (selectable ? ' selectable' : '')
    + (responding ? ' responding' : '')
    + (portrait.faceDown ? ' face-down' : '')
    + (portrait.dying ? ' dying' : '')
    + (portrait.chained ? ' chained' : '')
    + (eventKind?.includes('Damage') ? ' damage-flash' : '')
    + (eventKind?.includes('Recover') ? ' healing-flash' : '')
    + (!player.alive ? ' dead' : '')
  return <article data-player-id={player.player_id} className={classes} onClick={selectable ? onSelect : undefined}>
    <button className="portrait-button" onClick={(event) => { event.stopPropagation(); onDetail() }} aria-label={'查看' + player.character_name + '详情'}>
      {player.character_id === 'forest_god_lvbu' ? <GodPortrait characterId={player.character_id} name={player.character_name} quality={vfxQuality} mode={godMode} cue={eventCue} /> : <img src={portraitFor(player)} onError={(event) => { event.currentTarget.src = '/assets/generals/default_general.png' }} alt={player.character_name} />}
      {portrait.faceDown && <span className="face-down-mark">翻面</span>}
      {player.chained && <span className="chain-mark">锁</span>}
    </button>
    <div className="player-heading"><strong>{player.name}</strong><span>{player.identity_label}</span></div>
    <div className="general-line"><b>{player.character_name}</b><small>{player.faction} · 距离 {player.effective_distance ?? '—'} · 范围 {player.attack_range}</small></div>
    <div className="hp-row" aria-label={player.hp + ' / ' + player.max_hp + ' 体力'}>
      {Array.from({ length: player.max_hp }, (_, index) => <i key={index} className={index < player.hp ? 'full' : ''}>♥</i>)}
    </div>
    <div className="player-zones">
      <span className="hand-count">手牌 {player.hand_count}</span>
      {player.equipment.map((card) => <span key={card.card_id} className="zone-token equipment-token" tabIndex={0} aria-label={'装备 ' + card.name}>
        {card.name}
        <span className="equipment-preview" role="tooltip"><img src={assetForCard(card)} alt={card.name} /><small>{card.details}</small></span>
      </span>)}
      {player.judgments.map((card) => <span key={card.card_id} className="zone-token judgment-token" title={card.details}>{card.name}</span>)}
    </div>
    <div className="mini-skills">{player.skill_labels.map((skill) => <span key={skill}>{skill}</span>)}</div>
    {player.active && <span className="turn-badge">当前回合</span>}
    {responding && <span className="response-badge">正在响应</span>}
    {!!player.marks && Object.entries(player.marks).filter(([, count]) => count > 0).map(([mark, count]) => <span key={mark} className="mark-badge">{mark} {count}</span>)}
  </article>
}

function HandCard({ card, selected, eligible, onClick }: { card: CardView; selected: boolean; eligible: boolean; onClick(): void }) {
  return <button
    className={'hand-card' + (selected ? ' selected' : '') + (!eligible ? ' disabled' : '')}
    disabled={!eligible}
    onClick={onClick}
    title={card.details || card.name + ' · ' + card.suit + card.rank}
    aria-label={card.name + ' ' + card.suit + card.rank}
  >
    <img src={assetForCard(card)} onError={(event) => { event.currentTarget.src = '/assets/cards/default_card.png' }} alt="" />
    <span className="card-corner"><b>{card.rank}</b>{card.suit}</span>
    <strong>{card.name}</strong>
  </button>
}

function SkillBar({ player, general, request, chosen, onChoose }: { player: PlayerView; general?: GeneralInfo; request: PendingRequest | null; chosen: string; onChoose(value: string): void }) {
  const skillOptions = request?.choices.filter((choice) => choice.startsWith('skill:') || choice.startsWith('virtual:')) ?? []
  return <div className="skill-bar" aria-label="技能栏">
    {player.skill_labels.map((label) => {
      const plain = label.split(' · ')[0]
      const skill = general?.skills.find((item) => item.name === plain)
      const option = skillOptions.find((item) => skill && item.split(':')[1] === skill.id)
      return <button key={label} disabled={!option} className={chosen === option ? 'selected' : ''} onClick={() => option && onChoose(option)}>{label}</button>
    })}
    {skillOptions.filter((option) => !general?.skills.some((skill) => skill.id === option.split(':')[1])).map((option) =>
      <button key={option} className={chosen === option ? 'selected' : ''} onClick={() => onChoose(option)}>{option.split(':')[1]}</button>)}
  </div>
}

function DecisionPrompt({ request, canConfirm, onConfirm, onPass, onBoolean, onOption }: {
  request: PendingRequest
  canConfirm: boolean
  onConfirm(): void
  onPass(): void
  onBoolean(value: boolean): void
  onOption(value: string): void
}) {
  const prompt = ({
    'Choose a play action or end the play phase': '请选择出牌操作，或结束出牌阶段',
    'Choose a target': '请选择目标',
    'Respond with a card or pass': '请打出响应牌，或选择不出',
  } as Record<string, string>)[request.prompt] ?? request.prompt
  if (request.request_type === 'yes_no') return <section className="decision-prompt">
    <div className="prompt-copy"><strong>{prompt}</strong><small>服务器正在等待你的决定</small></div>
    <Timer remainingMs={request.remaining_ms} />
    <button className="brush-button primary compact" onClick={() => onBoolean(true)}>发动 / 是</button>
    <button className="brush-button subtle compact" onClick={() => onBoolean(false)}>不发动 / 否</button>
  </section>
  const directOptions = request.request_type === 'choose_option'
    ? request.choices.filter((choice) => !choice.startsWith('use:') && !choice.startsWith('skill:') && !choice.startsWith('virtual:'))
    : []
  return <section className="decision-prompt">
    <div className="prompt-copy"><strong>{prompt}</strong><small>选择后点击确认，操作才会提交</small></div>
    <Timer remainingMs={request.remaining_ms} />
    {directOptions.map((choice) => <button key={choice} className="brush-button compact" onClick={() => onOption(choice)}>{choice === 'end_play_phase' ? '结束出牌' : choice}</button>)}
    {request.allow_pass && <button className="brush-button subtle compact" onClick={onPass}>{request.required_definition_id === 'trick.nullification' ? '本次均不响应' : '不出'}</button>}
    <button className="brush-button primary compact" disabled={!canConfirm} onClick={onConfirm}>确定</button>
  </section>
}

function GeneralDetailPanel({ player, general, quality, onClose }: { player: PlayerView; general?: GeneralInfo; quality: VfxQuality; onClose(): void }) {
  return <div className="modal-backdrop" onClick={onClose}><aside className="game-general-detail paper-panel" onClick={(event) => event.stopPropagation()}>
    <button className="modal-close" onClick={onClose}>×</button>
    {player.character_id === 'forest_god_lvbu' ? <GodPortrait characterId={player.character_id} name={player.character_name} quality={quality} /> : <img src={portraitFor(player)} onError={(event) => { event.currentTarget.src = '/assets/generals/default_general.png' }} alt={player.character_name} />}
    <div><p className="eyebrow">武将详情</p><h2>{player.character_name}<span>{player.faction}</span></h2><p>{player.hp} / {player.max_hp} 体力 · {player.identity_label}</p>
      {(general?.skills ?? []).map((skill) => <section key={skill.id}><h3>{skill.name}<em>{skill.type}</em></h3><p>{skill.description}</p>{skill.type === 'lord' && player.identity_label !== '主公' && <small>当前身份未启用</small>}</section>)}
      {!general && player.skill_labels.map((skill) => <section key={skill}><h3>{skill}</h3><p>详细说明可在武将目录载入后查看。</p></section>)}
    </div>
  </aside></div>
}

function SharedCards({ cards, selected, eligible, onSelect }: { cards: CardView[]; selected: string[]; eligible: Set<string>; onSelect(id: string): void }) {
  if (!cards.length) return null
  return <section className="shared-card-pool"><p>五谷公共牌池</p><div>{cards.map((card) =>
    <HandCard key={card.card_id} card={card} selected={selected.includes(card.card_id)} eligible={eligible.has(card.card_id)} onClick={() => onSelect(card.card_id)} />)}</div></section>
}

function EventStage({ event, players }: { event?: PublicEvent; players: PlayerView[] }) {
  if (!event) return <div className="event-stage quiet"><span>牌局进行中</span></div>
  const name = (id: unknown) => players.find((player) => player.player_id === id)?.name ?? String(id ?? '')
  const kind = String(event.kind ?? '')
  let text = kind
  if (kind.includes('CardUsed') || kind.includes('TrickTargets')) text = name(event.source_id) + ' 使用【' + String(event.card_name ?? '卡牌') + '】'
  else if (kind.includes('Responded') || kind.includes('VirtualResponse')) {
    const responseNames: Record<string, string> = { 'basic.dodge': '闪', 'basic.slash': '杀', 'basic.peach': '桃', 'trick.nullification': '无懈可击' }
    text = name(event.source_id) + ' 打出【' + (responseNames[String(event.definition_id)] ?? '响应牌') + '】'
  }
  else if (kind.includes('Damage')) text = name(event.source_id) + ' 对 ' + name(event.target_id) + ' 造成 ' + String(event.amount ?? 1) + ' 点伤害'
  else if (kind.includes('Recovered')) text = name(event.target_id ?? event.source_id) + ' 恢复体力'
  else if (kind.includes('Death')) text = name(event.player_id ?? event.target_id) + ' 阵亡'
  else if (kind.includes('Judgment')) text = '判定正在结算'
  return <div className={'event-stage event-' + kind.toLowerCase()}><strong>{text}</strong></div>
}

export function ResultOverlay({ result, identity, onHome, onReplay }: { result: string; identity?: string; onHome(): void; onReplay(): void }) {
  const won = identity === '主公' || identity === '忠臣'
    ? result.includes('主公') || result.includes('忠臣')
    : identity === '反贼' ? result.includes('反贼') : identity === '内奸' ? result.includes('内奸') : false
  return <div className={'result-overlay ' + (won ? 'victory' : 'defeat')} role="dialog" aria-label="对局结果"><div>
    <p className="eyebrow">对局终了 · {identity ?? '身份未知'}</p><h1>{won ? '胜利' : '败北'}</h1><p>{result || '本局已经结束'}</p>
    <button className="brush-button primary" onClick={onReplay}>再来一局</button>
    <button className="brush-button subtle" onClick={onHome}>返回首页</button>
  </div></div>
}

export function GamePage() {
  const { state, actions } = useGame()
  const projection = state.projection
  const request = state.pendingRequest
  const [selectedCards, setSelectedCards] = useState<string[]>([])
  const [selectedTargets, setSelectedTargets] = useState<string[]>([])
  const [selectedOption, setSelectedOption] = useState('')
  const [detailPlayer, setDetailPlayer] = useState<PlayerView | null>(null)
  const [vfxQuality, setVfxQuality] = useState<VfxQuality>(readVfxQuality)

  useEffect(() => { setSelectedCards([]); setSelectedTargets([]); setSelectedOption('') }, [request?.request_id])
  if (!projection) return <main className="game-page table-background"><section className="paper-panel loading-panel">正在恢复牌桌……</section></main>

  const selfIndex = projection.players.findIndex((player) => player.player_id === state.seatId)
  const self = projection.players[selfIndex >= 0 ? selfIndex : 0]
  const opponents = projection.players.filter((player) => player.player_id !== self.player_id)
  const allowedTargets = new Set(request?.allowed_player_ids ?? [])
  const eligibleCards = new Set(request?.eligible_card_ids ?? [])
  const isCardRequest = !!request && ['respond_with_card', 'choose_card', 'choose_cards'].includes(request.request_type)
  const isTargetRequest = !!request && ['choose_player', 'choose_players'].includes(request.request_type)
  const choiceCardIds = new Set((request?.choices ?? []).filter((choice) => choice.startsWith('use:')).map((choice) => choice.slice(4)))
  const cardEligible = (id: string) => isCardRequest ? eligibleCards.has(id) : request?.request_type === 'choose_option' ? choiceCardIds.has(id) : false

  function toggleCard(id: string) {
    if (!request || !cardEligible(id)) return
    if (request.request_type === 'choose_option') { setSelectedCards([id]); setSelectedOption('use:' + id); return }
    const max = request.max_count || 1
    setSelectedCards((current) => current.includes(id) ? current.filter((item) => item !== id) : max === 1 ? [id] : current.length < max ? [...current, id] : current)
  }
  function toggleTarget(id: string) {
    if (!request || !allowedTargets.has(id)) return
    const max = request.max_count || 1
    setSelectedTargets((current) => current.includes(id) ? current.filter((item) => item !== id) : max === 1 ? [id] : current.length < max ? [...current, id] : current)
  }
  function confirm() {
    if (!request) return
    let value: unknown = selectedOption
    if (request.request_type === 'respond_with_card' || request.request_type === 'choose_card') value = selectedCards[0]
    if (request.request_type === 'choose_cards') value = selectedCards
    if (request.request_type === 'choose_player') value = selectedTargets[0]
    if (request.request_type === 'choose_players') value = selectedTargets
    actions.submitDecision(request.request_id, value)
  }
  const minimum = request?.min_count ?? 1
  const selectionCount = isTargetRequest ? selectedTargets.length : selectedOption ? 1 : selectedCards.length
  const canConfirm = !!request && selectionCount >= minimum && selectionCount <= (request.max_count || 1)
  const beamMode = request?.request_type === 'respond_with_card' ? 'protect' : selectedOption.includes('slash') || request?.required_definition_id?.includes('slash') ? 'attack' : 'normal'
  const detailGeneral = detailPlayer ? state.generals[detailPlayer.character_id] : undefined
  const latestEvent = state.publicEvents[state.publicEvents.length - 1]
  const eventTarget = String(latestEvent?.target_id ?? latestEvent?.player_id ?? '')
  const eventSource = String(latestEvent?.source_id ?? '')
  const eventKind = String(latestEvent?.kind ?? '')

  return <main className="game-page table-background">
    <header className="game-hud"><div><span>第 {projection.turn_number} 回合</span><strong>{phaseNames[projection.current_phase] ?? projection.current_phase}</strong>{state.updateAvailable && <small className="game-update-note">新版本可用</small>}</div><div className="pile-stats"><span>牌堆 {projection.deck_count}</span><span>弃牌 {projection.discard_count}</span><label className="vfx-quality-control">画质 <select aria-label="战斗特效画质" value={vfxQuality} onChange={(event) => { const value = event.target.value as VfxQuality; setVfxQuality(value); saveVfxQuality(value) }}><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label><button onClick={actions.returnHome}>离开牌局</button></div></header>
    <section className="game-board">
      <CombatVFXLayer players={projection.players} targets={selectedTargets} mode={beamMode} event={latestEvent} quality={vfxQuality} />
      {opponents.map((player, index) => <PlayerPanel key={player.player_id} player={player} position={positions[index]} selected={selectedTargets.includes(player.player_id)} selectable={isTargetRequest && allowedTargets.has(player.player_id)} responding={request?.player_id === player.player_id} eventKind={eventTarget === player.player_id || eventSource === player.player_id && eventKind.includes('CardUsed') ? eventKind : undefined} eventCue={latestEvent} vfxQuality={vfxQuality} onSelect={() => toggleTarget(player.player_id)} onDetail={() => setDetailPlayer(player)} />)}
      <EventStage event={state.publicEvents[state.publicEvents.length - 1]} players={projection.players} />
      <SharedCards cards={projection.shared_cards} selected={selectedCards} eligible={eligibleCards} onSelect={toggleCard} />
      {projection.discard_top && <div className="discard-top"><HandCard card={projection.discard_top} selected={false} eligible={false} onClick={() => undefined} /></div>}
      <div className="self-area">
        {request && <DecisionPrompt request={request} canConfirm={canConfirm} onConfirm={confirm} onPass={() => actions.submitDecision(request.request_id, { pass: true })} onBoolean={(value) => actions.submitDecision(request.request_id, value)} onOption={(value) => actions.submitDecision(request.request_id, value)} />}
        <PlayerPanel player={self} position="self" selected={false} selectable={false} responding={request?.player_id === self.player_id} eventKind={eventTarget === self.player_id || eventSource === self.player_id && eventKind.includes('CardUsed') ? eventKind : undefined} eventCue={latestEvent} vfxQuality={vfxQuality} onSelect={() => undefined} onDetail={() => setDetailPlayer(self)} />
        <SkillBar player={self} general={state.generals[self.character_id]} request={request} chosen={selectedOption} onChoose={setSelectedOption} />
        <div className="hand" aria-label="手牌区">{projection.hand.map((card) => <HandCard key={card.card_id} card={card} selected={selectedCards.includes(card.card_id)} eligible={cardEligible(card.card_id)} onClick={() => toggleCard(card.card_id)} />)}</div>
      </div>
    </section>
    {state.error && <div className="game-error">{state.error}<button onClick={actions.clearError}>×</button></div>}
    {detailPlayer && <GeneralDetailPanel player={detailPlayer} general={detailGeneral} quality={vfxQuality} onClose={() => setDetailPlayer(null)} />}
    {(state.result || projection.result) && <ResultOverlay result={state.result || projection.result || ''} identity={self.identity_label} onHome={actions.returnHome} onReplay={() => { actions.returnHome(); actions.createRoom(state.playerName || '玩家', true) }} />}
  </main>
}
