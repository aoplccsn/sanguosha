import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { effectiveSelection, emptySelection, virtualOptions, materials, type Selection } from '../state/selection'
import type { CardView, PlayerView, CombatContext } from '../types'
import { useGame } from '../state/GameContext'
import { TemporaryInteractionPanel } from './TemporaryInteractionPanel'
import { readGameSpeed, type GameSpeed } from '../presentation/pacing'
import { usePresentation } from '../presentation/usePresentation'
import { phaseNames } from '../labels'
import { SuitText } from './SuitText'
import { CombatVFXLayer } from './CombatVFXLayer'
import type { GodPortraitMode } from './GodPortrait'
import { readVfxQuality, saveVfxQuality, type VfxQuality } from '../vfx/CombatVFXRuntime'
import { LandscapeGate } from './LandscapeGate'
import { seatAnchors, boardClass } from '../tableLayout'
import { cardNames } from './cardUtil'
import { PlayerPanel } from './PlayerPanel'
import { HandCard, SharedCards } from './HandArea'
import { SkillBar } from './SkillPanel'
import { DecisionPrompt } from './ActionPrompt'
import { GeneralDetailPanel } from './GeneralDetail'
import { EventStage } from './EventStage'
import { EquipmentArea } from './EquipmentArea'
import { ResultOverlay } from './ResultOverlay'

