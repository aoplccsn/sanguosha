import type { GeneralInfo, PlayerView, PublicEvent, PortraitState } from '../types'
import { useGame } from '../state/GameContext'
import { generalPortrait } from '../assets'
import { Timer } from './Timer'
import { DynamicPortrait } from './DynamicPortrait'
import { idlePortrait } from '../idlePortraits'
import { markLabel, phaseNames } from '../labels'
import { SuitText } from './SuitText'
import type { GodPortraitMode } from './GodPortrait'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'
import { IdentityNote } from './IdentityNote'
import { assetForCard, cardNames, equipmentSign } from './cardUtil'

function portraitFor(player: PlayerView, catalog: Record<string, GeneralInfo>) {
  const kingdom = ({ 魏: 'wei', 蜀: 'shu', 吴: 'wu', 群: 'qun' } as Record<string, string>)[player.faction] ?? 'qun'
  return generalPortrait(player.character_id, kingdom, catalog)
}

export function portraitState(player: PlayerView, selected: boolean, selectable: boolean, responding: boolean): PortraitState {
  return { currentTurn: player.active, selectableTarget: selectable, selectedTarget: selected,
    waitingResponse: responding, damaged: false, healing: false, dying: player.alive && player.hp <= 0,
    dead: !player.alive, chained: player.chained, faceDown: player.face_up === false,
    judgment: false }
}

