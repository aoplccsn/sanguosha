"""Classic Mountain skills using the shared turn and card movement pipeline."""

from dataclasses import dataclass

from sanguosha.model.enums import Identity, Phase, Suit
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .requests import PendingRequest, RequestType
from .events import CardUsedEvent
from .judgment import JudgmentAction, JudgmentPattern
from .suits import effective_suit
from .hp import GainMaxHpAction, LoseMaxHpAction
from .recovery import RecoverAction
from .turn_order import queue_extra_turn


QIAOBIAN_PHASES = frozenset((Phase.JUDGMENT, Phase.DRAW, Phase.PLAY, Phase.DISCARD))


def field_zone(player_id):
    return ZoneRef(ZoneType.SPECIAL, player_id, special_key='tian')


@dataclass(frozen=True, slots=True)
class TuntianAction(Action):
    player_id: str


class TuntianHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        player_id = action.player_id
        if not self.skills.has(state, player_id, 'tuntian') or not state.players[player_id].is_alive:
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':offer', player_id, RequestType.YES_NO,
                '回合外失去牌，是否发动【屯田】判定？', action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.push(JudgmentAction(
                action.action_id + ':judgment', player_id,
                JudgmentPattern(), return_card_id=True))
        if frame.step_index == 2:
            card_id = frame.child_result
            if (card_id is not None and effective_suit(state, card_id, player_id) is not Suit.HEART
                    and card_id in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))):
                self.moves.move(state, CardMove(
                    action.action_id + ':field', (card_id,), ZoneRef(ZoneType.DISCARD_PILE),
                    field_zone(player_id), CardMoveReason.SYSTEM, player_id, action.action_id))
            return StepResult.complete()
        raise InvalidCardUse('屯田状态无效')


@dataclass(frozen=True, slots=True)
class ZaoxianAction(Action):
    player_id: str


class ZaoxianHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        player = state.players[frame.action.player_id]
        if frame.step_index == 0:
            if (not player.is_alive or not self.skills.has(state, player.player_id, 'zaoxian')
                    or player.marks.get('awakened_zaoxian')
                    or len(state.cards_in(field_zone(player.player_id))) < 3):
                return StepResult.complete(False)
            player.marks['awakened_zaoxian'] = 1
            frame.step_index = 1
            return StepResult.push(LoseMaxHpAction(frame.action.action_id + ':max-hp', player.player_id, 1))
        if player.is_alive:
            player.granted_skills['jixi'] = 'zaoxian'
        return StepResult.complete(player.is_alive)


@dataclass(frozen=True, slots=True)
class JixiUse(Action):
    player_id: str
    material_id: str


class JixiHandler:
    def __init__(self, skills, moves, events, snatch_rule):
        self.skills = skills
        self.moves = moves
        self.events = events
        self.snatch_rule = snatch_rule

    def targets(self, state, player_id):
        return self.snatch_rule.target_candidates(state, player_id)

    def available(self, state, player_id, material_id=None):
        field = state.cards_in(field_zone(player_id))
        return (self.skills.has(state, player_id, 'jixi')
                and state.players[player_id].is_alive
                and state.current_player_id == player_id
                and state.current_phase is Phase.PLAY
                and state.play_usage is not None
                and (material_id is None and bool(field) or material_id in field)
                and bool(self.targets(state, player_id)))

    def step(self, state, frame):
        from .military_tricks import TrickAction
        action = frame.action
        if frame.step_index == 0:
            if not self.available(state, action.player_id, action.material_id):
                raise InvalidCardUse('急袭当前不可用')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':target', action.player_id, RequestType.CHOOSE_PLAYER,
                '急袭：选择【顺手牵羊】目标', action.action_id, frame.frame_id,
                allowed_player_ids=self.targets(state, action.player_id)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            if (not self.available(state, action.player_id, action.material_id)
                    or target not in self.targets(state, action.player_id)):
                raise InvalidCardUse('急袭目标不合法')
            self.moves.move(state, CardMove(
                action.action_id + ':processing', (action.material_id,),
                field_zone(action.player_id), ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.USE, action.player_id, action.action_id))
            self.events.record(CardUsedEvent(action.action_id + ':used', action.player_id,
                                             action.material_id, (target,), 'trick.snatch'))
            frame.step_index = 2
            return StepResult.push(TrickAction(
                action.action_id + ':snatch', action.player_id, action.material_id,
                'trick.snatch', (target,)))
        if action.material_id in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
            self.moves.move(state, CardMove(
                action.action_id + ':discard', (action.material_id,),
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.USE, action.player_id, action.action_id))
        return StepResult.complete(frame.child_result)


@dataclass(frozen=True, slots=True)
class FangquanSkipAction(Action):
    player_id: str


class FangquanSkipHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        player_id = frame.action.player_id
        if (not self.skills.has(state, player_id, 'fangquan')
                or not state.players[player_id].is_alive):
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':offer', player_id, RequestType.YES_NO,
                '是否发动【放权】跳过出牌阶段？', frame.action.action_id, frame.frame_id))
        if frame.decision is True:
            state.players[player_id].marks['skip_play'] = 1
            state.players[player_id].marks['fangquan_pending'] = 1
        frame.decision = None
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class FangquanEndAction(Action):
    player_id: str


class FangquanEndHandler:
    def __init__(self, moves):
        self.moves = moves

    def targets(self, state, player_id):
        return tuple(pid for pid in state.seat_order
                     if pid != player_id and state.players[pid].is_alive)

    def step(self, state, frame):
        player_id = frame.action.player_id
        hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
        if frame.step_index == 0:
            if not hand or not self.targets(state, player_id):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':offer', player_id, RequestType.YES_NO,
                '放权：是否弃置一张手牌令其他角色进行额外回合？',
                frame.action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not hand:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':cost', player_id, RequestType.CHOOSE_CARD,
                '放权：弃置一张手牌', frame.action.action_id, frame.frame_id,
                eligible_card_ids=hand))
        if frame.step_index == 2:
            cost = frame.decision
            frame.decision = None
            if cost not in hand:
                raise InvalidCardUse('放权代价不是当前手牌')
            frame.local['cost'] = cost
            frame.step_index = 3
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':target', player_id, RequestType.CHOOSE_PLAYER,
                '放权：选择获得额外回合的角色', frame.action.action_id, frame.frame_id,
                allowed_player_ids=self.targets(state, player_id)))
        target = frame.decision
        frame.decision = None
        if target not in self.targets(state, player_id):
            raise InvalidCardUse('放权目标已不可用')
        cost = frame.local['cost']
        if cost not in hand:
            raise InvalidCardUse('放权手牌代价已不可用')
        self.moves.move(state, CardMove(
            frame.action.action_id + ':cost', (cost,), ZoneRef(ZoneType.HAND, player_id),
            ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
            player_id, frame.action.action_id))
        queue_extra_turn(state, target)
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class RuoyuAction(Action):
    player_id: str


class RuoyuHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        player_id = frame.action.player_id
        player = state.players[player_id]
        if frame.step_index == 0:
            if (not player.is_alive or player.identity is not Identity.LORD
                    or not self.skills.has(state, player_id, 'ruoyu')
                    or player.marks.get('awakened_ruoyu')
                    or any(other.is_alive and other.hp < player.hp
                           for other in state.players.values())):
                return StepResult.complete(False)
            player.marks['awakened_ruoyu'] = 1
            frame.step_index = 1
            return StepResult.push(GainMaxHpAction(
                frame.action.action_id + ':max-hp', player_id, 1))
        if frame.step_index == 1:
            frame.step_index = 2
            return StepResult.push(RecoverAction(
                frame.action.action_id + ':recover', player_id, player_id, 1))
        player.granted_skills['jijiang'] = 'ruoyu'
        return StepResult.complete(True)


@dataclass(frozen=True, slots=True)
class QiaobianAction(Action):
    player_id: str
    phase: Phase


