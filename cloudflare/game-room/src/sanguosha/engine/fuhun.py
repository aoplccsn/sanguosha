"""Fuhun reuses the shared two-hand virtual Slash and normal damage resolution."""
from dataclasses import dataclass
from .view_as import UseSpear, UseSpearHandler
from .card_rules import InvalidCardUse
from .card_limits import legal_pairs
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.enums import Phase


@dataclass(frozen=True, slots=True)
class UseFuhun(UseSpear):
    pass


def available(state, pid, skills, rule):
    usage=state.play_usage
    limit=rule.usage_limit(state,pid)
    return (state.players[pid].is_alive and skills.has(state,pid,'fuhun')
            and state.current_player_id==pid and state.current_phase is Phase.PLAY
            and usage is not None and usage.player_id==pid and usage.turn_number==state.turn_number
            and bool(legal_pairs(state,pid,state.cards_in(ZoneRef(ZoneType.HAND,pid))))
            and rule.can_use(state,pid) and (limit is None or usage.count('basic.slash')<limit)
            and bool(rule.target_candidates(state,pid)))


class UseFuhunHandler(UseSpearHandler):
    label='【伏魂】'
    skill_id='fuhun'

    def validate_start(self,state,a):
        if not available(state,a.player_id,self.provider.skills,self.provider.validator.rules.get('basic.slash')):
            raise InvalidCardUse('伏魂不可用')


def grant_after_damage(state, action, skills):
    virtual=getattr(action,'virtual_card',None)
    source=action.source_id
    if (skills is None or source not in state.players or not state.players[source].is_alive
            or virtual is None or virtual.skill_id!='fuhun'
            or getattr(action,'card_kind','')!='slash'
            or state.current_player_id!=source or state.current_phase is not Phase.PLAY
            or not skills.has(state,source,'fuhun')):
        return
    player=state.players[source]
    native=skills.characters.get(player.character_id)
    for skill in ('wusheng','paoxiao'):
        if skill not in player.granted_skills and (native is None or skill not in native.skill_ids):
            player.granted_skills[skill]='fuhun:'+str(state.turn_number)


def clear_grants(state,pid):
    player=state.players[pid]
    for skill in ('wusheng','paoxiao'):
        if player.granted_skills.get(skill,'').startswith('fuhun:'):
            del player.granted_skills[skill]