export function PlayerPanel({ player, position, selected, selectable, dimmed = false, responding, waiting, phase, aoeState, thinking = false, eventKind, eventActor, eventTarget, eventCue, godCue, vfxQuality, onSelect, onDetail, separateZones = false }: {
  separateZones?: boolean
  player: PlayerView
  position: string
  selected: boolean
  selectable: boolean
  dimmed?: boolean
  responding: boolean
  waiting?: { key: string; remaining_ms: number; total_ms?: number; required_definition_id?: string; response_to?: string }
  phase?: string
  aoeState?: string
  thinking?: boolean
  eventKind?: string
  eventActor?: boolean
  eventTarget?: boolean
  eventCue?: PublicEvent
  godCue?: { mode: GodPortraitMode; id: number }
  vfxQuality: VfxQuality
  onSelect(): void
  onDetail(): void
}) {
  const { state } = useGame()
  const portrait = portraitState(player, selected, selectable, responding)
  const buqu = player.special_piles?.buqu ?? []
  const field = player.special_piles?.tian ?? []
  const power = player.special_piles?.quan ?? []
  const counters = player.special_piles?.counter ?? []
  const zongxuanCards = new Set(Object.entries(player.special_piles ?? {}).filter(([key])=>key.startsWith('committed:zongxuan:')).flatMap(([,cards])=>cards.map(card=>card.card_id)))
  const committed = Object.entries(player.special_piles ?? {})
    .filter(([key]) => key.startsWith('committed:'))
    .flatMap(([, cards]) => cards)
  const classes = 'player-panel player-' + position + (player.team_id ? ' team-' + player.team_id : '')
    + (player.active ? ' active' : '')
    + (selected ? ' selected-target' : '')
    + (selectable ? ' selectable' : '')
    + (responding ? ' responding' : '')
    + (dimmed && player.alive && !selectable ? ' target-illegal' : '')
    + (thinking ? ' thinking' : '')
    + (portrait.faceDown ? ' face-down' : '')
    + (portrait.dying ? ' dying' : '')
    + (portrait.chained ? ' chained' : '')
    + (eventActor && /CardUsed|Responded|VirtualResponse|Skill|Guhuo/.test(eventKind ?? '') ? ' presenting-action' : '')
    + (eventTarget ? ' event-target' : '')
    + (aoeState ? ' aoe-' + aoeState : '')
    + (eventKind?.includes('Damage') ? ' damage-flash' : '')
    + (eventKind?.includes('Recover') ? ' healing-flash' : '')
    + (!player.alive ? ' dead' : '')
  return <article data-team-id={player.team_id ?? ""} data-character-id={player.character_id} data-player-id={player.player_id} className={classes} onClick={selectable ? onSelect : undefined}>
    <IdentityNote key={`${state.roomCode}:${state.seatId}:${player.player_id}`} roomId={state.roomCode ?? ''} localId={state.seatId ?? ''} player={player} />
    <button className="portrait-button" onClick={(event) => { event.stopPropagation(); if (selectable) onSelect(); else onDetail() }} aria-label={selectable ? '选择目标' + player.character_name : '查看' + player.character_name + '详情'}>
      <DynamicPortrait staticPortrait={portraitFor(player, state.generals)} idleVideo={idlePortrait(player.character_id)?.panelVideo ?? idlePortrait(player.character_id)?.video} objectPosition={idlePortrait(player.character_id)?.objectPosition} name={player.character_name} quality={vfxQuality} />
      {portrait.faceDown && <span className="face-down-mark">翻面</span>}
      {player.chained && <span className="chain-mark">连环</span>}
    </button>
    <div className="player-heading"><strong>{player.name}</strong><span>{player.identity_label}</span></div>
    <div className="general-line"><b>{player.character_name}</b></div>
    <div className="hp-row" aria-label={player.hp + ' / ' + player.max_hp + ' 体力'}>
      {Array.from({ length: player.max_hp }, (_, index) => <i key={index} className={index < player.hp ? 'full' : ''}>♥</i>)}
    </div>
    <div className="seat-caption">
      <div className="seat-facts">{player.ai_controlled && <span className="control-badge">AI 托管</span>}<span>{player.faction}</span><span>距离 {player.effective_distance ?? '—'} · 范围 {player.attack_range}</span></div>
      <div className="player-zones">
        <span className="hand-count">手牌 {player.hand_count}</span>
        {!separateZones && player.equipment.map((card) => <span key={card.card_id} className="zone-token equipment-token" tabIndex={0} aria-label={'装备 ' + card.name}>
          {card.name}{equipmentSign(card)}
          <span className="equipment-preview" role="tooltip"><img src={assetForCard(card)} alt={card.name} /><small><SuitText suit={card.suit} rank={card.rank} /> {card.details}</small></span>
        </span>)}
        {!separateZones && player.judgments.map((card) => <span key={card.card_id} className="zone-token judgment-token" title={card.details}>{card.name}</span>)}
        {buqu.length > 0 && <span className="zone-token buqu-token" title={'不屈牌：' + buqu.map((card) => card.suit + card.rank).join(' ')}>
          不屈 {buqu.length} · {buqu.map(card=><SuitText key={card.card_id} suit={card.suit} rank={card.rank} />)}
        </span>}
        {field.length > 0 && <span className="zone-token" title={'田：' + field.map((card) => card.suit + card.rank).join(' ')}>田 {field.length}</span>}
        {player.abolished_equipment_slots?.map(slot=><span key={slot} className="zone-token">已废除 {{weapon:'武器栏',armor:'防具栏',offensive_horse:'进攻马栏',defensive_horse:'防御马栏'}[slot] ?? slot}</span>)}
        {counters.length > 0 && <span className="zone-token" title={'逆：' + counters.map(card=>card.name+' '+card.suit+card.rank).join(' ')}>逆 {counters.length}</span>}
        {power.length > 0 && <span className="zone-token" title={'权：' + power.map(card => card.suit ? card.name + ' ' + card.suit + card.rank : '背面牌').join(' ')}>权 {power.length}</span>}
        {player.active_transformation && <span className="zone-token">化身 {state.generals[player.active_transformation]?.name ?? '已选择武将'}</span>}
        {!!player.transformation_pool?.length && <span className="zone-token">化身池 {player.transformation_pool.length}</span>}
        {committed.map((card) => <span key={card.card_id} className="zone-token judgment-token"
          title={card.name + (card.suit ? ' ' + card.suit + card.rank : '')}>{zongxuanCards.has(card.card_id) ? '纵玄待选' : '蛊惑'} · {card.name}</span>)}
      </div>
      <div className="mini-skills">{player.skill_labels.map((skill) => <span key={skill}>{skill}</span>)}</div>
      <div className="seat-marks">{!!player.marks && Object.entries(player.marks).filter(([, count]) => count > 0).map(([mark, count]) => <span key={mark} className="mark-badge">{markLabel(mark)} {count}</span>)}</div>
    </div>
    {eventActor && eventKind && /CardUsed|Responded|VirtualResponse|Skill/.test(eventKind) && <span className="action-badge">正在行动</span>}
    {player.active && <span className="turn-badge">当前回合 · {phaseNames[phase ?? ''] ?? '行动中'}</span>}
    {aoeState && <span className="aoe-badge">{aoeState === 'resolved' ? '已结算' : aoeState === 'current' ? '当前结算' : '待结算'}</span>}
    {responding && <span className="response-badge">正在响应</span>}
    {thinking && !responding && <span className="thinking-badge">思考中…</span>}
    {waiting && <div className={'seat-timer' + (responding ? ' responder-state' : '')}>
      {responding && <div className="response-description"><b>{waiting.response_to ? `响应【${cardNames[waiting.response_to] ?? '卡牌'}】` : '处理响应'}</b><span>{waiting.required_definition_id === 'trick.nullification' ? '可使用【无懈可击】' : waiting.required_definition_id ? `请出【${cardNames[waiting.required_definition_id] ?? '响应牌'}】` : '请作出选择'}</span></div>}
      {thinking && responding && <small>思考中 ···</small>}
      <Timer key={waiting.key} remainingMs={waiting.remaining_ms} totalMs={waiting.total_ms} warnAt={thinking ? 0 : 5} />
    </div>}
  </article>
}
