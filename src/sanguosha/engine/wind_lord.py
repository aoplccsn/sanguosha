"""Classic Wind lord skill actions."""

from dataclasses import dataclass

from sanguosha.model.enums import Kingdom, Phase
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .requests import PendingRequest, RequestType


def huangtian_lord(state, skills):
    return next((pid for pid in state.seat_order if state.players[pid].is_alive
                 and skills.has(state, pid, 'huangtian')), None)


@dataclass(frozen=True, slots=True)
class HuangtianAction(Action):
    player_id: str


class HuangtianHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def eligible(self, state, player_id):
        return tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                     if state.cards[cid].definition_id in ('basic.dodge', 'delayed.lightning'))

    def validate_start(self, state, action):
        lord = huangtian_lord(state, self.skills)
        if (lord is None or lord == action.player_id
                or not state.players[action.player_id].is_alive
                or self.skills.faction(state, action.player_id) is not Kingdom.QUN
                or state.current_player_id != action.player_id
                or state.current_phase is not Phase.PLAY
                or state.play_usage is None or state.play_usage.count('skill.huangtian')
                or not self.eligible(state, action.player_id)):
            raise InvalidCardUse('黄天不可用')

    def step(self, state, frame):
        action = frame.action
        self.validate_start(state, action)
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':card', action.player_id,
                RequestType.CHOOSE_CARD, '黄天：选择一张【闪】或【闪电】交给主公',
                action.action_id, frame.frame_id,
                eligible_card_ids=self.eligible(state, action.player_id)))
        card_id = frame.decision
        frame.decision = None
        if card_id not in self.eligible(state, action.player_id):
            raise InvalidCardUse('黄天所选牌已不可用')
        lord = huangtian_lord(state, self.skills)
        self.moves.move(state, CardMove(action.action_id + ':give', (card_id,),
            ZoneRef(ZoneType.HAND, action.player_id), ZoneRef(ZoneType.HAND, lord),
            CardMoveReason.SYSTEM, action.player_id, action.action_id))
        state.play_usage.record('skill.huangtian')
        return StepResult.complete()
