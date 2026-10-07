import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { effectiveSelection, emptySelection, virtualOptions, materials, type Selection } from '../state/selection'
import type { CardView, GeneralInfo, PendingRequest, PlayerView, Projection, PublicEvent, PortraitState, CombatContext } from '../types'
import { useGame } from '../state/GameContext'
import { cardImage, defaultCardImage, defaultGeneralPortrait, generalPortrait } from '../assets'
import { TemporaryInteractionPanel } from './TemporaryInteractionPanel'
import { Timer } from './Timer'
import { SkillTooltip, optionMetadata } from './SkillTooltip'
import { readGameSpeed, type GameSpeed } from '../presentation/pacing'
import { usePresentation } from '../presentation/usePresentation'
import { DynamicPortrait } from './DynamicPortrait'
import { idlePortrait } from '../idlePortraits'
import { markLabel, skillTypeLabel, battlePrompt } from '../labels'
import { SuitText, BattleText } from './SuitText'
import { CombatVFXLayer } from './CombatVFXLayer'
import type { GodPortraitMode } from './GodPortrait'
import { readVfxQuality, saveVfxQuality, type VfxQuality } from '../vfx/CombatVFXRuntime'

import { LandscapeGate } from './LandscapeGate'
import { IdentityNote } from './IdentityNote'

const positions = ['east', 'north-east', 'north-west', 'west']
const positionsSmall: Record<number, string[]> = { 2: ['north'], 4: ['east', 'north', 'west'] }
const positionsEight = ['east-lower', 'east-upper', 'north-east', 'north', 'north-west', 'west-upper', 'west-lower']
const phaseNames: Record<string, string> = {
  '—': '回合观察', start: '开始', judgment: '判定', draw: '摸牌', play: '出牌', discard: '弃牌', finish: '结束',
}

function assetForCard(card: CardView) {
  if (card.definition_id === 'basic.slash') return cardImage('basic/slash')
  if (card.definition_id === 'basic.dodge') return cardImage('basic/dodge')
  if (card.definition_id === 'basic.peach') return cardImage('basic/peach')
  if (/^(basic|trick|delayed)\./.test(card.definition_id)) {
    return cardImage('military/' + card.definition_id)
  }
  if (card.definition_id.startsWith('equipment.')) {
    return cardImage('military/' + card.definition_id + '-v2')
  }
  return defaultCardImage
}

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

