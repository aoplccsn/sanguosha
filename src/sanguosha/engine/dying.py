"""Explicit peach-request chain for a player at zero or negative HP."""

from dataclasses import dataclass

from sanguosha.content.cards.ids import PEACH_ID
from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState

from .actions import Action, StepResult
from .death import DeathAction
from .events import DyingRescuedEvent, EventRecorder
from .recovery import RecoverAction
from .resolution import ResolutionFrame
from .response import RespondWithCardAction


@dataclass(frozen=True, slots=True)
class DyingAction(Action):
    target_id: PlayerId
    source_id: PlayerId | None


class DyingActionHandler:
    def __init__(self, recorder: EventRecorder, skills=None, before_rescue=None) -> None:
        self.recorder = recorder
        self.skills = skills
        self.before_rescue = before_rescue

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, DyingAction)
        target = state.players[action.target_id]
        if frame.step_index == 0:
            if target.hp > 0:
                self.recorder.record(DyingRescuedEvent(f"{action.action_id}:rescued", action.target_id, target.hp))
                return StepResult.complete("rescued")
            if self.before_rescue is not None and not frame.local.get('before_rescue_checked'):
                frame.local['before_rescue_checked'] = True
                offer = self.before_rescue(state, action.target_id,
                                           action.action_id + ':before-rescue')
                if offer is not None:
                    frame.step_index = 4
                    return StepResult.push(offer)
            order = state.seat_order
            if frame.cursor >= len(order):
                frame.step_index = 3
                return StepResult.push(DeathAction(f"{action.action_id}:death", action.target_id, action.source_id))
            start = order.index(action.target_id)
            candidate = order[(start + frame.cursor) % len(order)]
            frame.cursor += 1
            if not state.players[candidate].is_alive:
                return StepResult.continue_()
            frame.step_index = 1
            round_number = int(frame.local.get("round", 0))
            return StepResult.push(RespondWithCardAction(
                f"{action.action_id}:ask:{round_number}:{frame.cursor}:{candidate}", candidate,
                PEACH_ID, action.action_id, f"{action.target_id} 濒死：请打出桃救援或放弃",
                action.target_id,
            ))
        if frame.step_index == 1:
            if frame.child_result is None:
                frame.step_index = 0
                return StepResult.continue_()
            responder = state.seat_order[(state.seat_order.index(action.target_id) + frame.cursor - 1) % len(state.seat_order)]
            frame.step_index = 2
            round_number = int(frame.local.get("round", 0))
            return StepResult.push(RecoverAction(
                f"{action.action_id}:recover:{round_number}:{frame.cursor}", responder, action.target_id,
                2 if self.skills is not None and self.skills.has(state,action.target_id,'jiuyuan')
                and responder != action.target_id and self.skills.faction(state,responder) == self.skills.faction(state,action.target_id)
                else 1,
            ))
        if frame.step_index == 2:
            frame.cursor = 0
            frame.local["round"] = int(frame.local.get("round", 0)) + 1
            frame.step_index = 0
            return StepResult.continue_()
        if frame.step_index == 4:
            frame.step_index = 0
            return StepResult.continue_()
        return StepResult.complete("dead")
