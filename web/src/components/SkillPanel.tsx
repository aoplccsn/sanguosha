import type { GeneralInfo, PendingRequest, PlayerView, SkillInfo } from '../types'
import { useGame } from '../state/GameContext'
import { SkillTooltip, optionMetadata } from './SkillTooltip'

// One state class per button; CSS styles each with brightness/border/typography only.
function skillClass(skill: SkillInfo | undefined, player: PlayerView, usable: boolean, selected: boolean) {
  const marks = player.marks ?? {}
  const id = skill?.id ?? ''
  const consumed = !!skill && ['awakening', 'limited'].includes(skill.type) && !!(marks[id + '_used'] || marks[id + '_awakened'] || (skill.type === 'awakening' && marks[id]))
  return ['skill-btn', selected ? 'selected' : usable ? 'available' : 'unavailable',
    skill?.type === 'locked' ? 'locked' : '', consumed ? 'consumed' : ''].filter(Boolean).join(' ')
}

export function SkillBar({ player, general, skillNames, request, chosen, onChoose, onUnavailable }: { player: PlayerView; general?: GeneralInfo; skillNames: Record<string, string>; request: PendingRequest | null; chosen: string; onChoose(value: string): void; onUnavailable(): void }) {
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
      return <SkillTooltip key={label} skills={metadata ? [metadata] : []}><button aria-disabled={!option} className={skillClass(metadata, player, !!option, chosen === option)} onClick={() => option ? onChoose(option) : onUnavailable()}>{label}</button></SkillTooltip>
    })}
    {skillOptions.filter((option) => !general?.skills.some((skill) => skill.id === option.split(':')[1])
      && !(option.split(':')[1] === 'guhuo' && player.skill_labels.some((label) => label.split(' · ')[0] === '蛊惑'))).map((option) =>
      <SkillTooltip key={option} {...optionMetadata(option, state.generals)}><button className={'skill-btn available' + (chosen === option ? ' selected' : '')} onClick={() => onChoose(option)}>{request?.choice_labels?.[option] ?? skillNames[option.split(':')[1]] ?? '技能选项'}</button></SkillTooltip>)}
  </div>
}
