"""A turn schedules phase child actions on the existing resolution stack."""

from dataclasses import dataclass

from sanguosha.model.enums import Phase
from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState, GameStatus

from .actions import Action, StepResult
from .events import EventRecorder, PhaseSkippedEvent, TurnEndedEvent, TurnStartedEvent
from .phases import PhaseAction
from .resolution import ResolutionFrame
from .turn_order import InvalidTurn
from .requests import PendingRequest, RequestType


STANDARD_PHASE_ORDER: tuple[Phase, ...] = (
    Phase.PREPARATION, Phase.JUDGMENT, Phase.DRAW,
    Phase.PLAY, Phase.DISCARD, Phase.FINISH,
)


@dataclass(frozen=True, slots=True)
class TurnAction(Action):
    player_id: PlayerId
    phases: tuple[Phase, ...] = STANDARD_PHASE_ORDER
    skipped_phases: frozenset[Phase] = frozenset()


class TurnActionHandler:
    def __init__(self, recorder: EventRecorder, before_phase=None, skills=None) -> None:
        self.recorder = recorder
        self.before_phase = before_phase
        self.skills = skills

    def validate_start(self, state: GameState, action: Action) -> None:
        assert isinstance(action, TurnAction)
        if action.player_id not in state.players or not state.players[action.player_id].is_alive:
            raise InvalidTurn(f"player {action.player_id!r} cannot start a turn")
        if any(phase not in STANDARD_PHASE_ORDER for phase in action.phases):
            raise InvalidTurn("turn schedule contains an unsupported phase")
        if len(action.phases) != len(set(action.phases)):
            raise InvalidTurn("turn schedule repeats a phase")
        if not action.phases:
            raise InvalidTurn("turn schedule is empty")

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, TurnAction)
        if frame.step_index == 9:
            wanted = frame.decision is True
            frame.decision = None
            if wanted and state.players[frame.local['lianpo_actor']].is_alive:
                from .turn_order import queue_extra_turn
                queue_extra_turn(state, frame.local['lianpo_actor'])
            frame.step_index = 1
            return StepResult.continue_()
        if frame.step_index == 0:
            if not state.metadata.get('mobile_game_started') and self.skills is not None:
                from .mobile_gods import MobileGodAction
                if 'mobile_faction_owners' not in frame.local:
                    frame.local['mobile_faction_owners'] = tuple(q for q in state.seat_order if state.players[q].character_id.startswith('mobile_god_') or state.players[q].character_id == 'mountain_god_simayi')
                    frame.local['mobile_faction_cursor'] = 0
                faction_owners = frame.local['mobile_faction_owners']; faction_index = frame.local['mobile_faction_cursor']
                if faction_index < len(faction_owners):
                    frame.local['mobile_faction_cursor'] = faction_index + 1
                    return StepResult.push(MobileGodAction(action.action_id + ':faction:' + faction_owners[faction_index],faction_owners[faction_index],'faction'))
                if 'mobile_start_owners' not in frame.local:
                    frame.local['mobile_start_owners'] = tuple(q for q in state.seat_order if self.skills.has(state,q,'tamo'))
                    frame.local['mobile_start_cursor'] = 0
                owners = frame.local['mobile_start_owners']; index = frame.local['mobile_start_cursor']
                if index < len(owners):
                    frame.local['mobile_start_cursor'] = index + 1
                    return StepResult.push(MobileGodAction(action.action_id + ':tamo:' + owners[index], owners[index], 'tamo'))
                for owner in state.seat_order:
                    if self.skills.has(state, owner, 'powei'):
                        for q in state.seat_order:
                            if q != owner:
                                state.players[q].marks['wei:' + owner] = 1
                state.metadata['mobile_game_started'] = True
            state.current_player_id = action.player_id
            state.current_phase = None
            state.turn_number += 1
            from .mobile_gods import start_normal_round
            start_normal_round(state, action.player_id)
            self.recorder.record(TurnStartedEvent(f"{action.action_id}:start", action.player_id, state.turn_number))
            from .remaining_gods import camp_start
            camp_start(state,action.player_id,self.skills)
            if not state.players[action.player_id].face_up:
                state.players[action.player_id].face_up = True
                frame.cursor = len(action.phases)
            frame.step_index = 1
            return StepResult.continue_()
        if (frame.step_index == 1 and frame.cursor == 0 and self.skills is not None
                and not frame.local.get('mobile_dinghan') and self.skills.has(state,action.player_id,'dinghan')):
            from .mobile_gods import MobileGodAction
            frame.local['mobile_dinghan'] = True
            return StepResult.push(MobileGodAction(action.action_id + ':dinghan',action.player_id,'dinghan'))
        if frame.step_index == 1 and frame.cursor == 0 and self.skills is not None:
            from .mobile_gods import MobileGodAction
            owners = tuple(q for q in state.seat_order if state.players[q].is_alive and self.skills.has(state,q,'powei'))
            index = frame.local.get('mobile_powei_cursor', 0)
            if index < len(owners):
                frame.local['mobile_powei_cursor'] = index + 1
                return StepResult.push(MobileGodAction(action.action_id + ':powei:' + owners[index], owners[index], 'powei_start', action.player_id))
        if frame.step_index==1 and frame.cursor==0 and self.skills is not None:
            from .yj2011_tier3 import hand
            from .yj2013 import YJ2013Action
            if 'zhuikong_owners' not in frame.local:
                start=state.seat_order.index(action.player_id);order=state.seat_order[start:]+state.seat_order[:start]
                frame.local['zhuikong_owners']=tuple(q for q in order if q!=action.player_id and state.players[q].is_alive and self.skills.has(state,q,'zhuikong'))
                frame.local['zhuikong_cursor']=0
            owners=frame.local['zhuikong_owners'];index=frame.local['zhuikong_cursor']
            if index<len(owners):
                frame.local['zhuikong_cursor']=index+1;owner=owners[index]
                if state.players[owner].is_alive and state.players[owner].hp<state.players[owner].max_hp and hand(state,owner) and hand(state,action.player_id):
                    return StepResult.push(YJ2013Action(action.action_id+':zhuikong:'+owner,owner,'zhuikong',action.player_id))
                return StepResult.continue_()
        if (frame.step_index == 1 and frame.cursor == 0 and not frame.local.get('yj2012_dangxian')
                and self.skills is not None and self.skills.has(state, action.player_id, 'dangxian')):
            frame.local['yj2012_dangxian'] = True
            return StepResult.push(PhaseAction(action.action_id + ':dangxian', action.player_id, Phase.PLAY))
        # A player who dies during a phase must not continue the rest of the turn.
        if (frame.cursor == len(action.phases) or state.status is GameStatus.FINISHED
                or not state.players[action.player_id].is_alive):
            if (state.players[action.player_id].marks.pop('fangquan_pending', 0)
                    and state.status is not GameStatus.FINISHED
                    and state.players[action.player_id].is_alive
                    and self.skills is not None and self.skills.has(state, action.player_id, 'fangquan')):
                from .mountain import FangquanEndAction
                return StepResult.push(FangquanEndAction(action.action_id + ':fangquan-end', action.player_id))
            if self.skills is not None and state.status is not GameStatus.FINISHED:
                eligible = next((pid for pid in state.seat_order
                    if state.players[pid].is_alive
                    and state.players[pid].marks.pop('lianpo_pending', 0)
                    and self.skills.has(state, pid, 'lianpo')), None)
                if eligible is not None:
                    from .turn_order import queue_extra_turn
                    queue_extra_turn(state, eligible)
                    return StepResult.continue_()
            if not frame.local.get('camp_return_checked'):
                from .remaining_gods import camp_source,clear_camp,RemainingGodAction
                frame.local['camp_return_checked']=True
                owner=camp_source(state,action.player_id,self.skills)
                if owner is not None and owner!=action.player_id:
                    return StepResult.push(RemainingGodAction(action.action_id+':camp-return',owner,'campend',action.player_id))
            if (not frame.local.get('mobile_zhimeng_end') and state.status is not GameStatus.FINISHED
                    and state.players[action.player_id].is_alive and self.skills is not None
                    and self.skills.has(state, action.player_id, 'zhimeng')):
                from .mobile_gods import MobileGodAction
                frame.local['mobile_zhimeng_end'] = True
                return StepResult.push(MobileGodAction(action.action_id + ':zhimeng', action.player_id, 'zhimeng'))
            if state.ruleset_id == 'classic-military':
                state.players[action.player_id].marks.pop('wine', None)
                state.players[action.player_id].marks.pop('jilue_wansha', None)
                for key in ('slash_quota_bonus', 'slash_ignore_distance',
                            'slash_extra_targets', 'slash_prohibited',
                            'shuangxiong_color', 'yj_zishou', 'yj_gongqi', 'poxi_hand_limit', 'poxi_end_play'):
                    state.players[action.player_id].marks.pop(key, None)
                if state.players[action.player_id].character_id == 'forest_god_lvbu':
                    state.players[action.player_id].marks.pop('wuwei', None)
                    for other in state.players.values():
                        other.marks.pop('wuwei_target_' + action.player_id, None)
            wine_targets=state.metadata.get('qiaoshui_wine_targets',{})
            for pid,effect in tuple(wine_targets.items()):
                if effect['source']==action.player_id:
                    state.players[pid].marks.pop('wine',None);del wine_targets[pid]
            from .card_limits import clear_source
            clear_source(state, action.player_id)
            from .fuhun import clear_grants
            clear_grants(state,action.player_id)
            from .yj2011_tier3 import clear_turn
            clear_turn(state)
            from .fuhuanghou import clear_turn as clear_zhuikong
            clear_zhuikong(state,action.player_id)
            from .skill_leases import expire_target
            expire_target(state,action.player_id)
            state.current_phase = None
            self.recorder.record(TurnEndedEvent(f"{action.action_id}:end", action.player_id, state.turn_number))
            return StepResult.complete()
        phase = action.phases[frame.cursor]
        already_skipped = phase in action.skipped_phases or state.players[action.player_id].marks.get('skip_' + phase.value, 0)
        if not already_skipped and self.before_phase is not None and frame.local.get('before_phase_cursor') != frame.cursor:
            frame.local['before_phase_cursor'] = frame.cursor
            offer = self.before_phase(state, action.player_id, phase,
                                      f'{action.action_id}:before:{frame.cursor}')
            if offer is not None:
                return StepResult.push(offer)
        frame.cursor += 1
        marked_skip = state.players[action.player_id].marks.pop('skip_' + phase.value, 0)
        if phase in action.skipped_phases or marked_skip:
            self.recorder.record(PhaseSkippedEvent(f"{action.action_id}:{frame.cursor}:skipped", action.player_id, phase))
            return StepResult.continue_()
        return StepResult.push(PhaseAction(f"{action.action_id}:phase:{frame.cursor}:{phase.value}", action.player_id, phase))
