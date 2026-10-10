import type { PendingRequest, Projection } from '../types'
import { useGame } from '../state/GameContext'
import { SkillTooltip, optionMetadata } from './SkillTooltip'
import { battlePrompt } from '../labels'
import { BattleText } from './SuitText'
import { cardNames } from './cardUtil'

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

export function DecisionPrompt({ request, projection, canConfirm, processing, summary, progress = '', reason = '', onConfirm, onCancel, onPass, onPassRoot, onBoolean, onOption, onRecast }: {
  onRecast?: () => void
  request: PendingRequest
  projection: Projection
  canConfirm: boolean
  processing: boolean
  summary: string
  progress?: string
  reason?: string
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
    <div className="prompt-copy"><strong><BattleText text={prompt}/></strong>
      <small className="prompt-status">{progress && <b className="prompt-progress">{progress}</b>}{reason ? <span className="prompt-reason">{reason}</span> : !progress && <span>选择后点击确认，操作才会提交</span>}</small></div>
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