class QiaobianHandler:
    """Pay the hand-card cost before recording a phase skip."""

    def __init__(self, skills, moves, rng, definitions):
        self.skills = skills
        self.moves = moves
        self.rng = rng
        self.definitions = definitions

    def _draw_targets(self, state, player_id, chosen):
        return tuple(pid for pid in state.seat_order
                     if pid != player_id and pid not in chosen
                     and state.players[pid].is_alive
                     and state.cards_in(ZoneRef(ZoneType.HAND, pid)))

    def _board_cards(self, state):
        return tuple((ref, cid) for ref, zone in state.zones.items()
                     if ref.zone_type in (ZoneType.EQUIPMENT, ZoneType.JUDGMENT)
                     and state.players[ref.player_id].is_alive
                     for cid in zone.card_ids
                     if self._destinations(state, ref, cid))

    def _destinations(self, state, source, card_id):
        from .military_tricks import delayed_definition
        result = []
        for pid in state.seat_order:
            if pid == source.player_id or not state.players[pid].is_alive:
                continue
            if source.zone_type is ZoneType.EQUIPMENT:
                slot = self.definitions.get(state.cards[card_id].definition_id).equipment_slot
                if slot is None:
                    continue
                destination = ZoneRef(ZoneType.EQUIPMENT, pid, slot)
                if state.cards_in(destination):
                    continue
            else:
                definition = delayed_definition(state, card_id)
                destination = ZoneRef(ZoneType.JUDGMENT, pid)
                if any(delayed_definition(state, other) == definition
                       for other in state.cards_in(destination)):
                    continue
            result.append(pid)
        return tuple(result)

    def step(self, state, frame):
        action = frame.action
        player_id = action.player_id
        if (action.phase not in QIAOBIAN_PHASES
                or not self.skills.has(state, player_id, 'qiaobian')
                or not state.players[player_id].is_alive):
            return StepResult.complete()
        hand = tuple(state.cards_in(ZoneRef(ZoneType.HAND, player_id)))
        if frame.step_index == 0:
            if not hand:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':offer', player_id, RequestType.YES_NO,
                '是否弃置一张手牌发动【巧变】，跳过' + action.phase.value + '阶段？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not hand:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                action.action_id + ':cost', player_id, RequestType.CHOOSE_CARD,
                '巧变：弃置一张手牌', action.action_id, frame.frame_id,
                eligible_card_ids=hand))
        if frame.step_index == 2:
            cost = frame.decision
            frame.decision = None
            if cost not in hand:
                raise InvalidCardUse('巧变代价必须是当前手牌')
            self.moves.move(state, CardMove(
                action.action_id + ':cost', (cost,), ZoneRef(ZoneType.HAND, player_id),
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, player_id))
            state.players[player_id].marks['skip_' + action.phase.value] = 1
            if action.phase is Phase.DRAW:
                frame.local['chosen'] = ()
                frame.step_index = 3
                return StepResult.continue_()
            if action.phase is Phase.PLAY:
                frame.step_index = 5
                return StepResult.continue_()
            return StepResult.complete()
        if frame.step_index == 3:
            chosen = frame.local['chosen']
            targets = self._draw_targets(state, player_id, chosen)
            if len(chosen) >= 2 or not targets:
                return StepResult.complete()
            frame.step_index = 4
            return StepResult.ask(PendingRequest(
                action.action_id + f':draw-target:{len(chosen)}', player_id,
                RequestType.CHOOSE_OPTION,
                '巧变：选择一名角色获得其一张手牌，或结束',
                action.action_id, frame.frame_id, choices=(*targets, 'done')))
        if frame.step_index == 4:
            target = frame.decision
            frame.decision = None
            chosen = frame.local['chosen']
            if target == 'done':
                return StepResult.complete()
            if target not in self._draw_targets(state, player_id, chosen):
                raise InvalidCardUse('巧变摸牌替代目标不合法')
            source = ZoneRef(ZoneType.HAND, target)
            card_id = self.rng.choice(state.cards_in(source))
            self.moves.move(state, CardMove(
                action.action_id + f':take:{len(chosen)}', (card_id,), source,
                ZoneRef(ZoneType.HAND, player_id), CardMoveReason.SYSTEM,
                player_id, action.action_id))
            frame.local['chosen'] = (*chosen, target)
            frame.step_index = 3
            return StepResult.continue_()
        if frame.step_index == 5:
            cards = self._board_cards(state)
            if not cards:
                return StepResult.complete()
            frame.step_index = 6
            return StepResult.ask(PendingRequest(
                action.action_id + ':board-card', player_id, RequestType.CHOOSE_CARD,
                '巧变：选择要移动的场上牌', action.action_id, frame.frame_id,
                eligible_card_ids=tuple(cid for _, cid in cards)))
        if frame.step_index == 6:
            card_id = frame.decision
            frame.decision = None
            sources = [(ref, cid) for ref, cid in self._board_cards(state) if cid == card_id]
            if len(sources) != 1:
                raise InvalidCardUse('巧变场上牌不可移动')
            source, _ = sources[0]
            frame.local['board_card'] = card_id
            frame.local['board_source'] = source
            frame.step_index = 7
            return StepResult.ask(PendingRequest(
                action.action_id + ':destination', player_id, RequestType.CHOOSE_PLAYER,
                '巧变：选择目标角色', action.action_id, frame.frame_id,
                allowed_player_ids=self._destinations(state, source, card_id)))
        if frame.step_index == 7:
            destination_id = frame.decision
            frame.decision = None
            source = frame.local['board_source']
            card_id = frame.local['board_card']
            if (card_id not in state.cards_in(source)
                    or destination_id not in self._destinations(state, source, card_id)):
                raise InvalidCardUse('巧变目标区域不合法')
            destination = (ZoneRef(ZoneType.EQUIPMENT, destination_id, source.equipment_slot)
                           if source.zone_type is ZoneType.EQUIPMENT
                           else ZoneRef(ZoneType.JUDGMENT, destination_id))
            self.moves.move(state, CardMove(
                action.action_id + ':board-move', (card_id,), source, destination,
                CardMoveReason.SYSTEM, player_id, action.action_id))
            return StepResult.complete()
        raise InvalidCardUse('巧变状态无效')
