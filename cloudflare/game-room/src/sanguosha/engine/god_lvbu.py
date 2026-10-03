"""Authoritative God Lu Bu skill actions for the local T11 review match."""

from dataclasses import dataclass

from sanguosha.model.enums import Phase
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .military_basics import MilitaryDamageAction
from .events import Event
from .requests import PendingRequest, RequestType
from .turnover import TurnoverAction


GOD_LVBU = 'forest_god_lvbu'
RAGE = 'rage'


def grant_rage_on_damage(state, source_id, target_id, amount):
    """狂暴: each damage point grants a mark to Lu Bu as source or recipient."""
    for pid in (source_id, target_id):
        if pid is not None and state.players[pid].character_id == GOD_LVBU and state.players[pid].is_alive:
            state.players[pid].marks[RAGE] = state.players[pid].marks.get(RAGE, 0) + amount


@dataclass(frozen=True, slots=True)
class WuqianAction(Action):
    player_id: str


class WuqianHandler:
    def __init__(self, recorder):
        self.recorder = recorder

    def targets(self, state, actor):
        return tuple(pid for pid in state.seat_order if pid != actor and state.players[pid].is_alive)

    def step(self, state, frame):
        action = frame.action
        actor = action.player_id
        if (state.players[actor].character_id != GOD_LVBU or state.current_player_id != actor
                or state.current_phase is not Phase.PLAY or state.players[actor].marks.get(RAGE, 0) < 2):
            raise InvalidCardUse('无前不可用')
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':target', actor,
                RequestType.CHOOSE_PLAYER, '无前：选择一名其他角色', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, actor)))
        target = frame.decision
        if target not in self.targets(state, actor):
            raise InvalidCardUse('无前目标已失效')
        state.players[actor].marks[RAGE] -= 2
        state.players[actor].marks['wuwei'] = 1
        state.players[target].marks['wuwei_target_' + actor] = 1
        self.recorder.record(Event(action.action_id + ':used', 'skill_wuwei', actor, (target,),
                                   {'level': 2, 'skill_id': 'wuwei'}))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class ShenfenAction(Action):
    player_id: str


class ShenfenHandler:
    def __init__(self, recorder, moves):
        self.recorder, self.moves = recorder, moves

    def step(self, state, frame):
        action = frame.action
        actor = action.player_id
        if frame.step_index == 0:
            if (state.players[actor].character_id != GOD_LVBU or state.current_player_id != actor
                    or state.current_phase is not Phase.PLAY or state.play_usage.count('skill.shenfen')
                    or state.players[actor].marks.get(RAGE, 0) < 6):
                raise InvalidCardUse('神愤不可用')
            state.players[actor].marks[RAGE] -= 6
            state.play_usage.record('skill.shenfen')
            targets = tuple(pid for pid in state.seat_order if pid != actor and state.players[pid].is_alive)
            frame.local['targets'] = '|'.join(map(str, targets))
            self.recorder.record(Event(action.action_id + ':used', 'skill_shenfen', actor, targets,
                                       {'level': 3, 'skill_id': 'shenfen'}))
            frame.step_index = 1
        targets = tuple(frame.local['targets'].split('|')) if frame.local['targets'] else ()
        if frame.step_index == 1:
            if frame.cursor < len(targets) and state.status is not GameStatus.FINISHED:
                target = targets[frame.cursor]
                frame.cursor += 1
                if state.players[target].is_alive:
                    return StepResult.push(MilitaryDamageAction(action.action_id + ':damage:' + str(frame.cursor),
                                                        actor, target, 1))
                return StepResult.continue_()
            frame.cursor = 0
            frame.step_index = 2
        if frame.step_index == 2:
            if frame.cursor >= len(targets) or state.status is GameStatus.FINISHED:
                frame.step_index = 4
            else:
                target = targets[frame.cursor]
                frame.cursor += 1
                if state.players[target].is_alive:
                    equipment = tuple((ref, cid) for ref, zone in state.zones.items()
                                      if ref.player_id == target and ref.zone_type is ZoneType.EQUIPMENT
                                      for cid in tuple(zone.card_ids))
                    for index, (ref, cid) in enumerate(equipment):
                        self.moves.move(state, CardMove(action.action_id + ':equip:' + str(frame.cursor) + ':' + str(index),
                            (cid,), ref, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, target))
                    hand = state.cards_in(ZoneRef(ZoneType.HAND, target))
                    if len(hand) > 4:
                        frame.local['discard_target'] = target
                        frame.step_index = 3
                        return StepResult.ask(PendingRequest(action.action_id + ':discard:' + str(frame.cursor), target,
                            RequestType.CHOOSE_CARDS, '神愤：弃置四张手牌', action.action_id, frame.frame_id,
                            eligible_card_ids=hand, min_count=4, max_count=4))
                    if hand:
                        self.moves.move(state, CardMove(action.action_id + ':hand:' + str(frame.cursor), hand,
                            ZoneRef(ZoneType.HAND, target), ZoneRef(ZoneType.DISCARD_PILE),
                            CardMoveReason.DISCARD, target))
                return StepResult.continue_()
        if frame.step_index == 3:
            target = frame.local['discard_target']
            cards = tuple(frame.decision)
            if len(cards) != 4 or any(cid not in state.cards_in(ZoneRef(ZoneType.HAND, target)) for cid in cards):
                raise InvalidCardUse('神愤弃牌已失效')
            self.moves.move(state, CardMove(action.action_id + ':hand:' + str(frame.cursor), cards,
                ZoneRef(ZoneType.HAND, target), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, target))
            frame.decision = None
            frame.step_index = 2
            return StepResult.continue_()
        if frame.step_index == 4:
            frame.step_index = 5
            if state.players[actor].is_alive and state.status is not GameStatus.FINISHED:
                return StepResult.push(TurnoverAction(action.action_id + ':turnover', actor))
            return StepResult.complete()
        if frame.step_index == 5:
            return StepResult.complete()
        return StepResult.continue_()
