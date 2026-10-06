"""Native skill eligibility and exact Zhiti event predicates."""
from sanguosha.model.enums import SkillType,Phase
from .remaining_gods import RemainingGodAction
from .distance import DistanceSystem
from .events import Event

# Frozen Noname unique/non-gainable skills and its explicit classic banned list.
SPECIAL_EXCLUDED=frozenset(('buqu','songci','guhuo','huashen','qixing','kuangfeng','rage','shenfen','jilue'))


def borrowable(state,target,skills):
    character=skills.characters.get(state.players[target].character_id)
    if character is None:return ()
    return tuple(s for s in character.skill_ids if s not in SPECIAL_EXCLUDED
        and skills.skills[s].skill_type not in (SkillType.LIMITED,SkillType.AWAKENING)
        and not any(skills.skills[s].metadata.get(key) for key in ('lord','limited','awakening','hidden','hidden_skill','mission','duty','special','charlotte','unique')))


def qualifies(state,owner,opponent,skills,definitions):
    return (opponent in state.players and owner!=opponent and state.players[owner].is_alive
        and state.players[opponent].is_alive and skills.has(state,owner,'zhiti')
        and state.players[owner].abolished_equipment_slots
        and state.players[opponent].hp<state.players[opponent].max_hp
        and DistanceSystem(definitions).can_reach_with_slash(state,owner,opponent))


def hand_penalty(state,pid,skills,definitions):
    p=state.players[pid]
    if p.hp>=p.max_hp:return 0
    distance=DistanceSystem(definitions)
    return sum(q!=pid and state.players[q].is_alive and skills.has(state,q,'zhiti')
        and distance.can_reach_with_slash(state,q,pid) for q in state.seat_order)


def damage_reaction(state,f,skills,definitions):
    if f.step_index!=1 or skills is None:return None
    a=f.action
    if not f.local.get('zhiti_damage_checked'):
        f.local['zhiti_damage_checked']=True
        if qualifies(state,a.target_id,a.source_id,skills,definitions):
            return RemainingGodAction(a.action_id+':zhiti',a.target_id,'zhiti_restore',a.source_id)
    if not f.local.get('duorui_checked'):
        f.local['duorui_checked']=True
        from .skill_leases import leases
        source=a.source_id
        if (source in state.players and source!=a.target_id and state.players[source].is_alive and state.players[a.target_id].is_alive
            and state.current_player_id==source and state.current_phase is Phase.PLAY and skills.has(state,source,'duorui')
            and source not in leases(state) and borrowable(state,a.target_id,skills)):
            return RemainingGodAction(a.action_id+':duorui',source,'duorui',a.target_id)
    return None


def event_reactions(state,event,skills,definitions):
    if not isinstance(event,Event) or event.event_type not in ('pindian_resolved','duel_resolved'):return ()
    winner=event.metadata.get('winner_id');loser=event.metadata.get('loser_id')
    return (RemainingGodAction(event.event_id+':zhiti',winner,'zhiti_restore',loser),) if winner in state.players and qualifies(state,winner,loser,skills,definitions) else ()
