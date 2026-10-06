"""Basic card effects are explicit child actions, never nested Python calls."""

from dataclasses import dataclass

from sanguosha.model.enums import DamageNature
from sanguosha.model.ids import CardDefinitionId, CardInstanceId, PlayerId
from sanguosha.model.state import GameState

from .actions import Action, StepResult
from .damage import DamageAction
from .recovery import RecoverAction
from .resolution import ResolutionFrame


@dataclass(frozen=True, slots=True)
class SlashEffectAction(Action):
    source_id: PlayerId
    target_id: PlayerId
    card_id: CardInstanceId
    dodge_definition_id: CardDefinitionId


class SlashEffectHandler:
    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, SlashEffectAction)
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.push(RespondWithCardAction(
                f"{action.action_id}:response", action.target_id,
                action.dodge_definition_id, action.action_id,
                f"{action.source_id} 对你使用【杀】，请打出【闪】或不出",
                action.target_id,
            ))
        if frame.step_index == 1:
            if frame.child_result is not None:
                return StepResult.complete("avoided")
            frame.step_index = 2
            return StepResult.push(DamageAction(
                f"{action.action_id}:damage", action.source_id, action.target_id,
                1, DamageNature.NORMAL, action.card_id, action.action_id,
            ))
        return StepResult.complete("hit")


@dataclass(frozen=True, slots=True)
class PeachEffectAction(Action):
    user_id: PlayerId
    card_id: CardInstanceId


class PeachEffectHandler:
    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, PeachEffectAction)
        if frame.step_index == 0:
            from .qiaoshui import take_targets
            frame.local['targets']=take_targets(state,action.action_id,(action.user_id,))
            frame.step_index=1
        targets=frame.local['targets']
        if frame.cursor>=len(targets):return StepResult.complete(frame.child_result)
        target=targets[frame.cursor];frame.cursor+=1
        return StepResult.push(RecoverAction(f"{action.action_id}:recover:{frame.cursor}",action.user_id,target,1,action.card_id))


from .response import RespondWithCardAction  # noqa: E402
