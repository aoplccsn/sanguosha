import type { GeneralInfo, PlayerView } from '../types'
import { generalPortrait } from '../assets'
import { DynamicPortrait } from './DynamicPortrait'
import { idlePortrait } from '../idlePortraits'
import { skillTypeLabel } from '../labels'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

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
