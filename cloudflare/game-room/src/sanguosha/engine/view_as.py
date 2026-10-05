"""Spear activation uses two hand costs and the normal shared Slash counter."""
from dataclasses import dataclass
from .actions import Action,StepResult
from .events import CardUsedEvent
from .card_use import LegalPlayActionProvider
from .card_rules import InvalidCardUse
from .card_moves import CardMove,CardMoveReason
from .requests import PendingRequest,RequestType
from .military_basics import equipped,SlashSequence
from .suits import effective_suit
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.enums import EquipmentSlot,Phase
from sanguosha.model.zones import ZoneRef,ZoneType

@dataclass(frozen=True,slots=True)
class UseSpear(Action):
    player_id: str

class MilitaryPlayOptions(LegalPlayActionProvider):
    def spear_legal(self,state,pid):
        from .card_limits import legal_pairs
        rule = self.validator.rules.get('basic.slash')
        limit = rule.usage_limit(state, pid)
        usage = state.play_usage
        return (equipped(state,pid,EquipmentSlot.WEAPON)=='equipment.weapon.serpent_spear'
                and bool(legal_pairs(state,pid,state.cards_in(ZoneRef(ZoneType.HAND,pid))))
                and usage is not None and rule.can_use(state, pid)
                and (limit is None or usage.count('basic.slash') < limit)
                and bool(rule.target_candidates(state,pid)))
    def options(self,state,pid):
        ordinary=super().options(state,pid)
        return (*ordinary,'virtual:spear') if self.spear_legal(state,pid) else ordinary
    def build_action(self,state,pid,option,aid):
        if option=='virtual:spear':
            if not self.spear_legal(state,pid):
                raise InvalidCardUse('spear unavailable')
            return UseSpear(aid,pid)
        return super().build_action(state,pid,option,aid)

class UseSpearHandler:
    label = "丈八蛇矛"
    skill_id = ""
    def __init__(self,provider,moves):
        self.provider=provider
        self.moves=moves
    def validate_start(self,state,a):
        if state.current_player_id!=a.player_id or state.current_phase is not Phase.PLAY or not self.provider.spear_legal(state,a.player_id):
            raise InvalidCardUse('invalid spear use')
    def step(self,state,f):
        a=f.action
        hand=ZoneRef(ZoneType.HAND,a.player_id)
        if f.step_index==0:
            self.validate_start(state,a)
            from .card_limits import legal_pairs
            f.step_index=1
            return StepResult.ask(PendingRequest(a.action_id+':cost',a.player_id,RequestType.CHOOSE_CARDS,
                self.label+'：选择两张手牌',a.action_id,f.frame_id,eligible_card_ids=state.cards_in(hand),min_count=2,max_count=2,
                legal_card_sets=legal_pairs(state,a.player_id,state.cards_in(hand))))
        if f.step_index==1:
            f.local['materials']='|'.join(f.decision)
            f.decision=None
            f.step_index=2
            return StepResult.ask(PendingRequest(a.action_id+':target',a.player_id,RequestType.CHOOSE_PLAYER,
                self.label+'：选择杀目标',a.action_id,f.frame_id,
                allowed_player_ids=self.provider.validator.rules.get('basic.slash').target_candidates(state,a.player_id)))
        materials=tuple(str(f.local['materials']).split('|'))
        if f.step_index==2:
            self.validate_start(state,a)
            target=f.decision
            f.decision=None
            self.provider.validator.rules.get('basic.slash').validate_targets(state,a.player_id,(target,))
            from dataclasses import replace
            virtual=replace(VirtualCard.spear(state,materials,effective_suit),skill_id=self.skill_id)
            self.moves.move(state,CardMove(a.action_id+':processing',materials,hand,ZoneRef(ZoneType.PROCESSING),CardMoveReason.USE,a.player_id))
            from .yj2011_tier3 import record_slash_use
            counted=record_slash_use(state, a.player_id, (target,))
            self.moves.recorder.record(CardUsedEvent(a.action_id+':used',a.player_id,materials[0],(target,),'basic.slash',counted,virtual))
            f.step_index=3
            return StepResult.push(SlashSequence(a.action_id+':slash',a.player_id,materials[0],(target,),virtual))
        remaining=tuple(cid for cid in materials if cid in state.cards_in(ZoneRef(ZoneType.PROCESSING)))
        if remaining:
            self.moves.move(state,CardMove(a.action_id+':discard',remaining,ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.USE,a.player_id))
        return StepResult.complete()
