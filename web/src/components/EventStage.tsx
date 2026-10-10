import type { CardView, CombatContext, PlayerView, PublicEvent } from '../types'
import { useGame } from '../state/GameContext'
import { SuitText } from './SuitText'
import { assetForCard, cardNames } from './cardUtil'

export function EventStage({ event, players, combat }: { event?: PublicEvent; players: PlayerView[]; combat?: CombatContext | null }) {
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
