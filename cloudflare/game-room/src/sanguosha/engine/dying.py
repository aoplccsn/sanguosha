"""Explicit peach-request chain for a player at zero or negative HP."""

from dataclasses import dataclass

from sanguosha.content.cards.ids import PEACH_ID
from sanguosha.model.ids import PlayerId
from sanguosha.model.enums import Kingdom
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
        if not target.is_alive:
            return StepResult.complete('dead')
        if frame.step_index == 0:
            if target.hp > 0:
                self.recorder.record(DyingRescuedEvent(f"{action.action_id}:rescued", action.target_id, target.hp))
                return StepResult.complete("rescued")
            if (self.skills is not None and self.skills.has(state, action.target_id, 'powei')
                    and not target.marks.get('powei_success') and not target.marks.get('powei_failed')):
                from .mobile_gods import MobileGodAction
                frame.step_index = 4
                return StepResult.push(MobileGodAction(action.action_id + ':powei-fail', action.target_id, 'powei_fail'))
            if self.skills is not None and not frame.local.get('yj2012_fuli') and self.skills.has(state, action.target_id, 'fuli'):
                from .yj2012 import YJ2012Action
                frame.local['yj2012_fuli'] = True
                frame.step_index = 4
                return StepResult.push(YJ2012Action(action.action_id + ':fuli', action.target_id, 'fuli'))
            if self.skills is not None:
                from .yj2011_tier3 import YJSkillAction
                offered = frame.local.setdefault('yj_buyi_owners', [])
                owner = next((pid for pid in state.seat_order if pid not in offered
                    and state.players[pid].is_alive and self.skills.has(state, pid, 'buyi')), None)
                if owner is not None:
                    offered.append(owner)
                    frame.step_index = 4
                    return StepResult.push(YJSkillAction(action.action_id + ':buyi:' + owner,
                        owner, 'buyi', action.target_id))
            if self.before_rescue is not None and not frame.local.get('before_rescue_checked'):
                frame.local['before_rescue_checked'] = True
                offer = self.before_rescue(state, action.target_id,
                                           action.action_id + ':before-rescue')
                if offer is not None:
                    frame.step_index = 4
                    return StepResult.push(offer)
            if 'rescue_order' not in frame.local:
                order = state.seat_order
                current = state.current_player_id
                if current in order:
                    start = order.index(current)
                    order = order[start:] + order[:start]
                    if state.current_phase is None:
                        order = order[1:] + order[:1]
                frame.local['rescue_order'] = order
            order = tuple(frame.local['rescue_order'])
            if frame.cursor >= len(order):
                frame.step_index = 3
                return StepResult.push(DeathAction(f"{action.action_id}:death", action.target_id, action.source_id))
            candidate = order[frame.cursor]
            frame.cursor += 1
            if not state.players[candidate].is_alive:
                return StepResult.continue_()
            turn_owner = state.current_player_id
            if (self.skills is not None and turn_owner in state.players
                    and state.players[turn_owner].is_alive and state.current_phase is not None
                    and self.skills.has(state, turn_owner, 'wansha')
                    and candidate not in (turn_owner, action.target_id)):
                return StepResult.continue_()
            frame.local['responder'] = candidate
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
            responder = frame.local['responder']
            frame.step_index = 2
            from sanguosha.model.virtual_card import VirtualCard
            if isinstance(frame.child_result,VirtualCard) and frame.child_result.skill_id=='chunlao':
                return StepResult.push(RecoverAction(action.action_id+':chunlao-recover:'+str(frame.cursor)+':'+str(frame.local.get('round',0)),action.target_id,action.target_id,1))
            round_number = int(frame.local.get("round", 0))
            return StepResult.push(RecoverAction(
                f"{action.action_id}:recover:{round_number}:{frame.cursor}", responder, action.target_id,
                2 if self.skills is not None and self.skills.has(state,action.target_id,'jiuyuan')
                and responder != action.target_id and self.skills.faction(state,responder) is Kingdom.WU
                else 1,
            ))
        if frame.step_index == 2:
            frame.cursor -= 1
            frame.local["round"] = int(frame.local.get("round", 0)) + 1
            frame.step_index = 0
            return StepResult.continue_()
        if frame.step_index == 4:
            frame.step_index = 0
            return StepResult.continue_()
        return StepResult.complete("dead")
