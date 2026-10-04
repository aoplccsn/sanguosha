import { useId, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import type { GeneralInfo, SkillInfo } from '../types'

export function optionMetadata(value: string, catalog: Record<string, GeneralInfo>) {
  const parts = value.split(':')
  const general = catalog[parts[0]]
  const skills = Object.values(catalog).flatMap(item => item.skills)
  const skill = general ? general.skills.find(item => item.id === parts.at(-1))
    : skills.find(item => item.id === (parts[0] === 'skill' || parts[0] === 'virtual' ? parts[1] : value))
  return { general, skills: skill ? [skill] : general?.skills ?? [] }
}

export function SkillTooltip({ children, general, skills }: { children: ReactNode; general?: GeneralInfo; skills: SkillInfo[] }) {
  const id = useId()
  const [open, setOpen] = useState(false)
  if (!skills.length) return <>{children}</>
  return <span className="skill-detail-trigger" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}
    onFocus={() => setOpen(true)} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}
    onKeyDown={event => { if (event.key === 'Escape') setOpen(false) }} aria-describedby={open ? id : undefined}>
    {children}
    <button type="button" className="skill-info" aria-label={'查看' + (general?.name ?? skills[0].name) + '技能说明'}
      aria-expanded={open} aria-controls={id} onClick={event => { event.stopPropagation(); setOpen(true) }}>ⓘ</button>
    {open && createPortal(<aside id={id} role="tooltip" className="skill-tooltip">
      {general && <header>{general.name} · {({ wei: '魏', shu: '蜀', wu: '吴', qun: '群', god: '神' } as Record<string, string>)[general.kingdom] ?? '群'} · {general.max_hp} 体力</header>}
      {skills.map(skill => <section key={skill.id}><strong>{skill.name}</strong><p>{skill.description || '技能说明暂未载入'}</p></section>)}
    </aside>, document.body)}
  </span>
}