// Stable public surface for tests and sibling components.
export { PlayerPanel, portraitState } from './PlayerPanel'
export { HandCard } from './HandArea'
export { GeneralDetailPanel } from './GeneralDetail'
export { ResultOverlay } from './ResultOverlay'

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
  const chainCard = projection.hand.find(c => c.card_id === selectedCards[0])?.definition_id === 'trick.iron_chain'
  // Empty string means Confirm is legal; otherwise it is the reason shown beside the disabled button.
  const countBlocker = playTargetSpec
    ? (() => {
      const need = chainCard ? Math.max(1, playTargetSpec.min) : playTargetSpec.min
      if (selectedTargets.length < need) return `还需选择 ${need - selectedTargets.length} 个目标`
      return selectedTargets.length > playTargetSpec.max ? `最多选择 ${playTargetSpec.max} 个目标` : ''
    })()
    : selectionCount < minimum ? `还需选择 ${minimum - selectionCount} 项`
      : selectionCount > (request?.max_count || 1) ? `最多选择 ${request?.max_count || 1} 项` : ''
  const confirmBlocker = !request ? '' : state.connection !== 'connected' ? '连接恢复中，请稍候' : countBlocker
    || (!(request.exclusive_card_groups ?? []).every((group) => selectedCards.filter((id) => group.includes(id)).length <= 1) ? '所选牌不能同时使用'
      : selectedCards.length && selectedCards.length < (request.minimum_nonempty_count ?? 0) ? `至少选择 ${request.minimum_nonempty_count} 张，或不选`
        : request.legal_card_sets?.length && !request.legal_card_sets.some((cards) => cards.length === selectedCards.length && cards.every((id) => selectedCards.includes(id))) ? '所选牌组合不合法' : '')
  const canConfirm = !!request && !confirmBlocker
  const progressMax = playTargetSpec?.max ?? request?.max_count ?? 0
  const progress = request && (isTargetRequest || isCardRequest) && progressMax > 1
    ? `已选${isTargetRequest ? '目标' : ''} ${selectionCount} / ${progressMax}` : ''
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
    {temporaryPanel && <TemporaryInteractionPanel projection={projection} request={request} seatId={state.seatId} connected={state.connection === 'connected'} processing={!!state.decisionProcessing} selected={selectedCards} canConfirm={canConfirm} onSelect={toggleCard} onConfirm={confirm} onPass={() => submitImmediate({ pass: true })} requestControls={request && request.request_type !== 'choose_card' ? <DecisionPrompt request={request} projection={projection} canConfirm={canConfirm} processing={!!state.decisionProcessing} summary={summary} progress={progress} reason={confirmBlocker} onConfirm={confirm} onCancel={() => setSelectedCards([])} onPass={() => submitImmediate({ pass: true })} onPassRoot={() => submitImmediate({ pass: true, scope: 'root_trick' })} onBoolean={submitImmediate} onOption={submitImmediate} /> : undefined} />}
    <header className="game-hud"><div><span>第 {projection.turn_number} 回合</span><strong>{phaseNames[projection.current_phase] ?? projection.current_phase}</strong>{state.updateAvailable && <small className="game-update-note">新版本可用</small>}</div><div className="pile-stats"><span>牌堆 {projection.deck_count}</span><span>弃牌 {projection.discard_count}</span><label>对局速度 <select aria-label="对局速度" value={gameSpeed} onChange={(event) => { const value = event.target.value as GameSpeed; setGameSpeed(value); actions.setPresentationSpeed?.(value); localStorage.setItem('sanguosha.web.speed', value) }}><option value="slow">慢</option><option value="normal">正常</option><option value="fast">快</option></select></label><label className="vfx-quality-control">画质 <select aria-label="战斗特效画质" value={vfxQuality} onChange={(event) => { const value = event.target.value as VfxQuality; setVfxQuality(value); saveVfxQuality(value) }}><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label><button onClick={actions.returnHome}>离开牌局</button></div></header>
    <section className={boardClass(projection.players.length)}>
      <CombatVFXLayer players={projection.players} targets={selectedTargets} mode={beamMode} events={visibleEvents} quality={vfxQuality} />
      {opponents.map((player, index) => <PlayerPanel key={player.player_id} player={player} phase={projection.current_phase} aoeState={aoeState(player.player_id)} position={seatAnchors(projection.players.length)[index]} dimmed={isTargetRequest && !allowedTargets.has(player.player_id)} selected={selectedTargets.includes(player.player_id)} selectable={isTargetRequest && allowedTargets.has(player.player_id)} responding={responseId === player.player_id} waiting={waiting?.player_id === player.player_id ? waiting : undefined} thinking={thinkingId === player.player_id} eventKind={eventTargetIds.includes(player.player_id) || eventActorId === player.player_id ? eventKind : undefined} eventActor={eventActorId === player.player_id} eventTarget={latestEvent?.presentation_phase === 'target' && eventTargetIds.includes(player.player_id)} eventCue={latestEvent} godCue={godCues[player.player_id]} vfxQuality={vfxQuality} onSelect={() => toggleTarget(player.player_id)} onDetail={() => setDetailPlayer(player)} />)}
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
        <div className="operation-area" aria-label="操作区">{request && !temporaryPanel && <DecisionPrompt request={request} projection={projection} canConfirm={canConfirm} processing={!!state.decisionProcessing} summary={summary} progress={progress} reason={confirmBlocker} onConfirm={confirm} onCancel={() => updateSelection(() => emptySelection(selectionKey))} onPass={() => submitImmediate({ pass: true })} onPassRoot={() => submitImmediate({ pass: true, scope: 'root_trick' })} onBoolean={submitImmediate} onOption={submitImmediate} onRecast={chainSelected ? () => submitImmediate({option:selectedOption,targets:[]}) : undefined} />}</div>
        <PlayerPanel separateZones player={self} phase={projection.current_phase} aoeState={aoeState(self.player_id)} position="self" selected={selectedTargets.includes(self.player_id)} selectable={isTargetRequest && allowedTargets.has(self.player_id)} responding={responseId === self.player_id} waiting={waiting?.player_id === self.player_id ? waiting : undefined} thinking={thinkingId === self.player_id} eventKind={eventTargetIds.includes(self.player_id) || eventActorId === self.player_id ? eventKind : undefined} eventActor={eventActorId === self.player_id} eventTarget={latestEvent?.presentation_phase === 'target' && eventTargetIds.includes(self.player_id)} eventCue={latestEvent} godCue={godCues[self.player_id]} vfxQuality={vfxQuality} onSelect={() => toggleTarget(self.player_id)} onDetail={() => setDetailPlayer(self)} />
        <div className="skill-area" aria-label="技能区"><SkillBar player={self} general={state.generals[self.character_id]} skillNames={Object.fromEntries(Object.values(state.generals).flatMap((general) => general.skills.map((skill) => [skill.id, skill.name])))} request={request} chosen={selectedOption || virtualOptions(request).find(o=>o.split(':')[1]===activeSelection.mode) || ''} onUnavailable={() => setHint('此技能当前不可使用')} onChoose={(option) => { if (state.decisionProcessing) return; setHint(''); const mode=option.startsWith('virtual:') && materials(option,materialIds).length ? option.split(':')[1] : ''; updateSelection(()=>({...emptySelection(selectionKey), mode: activeSelection.mode===mode && mode ? '' : mode, option: mode ? '' : selectedOption===option ? '' : option})) }} /></div>
        <EquipmentArea player={self} selectedCards={selectedCards} mode={!!activeSelection.mode} eligible={cardEligible} onToggle={toggleCard} />
        <div className="hand" aria-label="手牌区" data-active={request?.player_id === self.player_id} style={{'--hand-count':Math.max(1,projection.hand.length),'--hand-divisor':Math.max(1,projection.hand.length-1)} as CSSProperties}><div className="hand-fan">{projection.hand.map((card) => <HandCard key={card.card_id} card={card} selected={selectedCards.includes(card.card_id)} eligible={cardEligible(card.card_id)} onClick={() => toggleCard(card.card_id)} />)}</div></div>
      </div>
    </section>
    {hint && <div className="interaction-hint" role="status">{hint}</div>}
    {state.error && <div className="game-error">{state.error}<button onClick={actions.clearError}>×</button></div>}
    {detailPlayer && <GeneralDetailPanel player={detailPlayer} general={detailGeneral} quality={vfxQuality} onClose={() => setDetailPlayer(null)} />}
    {(state.result || projection.result) && <ResultOverlay result={state.result || projection.result || ''} identity={self.identity_label} godVictory={self.character_id === 'forest_god_lvbu'} quality={vfxQuality} onHome={actions.returnHome} onReplay={() => { actions.returnHome(); actions.createRoom(state.playerName || '玩家', true, state.lobby?.mode_id) }} />}
  </main>
}