export function PlayerPanel({ player, position, selected, selectable, responding, waiting, phase, aoeState, thinking = false, eventKind, eventActor, eventTarget, eventCue, godCue, vfxQuality, onSelect, onDetail, separateZones = false }: {
  separateZones?: boolean
  player: PlayerView
  position: string
  selected: boolean
  selectable: boolean
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
          {card.name}{card.equipment_slot === 'defensive_horse' ? ' +1' : card.equipment_slot === 'offensive_horse' ? ' -1' : ''}
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

export function HandCard({ card, selected, eligible, onClick }: { card: CardView; selected: boolean; eligible: boolean; onClick(): void }) {
  const [showTooltip,setShowTooltip]=useState(false)
  return <button
    onMouseEnter={()=>setShowTooltip(true)} onMouseLeave={()=>setShowTooltip(false)} onFocus={()=>setShowTooltip(true)} onBlur={()=>setShowTooltip(false)}
    className={'hand-card' + (selected ? ' selected' : '') + (!eligible ? ' disabled' : '')}
    data-card-id={card.card_id}
    aria-disabled={!eligible}
    onClick={onClick}
    title={card.details || card.name + ' · ' + card.suit + card.rank}
    aria-label={card.name + ' ' + card.suit + card.rank}
  >
    <img src={assetForCard(card)} alt="" />
    <span className="card-corner"><SuitText suit={card.suit} rank={card.rank} /></span>
    {showTooltip && <span className="hand-card-tooltip" role="tooltip"><SuitText suit={card.suit} rank={card.rank} /> <small>{card.details}</small></span>}
    <strong>{card.name}{card.equipment_slot === 'defensive_horse' ? ' +1' : card.equipment_slot === 'offensive_horse' ? ' -1' : ''}</strong>
  </button>
}

const cardNames: Record<string, string> = {
  'basic.slash': '杀', 'basic.fire_slash': '火杀', 'basic.thunder_slash': '雷杀',
  'basic.dodge': '闪', 'basic.peach': '桃', 'basic.wine': '酒',
  'trick.nullification': '无懈可击', 'trick.ex_nihilo': '无中生有',
  'trick.dismantlement': '过河拆桥', 'trick.snatch': '顺手牵羊',
  'trick.duel': '决斗', 'trick.fire_attack': '火攻', 'trick.iron_chain': '铁索连环',
  'trick.savage_assault': '南蛮入侵', 'trick.archery_attack': '万箭齐发',
  'trick.god_salvation': '桃园结义', 'trick.amazing_grace': '五谷丰登',
  'trick.borrowed_sword': '借刀杀人',
}

const choiceNames: Record<string, string> = {
  cancel:'放弃', confirm:'确认', choose:'选择', response:'响应', target:'目标', extra_turn:'本回合结束后额外回合', continue:'继续选牌', finish:'结束选牌', qi:'奇兵（仅你可见）', zheng:'正兵（仅你可见）', draw1_quota:'摸一张，杀上限加一', draw3_stop:'摸三张，本回合禁杀',
  keep: '保留当前化身', end_play_phase: '结束出牌', draw: '摸牌', discard: '弃牌', damage: '造成伤害',
  draw_x_discard_one: '摸 X 张，弃一张', draw_one_discard_x: '摸一张，弃 X 张',
  lose_hp: '失去体力', lose_max_hp: '减体力上限', rage: '弃一枚怒标记',
  slash: '打出杀', recover: '回复体力', top: '置于牌堆顶',
  decline: '放弃', done: '完成', spade: '黑桃', heart: '红桃',
  club: '梅花', diamond: '方块',
}

function choiceLabel(choice: string, index: number, projection: Projection): string {
  if (choiceNames[choice]) return choiceNames[choice]
  if (cardNames[choice]) return cardNames[choice]
  const player = projection.players.find((item) => item.player_id === choice)
  if (player) return player.name
  const card = [...projection.hand, ...projection.shared_cards,
    ...projection.players.flatMap((item) => [...item.equipment, ...item.judgments, ...(item.revealed_hand ?? [])])]
    .find((item) => item.card_id === choice || item.card_id === choice.split(':').at(-1))
  if (card) return card.name
  if (choice.startsWith('current:')) return '保留当前判定'
  if (choice.startsWith('better:')) return '选择改判牌'
  if (choice.startsWith('damage:')) return '受到伤害'
  return `选项 ${index + 1}`
}

function SkillBar({ player, general, skillNames, request, chosen, onChoose, onUnavailable }: { player: PlayerView; general?: GeneralInfo; skillNames: Record<string, string>; request: PendingRequest | null; chosen: string; onChoose(value: string): void; onUnavailable(): void }) {
  const allOptions = Array.from(new Set([
    ...(request?.choices.filter((choice) => choice.startsWith('skill:') || choice.startsWith('virtual:')) ?? []),
    ...(request?.eligible_card_ids.filter((choice) => choice.startsWith('virtual:')) ?? []),
  ]))
  const skillOptions=allOptions.filter((option,index)=>!option.startsWith('virtual:') || allOptions.findIndex(o=>o.startsWith('virtual:') && o.split(':')[1]===option.split(':')[1])===index)
  const { state } = useGame()
  return <div className="skill-bar" aria-label="技能栏">
    {player.skill_labels.map((label) => {
      const plain = label.split(' · ')[0]
      const skill = general?.skills.find((item) => item.name === plain) ?? Object.values(state.generals).flatMap(item=>item.skills).find(item=>item.name===plain)
      const option = skillOptions.find((item) => item.split(':')[1] === (skill?.id ?? (plain === '蛊惑' ? 'guhuo' : '')))
      const metadata = skill ?? Object.values(state.generals).flatMap(item => item.skills).find(item => item.name === plain)
      return <SkillTooltip key={label} skills={metadata ? [metadata] : []}><button aria-disabled={!option} className={chosen === option ? 'selected' : ''} onClick={() => option ? onChoose(option) : onUnavailable()}>{label}</button></SkillTooltip>
    })}
    {skillOptions.filter((option) => !general?.skills.some((skill) => skill.id === option.split(':')[1])
      && !(option.split(':')[1] === 'guhuo' && player.skill_labels.some((label) => label.split(' · ')[0] === '蛊惑'))).map((option) =>
      <SkillTooltip key={option} {...optionMetadata(option, state.generals)}><button className={chosen === option ? 'selected' : ''} onClick={() => onChoose(option)}>{request?.choice_labels?.[option] ?? skillNames[option.split(':')[1]] ?? '技能选项'}</button></SkillTooltip>)}
  </div>
}

function DecisionPrompt({ request, projection, canConfirm, processing, summary, onConfirm, onCancel, onPass, onPassRoot, onBoolean, onOption, onRecast }: {
  onRecast?: () => void
  request: PendingRequest
  projection: Projection
  canConfirm: boolean
  processing: boolean
  summary: string
  onConfirm(): void
  onCancel(): void
  onPass(): void
  onPassRoot(): void
  onBoolean(value: boolean): void
  onOption(value: string): void
}) {
  const { state } = useGame()
  const currentTarget=projection.combat?.current_target_id
  const effectTarget=projection.players.find(p=>p.player_id===currentTarget)?.character_name
  const prompt = request.required_definition_id==='trick.nullification' && effectTarget ? `是否对【${projection.combat?.card_name ?? cardNames[projection.combat?.definition_id ?? ''] ?? '锦囊'} → ${effectTarget}】使用【无懈可击】？` : ({
    'Choose a play action or end the play phase': '请选择出牌操作，或结束出牌阶段',
    'Choose a target': '请选择目标',
    'Respond with a card or pass': battlePrompt(request,cardNames,Object.fromEntries(Object.values(state.generals).flatMap(g=>g.skills.map(s=>[s.id,s.name]))),projection.combat?.definition_id),
  } as Record<string, string>)[request.prompt] ?? battlePrompt(request,cardNames,Object.fromEntries(Object.values(state.generals).flatMap(g=>g.skills.map(s=>[s.id,s.name]))),projection.combat?.definition_id)
  if (request.request_type === 'yes_no') return <section className="decision-prompt">
    <div className="prompt-copy"><strong><BattleText text={prompt}/></strong><small>服务器正在等待你的决定</small></div>
    <button className="brush-button primary compact" disabled={processing} onClick={() => onBoolean(true)}>{processing ? '正在提交…' : prompt.includes('质疑') ? '质疑' : '发动 / 是'}</button>
    <button className="brush-button subtle compact" disabled={processing} onClick={() => onBoolean(false)}>{prompt.includes('质疑') ? '不质疑' : '不发动 / 否'}</button>
  </section>
  const directOptions = request.request_type === 'choose_option'
    ? request.choices.filter((choice) => !choice.startsWith('use:') && !choice.startsWith('skill:') && !choice.startsWith('virtual:'))
    : []
  return <section className="decision-prompt">
    <div className="prompt-copy"><strong><BattleText text={prompt}/></strong><small>选择后点击确认，操作才会提交</small></div>
    {summary && <div className="decision-summary">{summary}</div>}
    {directOptions.map((choice, index) => {
      const detail = optionMetadata(choice, state.generals)
      const label = choice.startsWith('learn:') && detail.skills[0] ? '永久获得【'+detail.skills[0].name+'】' : detail.general ? detail.general.name + (detail.skills.length === 1 ? ' · ' + detail.skills[0].name : '') : detail.skills[0]?.name
      return <SkillTooltip key={choice} {...detail}><button className="brush-button compact" disabled={processing} onClick={() => onOption(choice)}>{label ?? request.choice_labels?.[choice] ?? choiceLabel(choice, index, projection)}</button></SkillTooltip>
    })}
    {request.allow_pass && <button className="brush-button subtle compact" disabled={processing} onClick={onPass}>{request.required_definition_id === 'trick.nullification' ? '不响应' : '不出'}</button>}
    {request.required_definition_id === 'trick.nullification' && request.allow_pass && request.allow_root_trick_pass && <button className="brush-button subtle compact" disabled={processing} onClick={onPassRoot}>本轮不再询问</button>}
    <button className="brush-button primary compact" disabled={!canConfirm || processing} onClick={onConfirm}>{processing ? '正在提交…' : request.required_definition_id === 'trick.nullification' ? '使用无懈' : onRecast ? '使用' : '确定'}</button>
    {onRecast && <button className="brush-button compact" disabled={processing} onClick={onRecast}>重铸</button>}
    <button className="brush-button subtle compact" disabled={processing} onClick={onCancel}>{onRecast ? '取消' : '取消选中'}</button>
  </section>
}

export function GeneralDetailPanel({ player, general, quality, onClose }: { player: PlayerView; general?: GeneralInfo; quality: VfxQuality; onClose(): void }) {
  return <div className="modal-backdrop" onClick={onClose}><aside className="game-general-detail paper-panel" data-portrait-mode={idlePortrait(player.character_id) ? 'dynamic' : 'static'} onClick={(event) => event.stopPropagation()}>
    <button className="modal-close" onClick={onClose}>×</button>
    <DynamicPortrait staticPortrait={generalPortrait(player.character_id, general?.kingdom ?? ({ 魏: 'wei', 蜀: 'shu', 吴: 'wu', 群: 'qun' } as Record<string, string>)[player.faction] ?? 'qun', general ? { [general.id]: general } : {})} idleVideo={idlePortrait(player.character_id)?.video} objectPosition={idlePortrait(player.character_id)?.objectPosition} name={player.character_name} quality={quality} />
    <div><p className="eyebrow">武将详情</p><h2>{player.character_name}<span>{player.faction}</span></h2><p>{player.hp} / {player.max_hp} 体力 · {player.identity_label}</p>
      {(general?.skills ?? []).map((skill) => <section key={skill.id}><h3>{skill.name}<em>{skillTypeLabel(skill.type)}</em></h3><p>{skill.description}</p>{skill.type === 'lord' && player.identity_label !== '主公' && <small>当前身份未启用</small>}</section>)}
      {!general && player.skill_labels.map((skill) => <section key={skill}><h3>{skill}</h3><p>详细说明可在武将目录载入后查看。</p></section>)}
    </div>
  </aside></div>
}

function SharedCards({ cards, selected, eligible, onSelect }: { cards: CardView[]; selected: string[]; eligible: Set<string>; onSelect(id: string): void }) {
  if (!cards.length) return null
  return <section className="shared-card-pool"><p>五谷公共牌池</p><div>{cards.map((card) =>
    <HandCard key={card.card_id} card={card} selected={selected.includes(card.card_id)} eligible={eligible.has(card.card_id)} onClick={() => onSelect(card.card_id)} />)}</div></section>
}

function EventStage({ event, players, combat }: { event?: PublicEvent; players: PlayerView[]; combat?: CombatContext | null }) {
  const { state: { generals: stateCatalogForEvents } } = useGame()
  const responseBase = event?.base_action as CombatContext | undefined
  const base = /Responded|VirtualResponse/.test(String(event?.kind)) && responseBase ? responseBase : combat ?? responseBase
  if ((!event || event.kind === 'AIThinkingEvent') && !base) return <div className="event-stage quiet" />
  event = event && event.kind !== 'AIThinkingEvent' ? event : {kind: 'CardUsedEvent', ...base}
  const name = (id: unknown) => players.find((player) => player.player_id === id)?.character_name ?? '该角色'
  const kind = String(event.kind ?? '')
  let text = '牌局结算'
  if (kind === 'AIThinkingEvent') text = name(event.source_id) + ' 正在思考……'
  else if (kind.includes('CardUsed') || kind.includes('TrickTargets')) {
    const targets = Array.isArray(event.target_ids) ? event.target_ids.map(name).join('、') : ''
    text = name(event.source_id) + (targets ? ' 对 ' + targets : '') + ' 使用【' + String(event.card_name ?? '卡牌') + '】'
  }
  else if (kind === 'GuhuoEvent') text = name(event.source_id) + (event.stage === 'reveal'
    ? ' 揭示蛊惑牌【' + (cardNames[String(event.actual)] ?? String(event.actual)) + '】'
    : ' 蛊惑声明【' + (cardNames[String(event.declared)] ?? String(event.declared)) + '】')
  else if (kind.includes('Responded') || kind.includes('VirtualResponse')) {
    const responseNames: Record<string, string> = { 'basic.dodge': '闪', 'basic.slash': '杀', 'basic.peach': '桃', 'trick.nullification': '无懈可击' }
    text = name(event.source_id) + ' 打出【' + (responseNames[String(event.definition_id)] ?? '响应牌') + '】'
  }
  else if (kind.includes('Damage')) text = name(event.source_id) + ' 对 ' + name(event.target_id) + ' 造成 ' + String(event.amount ?? 1) + ' 点伤害'
  else if (kind.includes('Recovered')) text = name(event.target_id ?? event.source_id) + ' 恢复体力'
  else if (kind.includes('Skill')) text = name(event.source_id ?? event.player_id) + ' 发动【' + String(event.skill_name ?? Object.values(stateCatalogForEvents).flatMap(item => item.skills).find(skill => skill.id === event.skill_id)?.name ?? '技能') + '】'
  if (kind.includes('Skill') && Array.isArray(event.target_ids) && event.target_ids.length) text += ' → ' + event.target_ids.map(name).join('、')
  else if (kind.includes('Turn')) text = name(event.player_id) + ' · ' + (kind.includes('Started') ? '回合开始' : '回合结束')
  else if (kind.includes('Discard') || kind.includes('CardMoved')) text = name(event.player_id ?? event.source_id) + ' 弃牌'
  else if (kind === 'CardRevealedEvent') text = name(event.source_id) + ' 展示【' + String(event.card_name ?? '卡牌') + '】'
  else if (kind.includes('Dying')) text = name(event.player_id ?? event.target_id) + ' 濒死结算'
  else if (kind.includes('Death') || kind.includes('Died')) text = name(event.player_id ?? event.target_id) + ' 阵亡'
  else if (kind.includes('Judgment')) text = name(event.source_id) + ' · 判定' + (event.matched === true ? '命中' : event.matched === false ? '未命中' : '正在结算')
  const isResponse = /Responded|VirtualResponse/.test(kind)
  const definition = base?.definition_id ?? String(event.definition_id ?? '')
  const top = isResponse ? {source_id: String(event.source_id), definition_id: String(event.definition_id)} : base?.top_response
  const publicCards = Array.isArray(event.cards) ? event.cards as CardView[] : []
  const showCard = !!definition && !publicCards.length
  if (publicCards.length) text = name(event.player_id ?? event.source_id) + (kind==='DiscardEvent' ? (event.reason==='recast' ? ' 重铸：' : ' 弃置：') : kind.includes('Judgment') ? (event.matched === true ? ' 判定通过：' : event.matched === false ? ' 判定未通过：' : ' 判定：') : ' 展示：')
  if (kind==='DelayedResultEvent') text=name(event.source_id)+' · '+String(event.message ?? '延时锦囊结算')
  if (kind==='FireAttackResultEvent') text = event.stage==='no_match' ? name(event.source_id)+'没有同花色手牌可弃置 · ' : '【火攻】未造成伤害'
  if (kind==='ChainPropagationEvent') text=name(event.source_id)+' → 连环传播 → '+name(event.target_id)
  if (kind==='EffectTargetEvent') text = '【' + (cardNames[String(event.definition_id)] ?? '锦囊') + '】当前结算：' + name(event.target_id)
  if (base && /CardUsed|TrickTargets|Responded|VirtualResponse/.test(kind)) text = name(base.source_id) + (base.target_ids.length ? ' → ' + base.target_ids.map(name).join('、') : '')
  if (top?.definition_id === 'trick.nullification') text = name(top.source_id) + '【无懈可击】 → 【' + (cardNames[definition] ?? base?.card_name ?? '') + '】'
  return <div key={String(event.event_id ?? kind) + String(event.presentation_phase ?? '')} data-event-id={event.event_id} data-stage={String(event.presentation_phase ?? 'result')} className={'event-stage event-' + kind.toLowerCase()}>
    <div className="action-cards">
    {publicCards.map((card,index)=><div className="public-resolution-card" key={index}>{event.reason==='pindian' && Array.isArray(event.card_owner_ids) && <small>{name(event.card_owner_ids[index])} · 拼点</small>}<img src={assetForCard(card)} alt={card.name}/><b><SuitText suit={card.suit} rank={card.rank} /> {card.name}</b></div>)}
    {showCard && <div className="center-action-card base-card"><img src={assetForCard({ definition_id: definition } as CardView)} alt={cardNames[definition] ?? String(event.card_name ?? '卡牌')} /><b>{cardNames[definition] ?? String(event.card_name ?? '卡牌')}</b></div>}
    {top && <div className="center-action-card response-card"><img src={assetForCard({definition_id:top.definition_id} as CardView)} alt={cardNames[top.definition_id] ?? '响应牌'} /><b>{cardNames[top.definition_id] ?? '响应牌'}</b></div>}
    </div><strong>{text}{kind==='FireAttackResultEvent' && event.stage==='no_match' && <SuitText suit={String(event.suit)} />}</strong>
    {base?.current_target_id && <small>当前结算：{name(base.current_target_id)}</small>}
    {!!base?.nullification_count && <small className="nullification-status">无懈×{base.nullification_count} · 当前{base.cancelled ? '锦囊失效' : '锦囊有效'}</small>}
  </div>
}

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

export function GamePage() {
  const { state, actions } = useGame()
  const projection = state.projection
  const request = state.pendingRequest
  const [selection, setSelection] = useState<Selection>(emptySelection(''))
  const selectionKey = `${request?.request_id ?? ''}:${state.requestEpoch ?? 0}`
  const materialIds = new Set([...(projection?.hand ?? []),...(projection?.players.flatMap(p=>[...p.equipment,...Object.values(p.special_piles ?? {}).flat()]) ?? [])].map(c=>c.card_id))
  const activeSelection = effectiveSelection(selection, selectionKey, request, materialIds)
  const selectedCards = activeSelection.cards
  const selectedTargets = activeSelection.targets
  const selectedOption = activeSelection.option
  const selectionStorageKey = state.roomCode && state.seatId ? `sanguosha.selection.v1:${state.roomCode}:${state.seatId}` : ''
  const attemptedSelectionRestore = useRef(false)
  useEffect(() => {
    if (!request || !selectionStorageKey || attemptedSelectionRestore.current) return
    attemptedSelectionRestore.current = true
    try {
      const raw = sessionStorage.getItem(selectionStorageKey)
      if (!raw) return
      const saved = JSON.parse(raw)
      if (saved.requestId !== request.request_id) { sessionStorage.removeItem(selectionStorageKey); return }
      const option = typeof saved.option === 'string' && (request.choices.includes(saved.option) || request.eligible_card_ids.includes(saved.option)) ? saved.option : ''
      const targets = request.play_card_targets?.[option]?.targets ?? request.allowed_player_ids
      setSelection({requestId:selectionKey,option,mode: typeof saved.mode==='string' ? saved.mode : '',
        cards:Array.isArray(saved.cards) ? [...new Set<string>(saved.cards.filter((id:unknown)=>typeof id==='string' && request.eligible_card_ids.includes(id)))].slice(0,request.max_count || 1) : [],
        targets:Array.isArray(saved.targets) ? [...new Set<string>(saved.targets.filter((id:unknown)=>typeof id==='string' && targets.includes(id)))].slice(0,request.play_card_targets?.[option]?.max ?? request.max_count ?? 1) : []})
    } catch { /* A malformed local selection never changes the authoritative request. */ }
  },[request,selectionKey,selectionStorageKey])

  const [hint, setHint] = useState('')
  useEffect(() => {
    if (!hint) return
    const timer = window.setTimeout(() => setHint(''), 1200)
    return () => window.clearTimeout(timer)
  }, [hint, request?.request_id])
  const requestRef = useRef(request?.request_id)
  requestRef.current = request?.request_id
  const selectionKeyRef = useRef(selectionKey)
  selectionKeyRef.current = selectionKey
  function updateSelection(update: (current: typeof selection) => typeof selection) {
    setSelection((current) => {
      const next = update(effectiveSelection(current, selectionKeyRef.current, request, materialIds))
      if (selectionStorageKey && request) {
        try { sessionStorage.setItem(selectionStorageKey, JSON.stringify({...next,requestId:request.request_id})) } catch { /* Selection still works when browser storage is unavailable. */ }
      }
      return next
    })
  }
  function setSelectedCards(next: string[] | ((current: string[]) => string[])) {
    updateSelection((current) => ({ ...current, cards: typeof next === 'function' ? next(current.cards) : next }))
  }
  function setSelectedTargets(next: string[] | ((current: string[]) => string[])) {
    updateSelection((current) => ({ ...current, targets: typeof next === 'function' ? next(current.targets) : next }))
  }
  function setSelectedOption(option: string) { updateSelection((current) => ({ ...current, option })) }
  const [detailPlayer, setDetailPlayer] = useState<PlayerView | null>(null)
  const [vfxQuality, setVfxQuality] = useState<VfxQuality>(readVfxQuality)
  const [gameSpeed, setGameSpeed] = useState<GameSpeed>(readGameSpeed)
  useEffect(() => { actions.setPresentationSpeed?.(readGameSpeed()) }, [state.lobby?.host_id, state.seatId])
  const presentedEvent = usePresentation(state.publicEvents, gameSpeed,
    state.connection !== 'connected' ? 'connection-reset'
      : request?.player_id === state.seatId ? request.request_id : undefined, projection?.waiting !== undefined)
  const visibleEvents = presentedEvent ? [presentedEvent] : []
  const [godCues, setGodCues] = useState<Record<string, { mode: GodPortraitMode; id: number }>>({})
  const seenGodEvents = useRef(new Set<string>())
  const entryShown = useRef(new Set<string>())
  const nextGodCue = useRef(0)

  useEffect(() => {
    if (!projection) return
    for (const player of projection.players) {
      if (player.character_id === 'forest_god_lvbu' && !entryShown.current.has(player.player_id)) {
        entryShown.current.add(player.player_id)
        setGodCues((current) => ({ ...current, [player.player_id]: { mode: 'entry', id: ++nextGodCue.current } }))
      }
    }
  }, [projection])
  useEffect(() => {
    if (!projection) return
    for (const [index, event] of visibleEvents.entries()) {
      const identity = String(event.event_id ?? index + ':' + event.kind)
      if (seenGodEvents.current.has(identity)) continue
      seenGodEvents.current.add(identity)
      const kind = String(event.kind)
      let playerId = ''
      let mode: GodPortraitMode | null = null
      if (kind === 'DamageDealtEvent' || kind === 'PlayerDiedEvent') {
        playerId = String(event.target_id ?? '')
        mode = kind === 'PlayerDiedEvent' || (projection.players.find((item) => item.player_id === playerId)?.hp ?? 1) <= 0 ? 'dying' : 'hit'
      } else if (kind === 'CardUsedEvent' && String(event.definition_id ?? '').includes('slash')) {
        playerId = String(event.source_id ?? '')
        mode = 'attack'
      } else if (kind === 'GodSkillEvent' && String(event.skill_id ?? '') === 'shenfen') {
        playerId = String(event.source_id ?? '')
        mode = 'attack'
      } else if (kind === 'GameEndedEvent') {
        const winnerIds = Array.isArray(event.winner_ids) ? event.winner_ids.map(String) : []
        playerId = winnerIds.find((id) => projection.players.some((item) => item.player_id === id && item.character_id === 'forest_god_lvbu')) ?? ''
        mode = playerId ? 'victory' : null
      }
      if (mode && projection.players.some((item) => item.player_id === playerId && item.character_id === 'forest_god_lvbu')) {
        setGodCues((current) => ({ ...current, [playerId]: { mode, id: ++nextGodCue.current } }))
      }
    }
    if (seenGodEvents.current.size > 200) seenGodEvents.current = new Set(visibleEvents.map((event, index) => String(event.event_id ?? index + ':' + event.kind)))
  }, [presentedEvent, projection])

  if (!projection) return <main className="game-page table-background"><section className="paper-panel loading-panel">正在恢复牌桌……</section></main>

  const selfIndex = Math.max(0, projection.players.findIndex((player) => player.player_id === state.seatId))
  const self = projection.players[selfIndex]
  const opponents = [...projection.players.slice(selfIndex+1),...projection.players.slice(0,selfIndex)].filter(p=>p.player_id!==self.player_id)
  const playTargetSpec = request?.play_card_targets?.[selectedOption]
  const allowedTargets = new Set(playTargetSpec?.targets ?? request?.allowed_player_ids ?? [])
  const eligibleCards = new Set(request?.eligible_card_ids ?? [])
  const displayedCardIds = new Set([
    ...self.equipment.map((card) => card.card_id),
    ...projection.hand.map((card) => card.card_id),
    ...projection.shared_cards.map((card) => card.card_id),
    ...projection.players.flatMap((player) => [
      ...(player.revealed_hand ?? []).map((card) => card.card_id),
    ]),
  ])
  const publicCards = projection.players.flatMap((player) => [...player.equipment, ...player.judgments])
  const otherCardChoices = request?.request_type === 'choose_card' || request?.request_type === 'choose_cards'
    ? request.eligible_card_ids.filter((id) => !displayedCardIds.has(id)) : []
  const isCardRequest = !!request && ['respond_with_card', 'choose_card', 'choose_cards'].includes(request.request_type)
  const isTargetRequest = !!request && (['choose_player', 'choose_players'].includes(request.request_type) || !!playTargetSpec?.max)
  const choiceCardIds = new Set((request?.choices ?? []).filter((choice) => choice.startsWith('use:')).map((choice) => choice.slice(4)))
  const modeOptions = virtualOptions(request).filter(o=>o.split(':')[1]===activeSelection.mode)
  const cardEligible = (id: string) => activeSelection.mode ? modeOptions.some(o=>{ const ids=materials(o,materialIds); return ids.includes(id) && selectedCards.filter(c=>c!==id).every(c=>ids.includes(c)) }) : isCardRequest ? eligibleCards.has(id) : request?.request_type === 'choose_option' ? choiceCardIds.has(id) : false

  function toggleCard(id: string) {
    if (!request || requestRef.current !== request.request_id || state.connection !== 'connected') { setHint('当前响应已更新或连接恢复中'); return }
    if (state.decisionProcessing) { setHint('正在处理，请稍候'); return }
    if (!cardEligible(id)) { setHint(request.request_type === 'respond_with_card' ? '此牌不能用于当前响应' : '当前不能选择这张牌'); return }
    if (import.meta.env.DEV) console.debug('[game] click card', id, 'request', request.request_id, 'option', selectedOption)
    setHint('')
    if (activeSelection.mode) {
      const cards = selectedCards.includes(id) ? selectedCards.filter(c=>c!==id) : [...selectedCards,id]
      const option = modeOptions.find(o=>{const ids=materials(o,materialIds);return ids.length===cards.length && ids.every(c=>cards.includes(c))}) ?? ''
      updateSelection(current=>({...current,cards,option,targets:[]}))
      return
    }
    if (request.request_type === 'choose_option') {
      const next = selectedCards.includes(id) ? '' : 'use:' + id
      updateSelection((current) => ({ ...current, cards: next ? [id] : [], targets: [], option: next }))
      return
    }
    if (request.request_type === 'respond_with_card') setSelectedOption('')
    const max = request.max_count || 1
    setSelectedCards((current) => current.includes(id) ? current.filter((item) => item !== id) : max === 1 ? [id] : current.length < max ? [...current, id] : current)
  }
  function toggleTarget(id: string) {
    if (!request || requestRef.current !== request.request_id || state.decisionProcessing) { setHint('当前响应已更新'); return }
    if (!allowedTargets.has(id)) { setHint('当前不能选择这个目标'); return }
    setHint('')
    const max = playTargetSpec?.max || request.max_count || 1
    setSelectedTargets((current) => current.includes(id) ? current.filter((item) => item !== id) : max === 1 ? [id] : current.length < max ? [...current, id] : current)
  }
  function confirm() {
    if (!request || requestRef.current !== request.request_id || state.decisionProcessing) { setHint('当前响应已更新或正在处理'); return }
    let value: unknown = selectedOption
    if (request.request_type === 'respond_with_card') value = selectedOption.startsWith('virtual:') ? selectedOption : selectedCards[0]
    if (request.request_type === 'choose_card') value = selectedCards[0]
    if (request.request_type === 'choose_cards') value = selectedCards
    if (request.request_type === 'choose_player') value = selectedTargets[0]
    if (request.request_type === 'choose_players') value = selectedTargets
    if (playTargetSpec) value = { option: selectedOption, targets: selectedTargets }
    if (selectionStorageKey) { try { sessionStorage.removeItem(selectionStorageKey) } catch { /* Optional local selection cache. */ } }
    actions.submitDecision(request.request_id, value)
  }
  function submitImmediate(value: unknown) {
    if (!request || requestRef.current !== request.request_id || state.decisionProcessing) { setHint('当前响应已更新或正在处理'); return }
    setHint('')
    if (selectionStorageKey) { try { sessionStorage.removeItem(selectionStorageKey) } catch { /* Optional local selection cache. */ } }
    actions.submitDecision(request.request_id, value)
  }
  const minimum = request?.min_count ?? 1
  const selectionCount = isTargetRequest ? selectedTargets.length : activeSelection.mode ? (selectedOption ? 1 : 0) : selectedOption ? 1 : selectedCards.length
  const canConfirm = !!request && state.connection === 'connected' && (playTargetSpec
    ? selectedTargets.length >= (projection.hand.find(c=>c.card_id===selectedCards[0])?.definition_id==='trick.iron_chain' ? Math.max(1,playTargetSpec.min) : playTargetSpec.min) && selectedTargets.length <= playTargetSpec.max
    : selectionCount >= minimum && selectionCount <= (request.max_count || 1))
    && (request.exclusive_card_groups ?? []).every((group) => selectedCards.filter((id) => group.includes(id)).length <= 1)
    && (!selectedCards.length || selectedCards.length >= (request.minimum_nonempty_count ?? 0))
    && (!request.legal_card_sets?.length || request.legal_card_sets.some((cards) =>
      cards.length === selectedCards.length && cards.every((id) => selectedCards.includes(id))))
  const selectedCard = [...projection.hand, ...projection.shared_cards].find((card) => card.card_id === selectedCards[0])
  const chainSelected = selectedCard?.definition_id === 'trick.iron_chain' && !!playTargetSpec
  const summary = playTargetSpec && selectedCard ? `${selectedCard.name}${selectedTargets.length
    ? ' → ' + selectedTargets.map((id) => projection.players.find((player) => player.player_id === id)?.name ?? '该角色').join('、')
    : playTargetSpec.max ? ' → 请选择目标' : ''}` : ''
  const beamMode = request?.request_type === 'respond_with_card' ? 'protect' : selectedOption.includes('slash') || request?.required_definition_id?.includes('slash') ? 'attack' : 'normal'
  const detailGeneral = detailPlayer ? state.generals[detailPlayer.character_id] : undefined
  const latestEvent = visibleEvents[visibleEvents.length - 1] ?? projection.public_reveal ?? undefined
  const eventActorId = String(latestEvent?.source_id ?? latestEvent?.player_id ?? '')
  const eventTargetIds = [String(latestEvent?.target_id ?? ''), ...(Array.isArray(latestEvent?.target_ids) ? latestEvent.target_ids.map(String) : [])]
  const eventKind = String(latestEvent?.kind ?? '')
  const waiting = state.connection === 'connected' ? projection.waiting ?? (request ? {
    key: request.request_id, player_id: request.player_id, responding: request.request_type === 'respond_with_card',
    thinking: false, remaining_ms: request.remaining_ms, required_definition_id: request.required_definition_id ?? undefined, response_to: projection.combat?.definition_id,
  } : null) : null
  const thinkingId = waiting?.thinking ? waiting.player_id : state.connection === 'connected' && !request && eventKind === 'AIThinkingEvent' ? eventActorId : ''
  const responseId = waiting?.responding ? waiting.player_id : ''
  const combat = projection.combat
  const aoe = combat && ['trick.savage_assault', 'trick.archery_attack'].includes(combat.definition_id) ? combat : null
  const aoeState = (id: string) => !aoe?.target_ids.includes(id) ? undefined : aoe.resolved_target_ids?.includes(id) ? 'resolved' : aoe.current_target_id === id ? 'current' : 'pending'

  const temporaryPanel = projection.shared_cards.length > 0 || (!!request && (request.request_type === 'choose_card' || request.request_type === 'choose_cards' && (!!projection.players.find((p) => p.player_id === request.subject_player_id)?.revealed_hand?.length || Object.values(projection.players.find((p) => p.player_id === request.subject_player_id)?.special_piles ?? {}).some(cards=>cards.some(card=>request.eligible_card_ids?.includes(card.card_id))))) && !!request.subject_player_id && (otherCardChoices.length > 0 || !!projection.players.find((p) => p.player_id === request.subject_player_id)?.revealed_hand?.some((card) => request.eligible_card_ids?.includes(card.card_id))))
  return <main className="game-page table-background">
    <LandscapeGate />
    {temporaryPanel && <TemporaryInteractionPanel projection={projection} request={request} seatId={state.seatId} connected={state.connection === 'connected'} processing={!!state.decisionProcessing} selected={selectedCards} canConfirm={canConfirm} onSelect={toggleCard} onConfirm={confirm} onPass={() => submitImmediate({ pass: true })} requestControls={request && request.request_type !== 'choose_card' ? <DecisionPrompt request={request} projection={projection} canConfirm={canConfirm} processing={!!state.decisionProcessing} summary={summary} onConfirm={confirm} onCancel={() => setSelectedCards([])} onPass={() => submitImmediate({ pass: true })} onPassRoot={() => submitImmediate({ pass: true, scope: 'root_trick' })} onBoolean={submitImmediate} onOption={submitImmediate} /> : undefined} />}
    <header className="game-hud"><div><span>第 {projection.turn_number} 回合</span><strong>{phaseNames[projection.current_phase] ?? projection.current_phase}</strong>{state.updateAvailable && <small className="game-update-note">新版本可用</small>}</div><div className="pile-stats"><span>牌堆 {projection.deck_count}</span><span>弃牌 {projection.discard_count}</span><label>对局速度 <select aria-label="对局速度" value={gameSpeed} onChange={(event) => { const value = event.target.value as GameSpeed; setGameSpeed(value); actions.setPresentationSpeed?.(value); localStorage.setItem('sanguosha.web.speed', value) }}><option value="slow">慢</option><option value="normal">正常</option><option value="fast">快</option></select></label><label className="vfx-quality-control">画质 <select aria-label="战斗特效画质" value={vfxQuality} onChange={(event) => { const value = event.target.value as VfxQuality; setVfxQuality(value); saveVfxQuality(value) }}><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label><button onClick={actions.returnHome}>离开牌局</button></div></header>
    <section className={'game-board' + (projection.players.length === 8 ? ' eight-seats' : projection.players.length <= 4 ? ' small-party-seats' : '')}>
      <CombatVFXLayer players={projection.players} targets={selectedTargets} mode={beamMode} events={visibleEvents} quality={vfxQuality} />
      {opponents.map((player, index) => <PlayerPanel key={player.player_id} player={player} phase={projection.current_phase} aoeState={aoeState(player.player_id)} position={(positionsSmall[projection.players.length] ?? (projection.players.length === 8 ? positionsEight : positions))[index]} selected={selectedTargets.includes(player.player_id)} selectable={isTargetRequest && allowedTargets.has(player.player_id)} responding={responseId === player.player_id} waiting={waiting?.player_id === player.player_id ? waiting : undefined} thinking={thinkingId === player.player_id} eventKind={eventTargetIds.includes(player.player_id) || eventActorId === player.player_id ? eventKind : undefined} eventActor={eventActorId === player.player_id} eventTarget={latestEvent?.presentation_phase === 'target' && eventTargetIds.includes(player.player_id)} eventCue={latestEvent} godCue={godCues[player.player_id]} vfxQuality={vfxQuality} onSelect={() => toggleTarget(player.player_id)} onDetail={() => setDetailPlayer(player)} />)}
      <EventStage event={latestEvent} players={projection.players} combat={combat} />
      <aside className="recent-actions" aria-label="最近动作"><small>最近动作</small>{state.publicEvents.filter(e => /^(CardUsedEvent|CardRespondedEvent|VirtualResponseEvent|SkillEvent|GodSkillEvent)$/.test(String(e.kind))).slice(-4).reverse().map((e, i) => {
        const name = (id: unknown) => projection.players.find(p => p.player_id === id)?.character_name ?? '该角色'
        const targets = Array.isArray(e.target_ids) ? e.target_ids : (e.base_action as CombatContext | undefined)?.target_ids ?? []
        const message = '【' + String(e.skill_name ?? cardNames[String(e.definition_id)] ?? e.card_name ?? '技能') + '】 ' + name(e.source_id) + (targets.length ? ' → ' + targets.map(name).join('、') : '')
        return <div key={String(e.event_id ?? i)} title={message}>{message}</div>
      })}{projection.public_card_history?.length ? <details className="public-card-history"><summary>公开牌记录</summary>{projection.public_card_history.map((event,index)=><div key={index}>{projection.players.find(p=>p.player_id===(event.player_id ?? event.source_id))?.character_name} · {event.kind==='DiscardEvent' ? (event.reason==='recast' ? '重铸' : '弃置') : event.kind==='JudgmentEvent' ? '判定' : '展示'}：{event.kind==='DelayedResultEvent' ? String(event.message ?? '') : (event.cards as CardView[] ?? []).map((c,i)=><span key={c.card_id}>{i>0?'、':''}<SuitText suit={c.suit} rank={c.rank} /> {c.name}</span>)}</div>)}</details> : null}</aside>
      {!temporaryPanel && <SharedCards cards={projection.shared_cards} selected={selectedCards} eligible={eligibleCards} onSelect={toggleCard} />}
      {!temporaryPanel && otherCardChoices.length > 0 && <section className="shared-card-pool" aria-label="可选目标牌">
        <p>选择目标的一张牌</p><div>{otherCardChoices.map((id) =>
          <button key={id} className={'brush-button compact' + (selectedCards.includes(id) ? ' selected' : '')}
            onClick={() => toggleCard(id)}>{id.startsWith('hidden-hand:') ? '暗置手牌 ' + id.split(':')[1] : request?.choice_labels?.[id] ?? publicCards.find((card) => card.card_id === id)?.name ?? '可选牌'}</button>)}</div>
      </section>}
      {request?.player_id === self.player_id && projection.players.filter((player) => !!player.revealed_hand?.length).map((player) =>
        <section key={player.player_id} className="shared-card-pool" aria-label="攻心查看手牌">
          <p>{request.prompt.match(/【([^】]+)】/)?.[1] ?? '攻心'} · {player.name} 的手牌</p><div>{player.revealed_hand!.map((card) =>
            <HandCard key={card.card_id} card={card} selected={false}
              eligible={request.choices.includes(card.card_id)}
              onClick={() => request.choices.includes(card.card_id) ? submitImmediate(card.card_id) : setHint('当前不能选择这张牌')} />)}</div>
        </section>)}
      <div className="table-piles" aria-label="牌桌牌堆">
        <div><span className="table-deck" aria-hidden="true" /><small>牌堆 {projection.deck_count}</small></div>
        <div>{projection.discard_top ? <div className="discard-top"><HandCard card={projection.discard_top} selected={false} eligible={false} onClick={() => undefined} /></div> : <span className="table-discard" aria-hidden="true" />}<small>弃牌 {projection.discard_count}</small></div>
      </div>
      <div className="self-area">
        <div className="operation-area" aria-label="操作区">{request && !temporaryPanel && <DecisionPrompt request={request} projection={projection} canConfirm={canConfirm} processing={!!state.decisionProcessing} summary={summary} onConfirm={confirm} onCancel={() => updateSelection(() => emptySelection(selectionKey))} onPass={() => submitImmediate({ pass: true })} onPassRoot={() => submitImmediate({ pass: true, scope: 'root_trick' })} onBoolean={submitImmediate} onOption={submitImmediate} onRecast={chainSelected ? () => submitImmediate({option:selectedOption,targets:[]}) : undefined} />}</div>
        <PlayerPanel separateZones player={self} phase={projection.current_phase} aoeState={aoeState(self.player_id)} position="self" selected={selectedTargets.includes(self.player_id)} selectable={isTargetRequest && allowedTargets.has(self.player_id)} responding={responseId === self.player_id} waiting={waiting?.player_id === self.player_id ? waiting : undefined} thinking={thinkingId === self.player_id} eventKind={eventTargetIds.includes(self.player_id) || eventActorId === self.player_id ? eventKind : undefined} eventActor={eventActorId === self.player_id} eventTarget={latestEvent?.presentation_phase === 'target' && eventTargetIds.includes(self.player_id)} eventCue={latestEvent} godCue={godCues[self.player_id]} vfxQuality={vfxQuality} onSelect={() => toggleTarget(self.player_id)} onDetail={() => setDetailPlayer(self)} />
        <div className="skill-area" aria-label="技能区"><SkillBar player={self} general={state.generals[self.character_id]} skillNames={Object.fromEntries(Object.values(state.generals).flatMap((general) => general.skills.map((skill) => [skill.id, skill.name])))} request={request} chosen={selectedOption || virtualOptions(request).find(o=>o.split(':')[1]===activeSelection.mode) || ''} onUnavailable={() => setHint('此技能当前不可使用')} onChoose={(option) => { if (state.decisionProcessing) return; setHint(''); const mode=option.startsWith('virtual:') && materials(option,materialIds).length ? option.split(':')[1] : ''; updateSelection(()=>({...emptySelection(selectionKey), mode: activeSelection.mode===mode && mode ? '' : mode, option: mode ? '' : selectedOption===option ? '' : option})) }} /></div>
        <section className="equipment-area" aria-label="装备与判定区">
          <div className="equipment-slots">{[['weapon','武器'],['armor','防具'],['defensive_horse','+1马'],['offensive_horse','-1马'],['treasure','宝物']].map(([slot,label]) => {
            const card=self.equipment.find(c=>c.equipment_slot===slot)
            return card ? <button key={slot} aria-label={'装备 '+card.name} aria-pressed={selectedCards.includes(card.card_id)} aria-disabled={!cardEligible(card.card_id)} className={'equipment-token equipment-choice'+(selectedCards.includes(card.card_id)?' selected':'')+(cardEligible(card.card_id)?' selectable':' unavailable')} onClick={()=>toggleCard(card.card_id)} title={card.details}><small>{label}</small><b>{card.name}{card.equipment_slot==='defensive_horse' ? ' +1' : card.equipment_slot==='offensive_horse' ? ' -1' : ''}</b><SuitText suit={card.suit} rank={card.rank} />{selectedCards.includes(card.card_id)&&<span className="selected-check">✓</span>}</button> : <div key={slot} className="equipment-empty">{label}</div>
          })}</div>
          <div className="local-judgments">判定：{self.judgments.length ? self.judgments.map(card=><span key={card.card_id} title={card.details}>{card.name} <SuitText suit={card.suit} rank={card.rank} /></span>) : '无'}</div>
          {activeSelection.mode && <div className="view-as-materials" aria-label="技能区域材料">{Object.values(self.special_piles ?? {}).flat().filter(c=>cardEligible(c.card_id)).map(card=><button key={card.card_id} aria-pressed={selectedCards.includes(card.card_id)} className={selectedCards.includes(card.card_id) ? 'selected' : ''} onClick={()=>toggleCard(card.card_id)}>{card.name} <SuitText suit={card.suit} rank={card.rank} /></button>)}</div>}
        </section>
        <div className="hand" aria-label="手牌区" style={{'--hand-count':Math.max(1,projection.hand.length),'--hand-divisor':Math.max(1,projection.hand.length-1)} as CSSProperties}><div className="hand-fan">{projection.hand.map((card) => <HandCard key={card.card_id} card={card} selected={selectedCards.includes(card.card_id)} eligible={cardEligible(card.card_id)} onClick={() => toggleCard(card.card_id)} />)}</div></div>
      </div>
    </section>
    {hint && <div className="interaction-hint" role="status">{hint}</div>}
    {state.error && <div className="game-error">{state.error}<button onClick={actions.clearError}>×</button></div>}
    {detailPlayer && <GeneralDetailPanel player={detailPlayer} general={detailGeneral} quality={vfxQuality} onClose={() => setDetailPlayer(null)} />}
    {(state.result || projection.result) && <ResultOverlay result={state.result || projection.result || ''} identity={self.identity_label} godVictory={self.character_id === 'forest_god_lvbu'} quality={vfxQuality} onHome={actions.returnHome} onReplay={() => { actions.returnHome(); actions.createRoom(state.playerName || '玩家', true, state.lobby?.mode_id) }} />}
  </main>
}
