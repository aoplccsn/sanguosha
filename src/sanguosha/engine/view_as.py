"""Spear activation uses two hand costs and the normal shared Slash counter."""
from dataclasses import dataclass
from .actions import Action,StepResult
from .card_use import LegalPlayActionProvider
from .card_rules import InvalidCardUse
from .card_moves import CardMove,CardMoveReason
from .requests import PendingRequest,RequestType
from .military_basics import equipped,SlashSequence
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.enums import EquipmentSlot,Phase
from sanguosha.model.zones import ZoneRef,ZoneType

@dataclass(frozen=True,slots=True)
class UseSpear(Action):
    player_id: str

class MilitaryPlayOptions(LegalPlayActionProvider):
    def spear_legal(self,state,pid):
        return equipped(state,pid,EquipmentSlot.WEAPON)=='equipment.weapon.serpent_spear' and len(state.cards_in(ZoneRef(ZoneType.HAND,pid)))>=2 and state.play_usage.count('basic.slash')<1 and bool(self.validator.rules.get('basic.slash').target_candidates(state,pid))
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
            f.step_index=1
            return StepResult.ask(PendingRequest(a.action_id+':cost',a.player_id,RequestType.CHOOSE_CARDS,
                '丈八蛇矛：选择两张手牌',a.action_id,f.frame_id,eligible_card_ids=state.cards_in(hand),min_count=2,max_count=2))
        if f.step_index==1:
            f.local['materials']='|'.join(f.decision)
            f.decision=None
            f.step_index=2
            return StepResult.ask(PendingRequest(a.action_id+':target',a.player_id,RequestType.CHOOSE_PLAYER,
                '丈八蛇矛：选择杀目标',a.action_id,f.frame_id,
                allowed_player_ids=self.provider.validator.rules.get('basic.slash').target_candidates(state,a.player_id)))
        materials=tuple(str(f.local['materials']).split('|'))
        if f.step_index==2:
            self.validate_start(state,a)
            target=f.decision
            f.decision=None
            self.provider.validator.rules.get('basic.slash').validate_targets(state,a.player_id,(target,))
            virtual=VirtualCard.spear(state,materials)
            self.moves.move(state,CardMove(a.action_id+':processing',materials,hand,ZoneRef(ZoneType.PROCESSING),CardMoveReason.USE,a.player_id))
            state.play_usage.record('basic.slash')
            f.step_index=3
            return StepResult.push(SlashSequence(a.action_id+':slash',a.player_id,materials[0],(target,),virtual))
        remaining=tuple(cid for cid in materials if cid in state.cards_in(ZoneRef(ZoneType.PROCESSING)))
        if remaining:
            self.moves.move(state,CardMove(a.action_id+':discard',remaining,ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.USE,a.player_id))
        return StepResult.complete()
