"""Classic Forest skills using the shared resolution stack and card services."""
from dataclasses import dataclass

from sanguosha.model.enums import CardCategory, Color, Identity, Kingdom, Phase, Suit
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .deck import DrawCardsAction, RevealTopCardsAction
from .distance import DistanceSystem
from .forced_cards import ForcedDiscardAction, SwapHandsAction, discardable_cards
from .hp import LoseHpAction, LoseMaxHpAction
from .judgment import JudgmentAction, JudgmentPattern
from .events import CardResolvedEvent, CardUsedEvent
from .pindian import PindianAction
from .recovery import RecoverAction
from .requests import PendingRequest, RequestType
from .suits import effective_color, effective_suit
from .turnover import TurnoverAction


def owned_cards(state, player_id):
    """Hand and equipment eligible for classic Xingshang, in zone order."""
    refs = sorted((ref for ref in state.zones if ref.player_id == player_id
                   and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)),
                  key=lambda ref: (ref.zone_type.value,
                                   ref.equipment_slot.value if ref.equipment_slot else ''))
    return tuple((ref, state.cards_in(ref)) for ref in refs if state.cards_in(ref))


def savage_effect_immune(state, target_id, skills):
    """Shared target-effect immunity for the two Forest Savage Assault skills."""
    return (skills is not None and state.players[target_id].is_alive
            and (skills.has(state, target_id, 'huoshou')
                 or skills.has(state, target_id, 'juxiang')))



def collect_juxiang(state, moves, skills, user_id, card_id, definition_id,
                    action_id, *, virtual_skill=None):
    """Classic Juxiang intercepts a physical Savage or Guhuo's single material.

    Other virtual Savage cards (including single-material Qice) are excluded.
    Never reclaim a material already obtained during the effect.
    """
    if (skills is None or definition_id != 'trick.savage_assault'
            or virtual_skill not in (None, 'guhuo')
            or card_id not in state.cards_in(ZoneRef(ZoneType.PROCESSING))):
        return False
    owner = next((pid for pid in state.seat_order if pid != user_id
                  and state.players[pid].is_alive
                  and skills.has(state, pid, 'juxiang')), None)
    if owner is None:
        return False
    moves.move(state, CardMove(action_id + ':juxiang', (card_id,),
        ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.HAND, owner),
        CardMoveReason.SYSTEM, owner, action_id))
    return True


def savage_damage_source(state, user_id, skills):
    if skills is None:
        return user_id
    return next((pid for pid in state.seat_order if pid != user_id
                 and state.players[pid].is_alive
                 and skills.has(state, pid, 'huoshou')), user_id)


def weimu_blocks(state, target_id, card_id, definition_id, user_id, skills, virtual_card=None):
    return (skills is not None and state.players[target_id].is_alive
            and skills.has(state, target_id, 'weimu')
            and definition_id.startswith(('trick.', 'delayed.'))
            and not (virtual_card is not None and virtual_card.skill_id == 'guhuo')
            and (virtual_card.color if virtual_card is not None else effective_color(state, card_id, user_id)) is Color.BLACK)


@dataclass(frozen=True, slots=True)
class ZaiqiAction(Action):
    player_id: str


class ZaiqiHandler:
    def __init__(self, skills, moves):
        self.skills, self.moves = skills, moves

    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        if frame.step_index == 0:
            if (not state.players[owner].is_alive
                    or not self.skills.has(state, owner, 'zaiqi')):
                return StepResult.complete()
            missing = max(0, state.players[owner].max_hp - state.players[owner].hp)
            if not missing:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.push(RevealTopCardsAction(action.action_id + ':reveal',
                                                        owner, missing))
        if frame.step_index == 1:
            hearts = 0
            for index, card_id in enumerate(frame.child_result or ()):
                heart = effective_suit(state, card_id, owner) is Suit.HEART
                destination = (ZoneRef(ZoneType.DISCARD_PILE) if heart
                               else ZoneRef(ZoneType.HAND, owner))
                self.moves.move(state, CardMove(f'{action.action_id}:collect:{index}',
                    (card_id,), ZoneRef(ZoneType.PROCESSING), destination,
                    CardMoveReason.SYSTEM, owner, action.action_id))
                hearts += int(heart)
            frame.local['hearts'] = hearts
            frame.step_index = 2
        if frame.cursor < frame.local['hearts']:
            index = frame.cursor
            frame.cursor += 1
            return StepResult.push(RecoverAction(f'{action.action_id}:recover:{index}',
                                                 owner, owner, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class XingshangAction(Action):
    victim_id: str


class XingshangHandler:
    def __init__(self, skills, moves):
        self.skills, self.moves = skills, moves

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            frame.local['owners'] = tuple(pid for pid in state.seat_order
                if pid != action.victim_id and state.players[pid].is_alive
                and self.skills.has(state, pid, 'xingshang'))
            frame.step_index = 1
        if frame.step_index == 1:
            owners = frame.local['owners']
            while frame.cursor < len(owners):
                owner = owners[frame.cursor]
                if state.players[owner].is_alive and owned_cards(state, action.victim_id):
                    frame.local['owner'] = owner
                    frame.step_index = 2
                    return StepResult.ask(PendingRequest(
                        f'{action.action_id}:offer:{frame.cursor}', owner, RequestType.YES_NO,
                        '是否发动【行殇】获得死者的所有牌？', action.action_id,
                        frame.frame_id, subject_player_id=action.victim_id))
                frame.cursor += 1
            return StepResult.complete()
        owner = frame.local['owner']
        wanted = frame.decision is True
        frame.decision = None
        if wanted and state.players[owner].is_alive:
            cards = tuple(cid for _, ids in owned_cards(state, action.victim_id) for cid in ids)
            if cards:
                self.moves.obtain_cards(state, cards, owner, owner,
                    f'{action.action_id}:gain:{frame.cursor}')
        frame.cursor += 1
        frame.step_index = 1
        return StepResult.continue_()


@dataclass(frozen=True, slots=True)
class FangzhuAction(Action):
    player_id: str


class FangzhuHandler:
    def __init__(self, skills):
        self.skills = skills

    def targets(self, state, player_id):
        return tuple(pid for pid in state.seat_order if pid != player_id
                     and state.players[pid].is_alive)

    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        if not state.players[owner].is_alive:
            return StepResult.complete()
        if frame.step_index == 0:
            if not self.targets(state, owner):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', owner,
                RequestType.YES_NO, '是否发动【放逐】？', action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not self.targets(state, owner):
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':target', owner,
                RequestType.CHOOSE_PLAYER, '放逐：选择另一名角色', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, owner)))
        if frame.step_index == 2:
            target = frame.decision
            frame.decision = None
            if target not in self.targets(state, owner):
                raise InvalidCardUse('放逐目标已不可用')
            frame.local['target'] = target
            from .skill_grants import grant_sources
            if 'jilue.permanent' in grant_sources(state, owner, 'fangzhu'):
                frame.step_index = 5
                return StepResult.push(TurnoverAction(action.action_id + ':turnover', target))
            missing = max(0, state.players[owner].max_hp - state.players[owner].hp)
            frame.step_index = 3
            if missing:
                return StepResult.push(DrawCardsAction(action.action_id + ':draw', target, missing))
        if frame.step_index == 5:
            target = frame.local['target']
            missing = max(0, state.players[owner].max_hp - state.players[owner].hp)
            frame.step_index = 4
            if missing and state.players[target].is_alive:
                return StepResult.push(DrawCardsAction(action.action_id + ':draw', target, missing))
            return StepResult.complete()
        if frame.step_index == 3:
            target = frame.local['target']
            if not state.players[target].is_alive:
                return StepResult.complete()
            frame.step_index = 4
            return StepResult.push(TurnoverAction(action.action_id + ':turnover', target))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class SongweiAction(Action):
    judge_id: str
    lord_id: str


class SongweiHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        action = frame.action
        if (not state.players[action.judge_id].is_alive
                or not state.players[action.lord_id].is_alive
                or not self.skills.has(state, action.lord_id, 'songwei')):
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer',
                action.judge_id, RequestType.YES_NO,
                '是否发动【颂威】令主公摸一张牌？', action.action_id,
                frame.frame_id, subject_player_id=action.lord_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if wanted:
                frame.step_index = 2
                return StepResult.push(DrawCardsAction(action.action_id + ':draw',
                                                       action.lord_id, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class DuanliangUse(Action):
    player_id: str
    material_id: str


class DuanliangHandler:
    def __init__(self, skills, moves, events, definitions, trick_rule):
        self.skills, self.moves, self.events = skills, moves, events
        self.definitions, self.trick_rule = definitions, trick_rule

    def materials(self, state, player_id):
        return tuple(cid for ref, zone in state.zones.items()
            if ref.player_id == player_id and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
            for cid in zone.card_ids
            if effective_color(state, cid, player_id) is Color.BLACK
            and self.definitions.get(state.cards[cid].definition_id).category
            in (CardCategory.BASIC, CardCategory.EQUIPMENT))

    def targets(self, state, player_id, material_id):
        return tuple(pid for pid in self.trick_rule.target_candidates(state, player_id)
                     if not weimu_blocks(state, pid, material_id,
                         'delayed.supply_shortage', player_id, self.skills))

    def available(self, state, player_id, material_id=None):
        return (self.skills.has(state, player_id, 'duanliang')
            and state.players[player_id].is_alive
            and state.current_player_id == player_id and state.current_phase is Phase.PLAY
            and state.play_usage is not None and state.play_usage.player_id == player_id
            and (material_id is None and bool(self.materials(state, player_id))
                 or material_id in self.materials(state, player_id))
            and (any(self.targets(state, player_id, cid)
                     for cid in self.materials(state, player_id)) if material_id is None
                 else bool(self.targets(state, player_id, material_id))))

    def validate_start(self, state, action):
        if not self.available(state, action.player_id, action.material_id):
            raise InvalidCardUse('断粮当前不可用')

    def step(self, state, frame):
        from .military_tricks import TrickAction
        action = frame.action
        if frame.step_index in (0, 1):
            from .card_limits import validate_view_as_limits
            validate_view_as_limits(state, action.player_id, (action.material_id,), 'delayed.supply_shortage', skills=self.skills, skill_id='duanliang')
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '断粮：选择【兵粮寸断】目标', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(
                    state, action.player_id, action.material_id)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            self.validate_start(state, action)
            self.trick_rule.validate_targets(state, action.player_id, (target,))
            if target not in self.targets(state, action.player_id, action.material_id):
                raise InvalidCardUse('帷幕阻止该兵粮寸断目标')
            source = next(ref for ref, zone in state.zones.items()
                          if action.material_id in zone.card_ids)
            self.moves.move(state, CardMove(action.action_id + ':processing',
                (action.material_id,), source, ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.USE, action.player_id, action.action_id))
            state.metadata.setdefault('virtual_delayed_cards', {})[action.material_id] = 'delayed.supply_shortage'
            state.play_usage.record('delayed.supply_shortage')
            self.events.record(CardUsedEvent(action.action_id + ':used', action.player_id,
                action.material_id, (target,), 'delayed.supply_shortage'))
            frame.step_index = 2
            return StepResult.push(TrickAction(action.action_id + ':trick', action.player_id,
                action.material_id, 'delayed.supply_shortage', (target,)))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class LierenAction(Action):
    source_id: str
    target_id: str


class LierenHandler:
    def __init__(self, skills, moves, rng):
        self.skills, self.moves, self.rng = skills, moves, rng

    def _equipment(self, state, player_id):
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == player_id and ref.zone_type is ZoneType.EQUIPMENT
                     for cid in zone.card_ids)

    def step(self, state, frame):
        action = frame.action
        source, target = action.source_id, action.target_id
        if frame.step_index == 0:
            if (not state.players[source].is_alive or not state.players[target].is_alive
                    or not self.skills.has(state, source, 'lieren')
                    or not state.cards_in(ZoneRef(ZoneType.HAND, source))
                    or not state.cards_in(ZoneRef(ZoneType.HAND, target))):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', source,
                RequestType.YES_NO, '是否发动【烈刃】与受伤角色拼点？', action.action_id,
                frame.frame_id, subject_player_id=target))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not state.players[target].is_alive:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.push(PindianAction(action.action_id + ':pindian', source, target))
        if frame.step_index == 2:
            if frame.child_result is not True or not state.players[target].is_alive:
                return StepResult.complete(False)
            hand = state.cards_in(ZoneRef(ZoneType.HAND, target))
            equipment = self._equipment(state, target)
            choices = (('random_hand',) if hand else ()) + tuple(
                f'equipment:{cid}' for cid in equipment)
            if not choices:
                return StepResult.complete(True)
            frame.step_index = 3
            return StepResult.ask(PendingRequest(action.action_id + ':gain', source,
                RequestType.CHOOSE_OPTION, '烈刃：选择一张装备或随机获得一张手牌',
                action.action_id, frame.frame_id, choices=choices,
                subject_player_id=target))
        choice = frame.decision
        frame.decision = None
        if choice == 'random_hand':
            hand = state.cards_in(ZoneRef(ZoneType.HAND, target))
            if not hand:
                return StepResult.complete()
            card_id = self.rng.choice(hand)
            source_zone = ZoneRef(ZoneType.HAND, target)
        elif isinstance(choice, str) and choice.startswith('equipment:'):
            card_id = choice.split(':', 1)[1]
            source_zone = next((ref for ref, zone in state.zones.items()
                                if ref.player_id == target and ref.zone_type is ZoneType.EQUIPMENT
                                and card_id in zone.card_ids), None)
            if source_zone is None:
                return StepResult.complete()
        else:
            raise InvalidCardUse('烈刃获牌选择不合法')
        self.moves.move(state, CardMove(action.action_id + ':gain-card', (card_id,),
            source_zone, ZoneRef(ZoneType.HAND, source), CardMoveReason.SYSTEM,
            source, action.action_id))
        return StepResult.complete(True)


@dataclass(frozen=True, slots=True)
class YinghunAction(Action):
    player_id: str


class YinghunHandler:
    def __init__(self, skills):
        self.skills = skills

    def targets(self, state, owner):
        return tuple(pid for pid in state.seat_order if pid != owner
                     and state.players[pid].is_alive)

    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        if frame.step_index == 0:
            if (not state.players[owner].is_alive or not self.skills.has(state, owner, 'yinghun')
                    or state.players[owner].hp >= state.players[owner].max_hp
                    or not self.targets(state, owner)):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', owner,
                RequestType.YES_NO, '是否发动【英魂】？', action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not self.targets(state, owner):
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':target', owner,
                RequestType.CHOOSE_PLAYER, '英魂：选择另一名角色', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, owner)))
        if frame.step_index == 2:
            target = frame.decision
            frame.decision = None
            if target not in self.targets(state, owner):
                return StepResult.complete()
            frame.local['target'] = target
            frame.local['missing'] = state.players[owner].max_hp - state.players[owner].hp
            frame.step_index = 3
            return StepResult.ask(PendingRequest(action.action_id + ':mode', owner,
                RequestType.CHOOSE_OPTION, '英魂：选择摸牌及弃牌数量',
                action.action_id, frame.frame_id,
                choices=('draw_x_discard_one', 'draw_one_discard_x'),
                subject_player_id=target))
        if frame.step_index == 3:
            mode = frame.decision
            frame.decision = None
            frame.local['discard_count'] = (1 if mode == 'draw_x_discard_one'
                                            else frame.local['missing'])
            draw_count = (frame.local['missing'] if mode == 'draw_x_discard_one' else 1)
            frame.step_index = 4
            return StepResult.push(DrawCardsAction(action.action_id + ':draw',
                                                    frame.local['target'], draw_count))
        if frame.step_index == 4:
            target = frame.local['target']
            if not state.players[target].is_alive:
                return StepResult.complete()
            frame.step_index = 5
            return StepResult.push(ForcedDiscardAction(action.action_id + ':discard',
                                                       target, frame.local['discard_count']))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class HaoshiGiveAction(Action):
    player_id: str


class HaoshiGiveHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        hand = ZoneRef(ZoneType.HAND, owner)
        if frame.step_index == 0:
            cards = state.cards_in(hand)
            others = tuple(pid for pid in state.seat_order if pid != owner
                           and state.players[pid].is_alive)
            if len(cards) <= 5 or not others or not state.players[owner].is_alive:
                return StepResult.complete()
            lowest = min(len(state.cards_in(ZoneRef(ZoneType.HAND, pid))) for pid in others)
            eligible = tuple(pid for pid in others
                             if len(state.cards_in(ZoneRef(ZoneType.HAND, pid))) == lowest)
            frame.local['count'] = len(cards) // 2
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':recipient', owner,
                RequestType.CHOOSE_PLAYER, '好施：选择手牌最少的另一名角色',
                action.action_id, frame.frame_id, allowed_player_ids=eligible))
        if frame.step_index == 1:
            frame.local['recipient'] = frame.decision
            frame.decision = None
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':cards', owner,
                RequestType.CHOOSE_CARDS, '好施：选择交出的手牌',
                action.action_id, frame.frame_id, eligible_card_ids=state.cards_in(hand),
                min_count=frame.local['count'], max_count=frame.local['count'],
                subject_player_id=frame.local['recipient']))
        selected = tuple(frame.decision)
        frame.decision = None
        recipient = frame.local['recipient']
        if (state.players[recipient].is_alive and len(selected) == frame.local['count']
                and set(selected).issubset(state.cards_in(hand))):
            self.moves.move(state, CardMove(action.action_id + ':give', selected, hand,
                ZoneRef(ZoneType.HAND, recipient), CardMoveReason.SYSTEM,
                owner, action.action_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class DimengAction(Action):
    player_id: str


class DimengHandler:
    def __init__(self, skills):
        self.skills = skills

    def partners(self, state, owner, first=None):
        others = tuple(pid for pid in state.seat_order if pid != owner
                       and state.players[pid].is_alive)
        count = len(discardable_cards(state, owner))
        if first is None:
            return tuple(pid for pid in others if any(other != pid and
                abs(len(state.cards_in(ZoneRef(ZoneType.HAND, pid))) -
                    len(state.cards_in(ZoneRef(ZoneType.HAND, other)))) <= count
                for other in others))
        return tuple(pid for pid in others if pid != first and
            abs(len(state.cards_in(ZoneRef(ZoneType.HAND, first))) -
                len(state.cards_in(ZoneRef(ZoneType.HAND, pid)))) <= count)

    def available(self, state, owner):
        return (self.skills.has(state, owner, 'dimeng')
                and state.players[owner].is_alive
                and state.current_player_id == owner and state.current_phase is Phase.PLAY
                and state.play_usage is not None and not state.play_usage.count('skill.dimeng')
                and bool(self.partners(state, owner)))

    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        if frame.step_index == 0:
            if not self.available(state, owner):
                raise InvalidCardUse('缔盟当前不可用')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':first', owner,
                RequestType.CHOOSE_PLAYER, '缔盟：选择第一名其他角色',
                action.action_id, frame.frame_id,
                allowed_player_ids=self.partners(state, owner)))
        if frame.step_index == 1:
            first = frame.decision
            frame.decision = None
            frame.local['first'] = first
            partners = self.partners(state, owner, first)
            if not partners:
                return StepResult.complete(False)
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':second', owner,
                RequestType.CHOOSE_PLAYER, '缔盟：选择第二名其他角色',
                action.action_id, frame.frame_id, allowed_player_ids=partners))
        if frame.step_index == 2:
            second = frame.decision
            frame.decision = None
            first = frame.local['first']
            if second not in self.partners(state, owner, first):
                return StepResult.complete(False)
            frame.local['second'] = second
            count = abs(len(state.cards_in(ZoneRef(ZoneType.HAND, first))) -
                        len(state.cards_in(ZoneRef(ZoneType.HAND, second))))
            frame.local['cost'] = count
            frame.step_index = 3
            if count:
                return StepResult.push(ForcedDiscardAction(action.action_id + ':cost',
                                                           owner, count))
            return StepResult.continue_()
        if frame.step_index == 3:
            first, second = frame.local['first'], frame.local['second']
            if (frame.local['cost'] and frame.child_result != frame.local['cost']
                    or not state.players[owner].is_alive
                    or not state.players[first].is_alive or not state.players[second].is_alive):
                return StepResult.complete(False)
            state.play_usage.record('skill.dimeng')
            frame.step_index = 4
            return StepResult.push(SwapHandsAction(action.action_id + ':swap', first, second))
        return StepResult.complete(frame.child_result)


@dataclass(frozen=True, slots=True)
class BenghuaiAction(Action):
    player_id: str


class BenghuaiHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        if frame.step_index == 0:
            if (not state.players[owner].is_alive
                    or not self.skills.has(state, owner, 'benghuai')
                    or not any(pid != owner and player.is_alive
                               and player.hp < state.players[owner].hp
                               for pid, player in state.players.items())):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':choice', owner,
                RequestType.CHOOSE_OPTION, '崩坏：选择失去体力或减少体力上限',
                action.action_id, frame.frame_id,
                choices=('lose_hp', 'lose_max_hp')))
        if frame.step_index == 1:
            choice = frame.decision
            frame.decision = None
            frame.step_index = 2
            if choice == 'lose_hp':
                return StepResult.push(LoseHpAction(action.action_id + ':hp', owner, 1))
            return StepResult.push(LoseMaxHpAction(action.action_id + ':max-hp', owner, 1))
        return StepResult.complete(frame.child_result)


@dataclass(frozen=True, slots=True)
class BaonueAction(Action):
    source_id: str
    lord_id: str


class BaonueHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        action = frame.action
        source, lord = action.source_id, action.lord_id
        if frame.step_index == 0:
            if (source == lord or not state.players[source].is_alive
                    or not state.players[lord].is_alive
                    or state.players[lord].identity is not Identity.LORD
                    or self.skills.faction(state, source) is not Kingdom.QUN
                    or not self.skills.has(state, lord, 'baonue')):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', source,
                RequestType.YES_NO, '是否发动【暴虐】进行判定？', action.action_id,
                frame.frame_id, subject_player_id=lord))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.push(JudgmentAction(action.action_id + ':judge',
                                                 source, JudgmentPattern(suit=Suit.SPADE)))
        if frame.step_index == 2:
            if frame.child_result is not True or not state.players[lord].is_alive:
                return StepResult.complete()
            frame.step_index = 3
            return StepResult.push(RecoverAction(action.action_id + ':recover',
                                                 source, lord, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class LuanwuAction(Action):
    player_id: str


class LuanwuHandler:
    def __init__(self, skills, slash_rule):
        self.skills = skills
        self.slash_rule = slash_rule
        self.distance = DistanceSystem()

    def available(self, state, owner):
        return (self.skills.has(state, owner, 'luanwu')
                and state.players[owner].is_alive
                and not state.players[owner].marks.get('luanwu_used')
                and state.current_player_id == owner and state.current_phase is Phase.PLAY
                and state.play_usage is not None and state.play_usage.player_id == owner)

    def slash_cards(self, state, player_id):
        return tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                     if state.cards[cid].definition_id in
                     ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash'))

    def nearest_legal_targets(self, state, player_id):
        others = tuple(pid for pid in state.seat_order if pid != player_id
                       and state.players[pid].is_alive)
        if not others:
            return ()
        minimum = min(self.distance.distance_between(state, player_id, pid)
                      for pid in others)
        legal = set(self.slash_rule.target_candidates(state, player_id))
        return tuple(pid for pid in others if
                     self.distance.distance_between(state, player_id, pid) == minimum
                     and pid in legal)

    def step(self, state, frame):
        from .card_use import UseCardAction
        action = frame.action
        owner = action.player_id
        if frame.step_index == 0:
            if not self.available(state, owner):
                raise InvalidCardUse('乱武当前不可用')
            state.players[owner].marks['luanwu_used'] = 1
            state.play_usage.record('skill.luanwu')
            start = state.seat_order.index(owner)
            frame.local['order'] = (state.seat_order[start + 1:]
                                    + state.seat_order[:start])
            frame.step_index = 1
        if frame.step_index == 1:
            if state.status is GameStatus.FINISHED:
                return StepResult.complete()
            order = frame.local['order']
            while frame.cursor < len(order) and not state.players[order[frame.cursor]].is_alive:
                frame.cursor += 1
            if frame.cursor >= len(order):
                return StepResult.complete()
            victim = order[frame.cursor]
            frame.local['victim'] = victim
            frame.cursor += 1
            if not self.slash_cards(state, victim) or not self.nearest_legal_targets(state, victim):
                frame.step_index = 5
                return StepResult.push(LoseHpAction(action.action_id + ':lose:' + victim,
                                                    victim, 1))
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':choice:' + victim,
                victim, RequestType.CHOOSE_OPTION, '乱武：对最近角色使用杀或失去一点体力',
                action.action_id, frame.frame_id, choices=('slash', 'lose_hp')))
        if frame.step_index == 2:
            victim = frame.local['victim']
            choice = frame.decision
            frame.decision = None
            if choice == 'lose_hp':
                frame.step_index = 5
                return StepResult.push(LoseHpAction(action.action_id + ':lose:' + victim,
                                                    victim, 1))
            cards = self.slash_cards(state, victim)
            if not cards:
                frame.step_index = 5
                return StepResult.push(LoseHpAction(action.action_id + ':lose:' + victim,
                                                    victim, 1))
            frame.step_index = 3
            return StepResult.ask(PendingRequest(action.action_id + ':slash:' + victim,
                victim, RequestType.CHOOSE_CARD, '乱武：选择使用的杀',
                action.action_id, frame.frame_id, eligible_card_ids=cards))
        if frame.step_index == 3:
            victim = frame.local['victim']
            frame.local['card'] = frame.decision
            frame.decision = None
            targets = self.nearest_legal_targets(state, victim)
            if not targets:
                frame.step_index = 5
                return StepResult.push(LoseHpAction(action.action_id + ':lose:' + victim,
                                                    victim, 1))
            frame.step_index = 4
            return StepResult.ask(PendingRequest(action.action_id + ':target:' + victim,
                victim, RequestType.CHOOSE_PLAYER, '乱武：选择最近的合法杀目标',
                action.action_id, frame.frame_id, allowed_player_ids=targets))
        if frame.step_index == 4:
            victim = frame.local['victim']
            target = frame.decision
            frame.decision = None
            if (target not in self.nearest_legal_targets(state, victim)
                    or frame.local['card'] not in self.slash_cards(state, victim)):
                raise InvalidCardUse('乱武的杀或目标已不可用')
            frame.step_index = 5
            return StepResult.push(UseCardAction(action.action_id + ':use:' + victim,
                victim, frame.local['card'], (target,), forced=True))
        frame.step_index = 1
        return StepResult.continue_()


@dataclass(frozen=True, slots=True)
class JiuchiUse(Action):
    player_id: str
    material_id: str


class JiuchiHandler:
    def __init__(self, skills, moves, events, wine_rule):
        self.skills, self.moves, self.events = skills, moves, events
        self.wine_rule = wine_rule

    def materials(self, state, player_id):
        return tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                     if effective_suit(state, cid, player_id) is Suit.SPADE)

    def available(self, state, player_id, material_id=None):
        usage = state.play_usage
        limit = self.wine_rule.usage_limit(state, player_id)
        return (self.skills.has(state, player_id, 'jiuchi')
                and state.players[player_id].is_alive
                and state.current_player_id == player_id
                and state.current_phase is Phase.PLAY
                and usage is not None and usage.player_id == player_id
                and usage.turn_number == state.turn_number
                and (limit is None or usage.count('basic.wine') < limit)
                and self.wine_rule.can_use(state, player_id)
                and (bool(self.materials(state, player_id)) if material_id is None
                     else material_id in self.materials(state, player_id)))

    def step(self, state, frame):
        from .military_basics import WineAction
        action = frame.action
        if frame.step_index in (0, 1):
            from .card_limits import validate_view_as_limits
            validate_view_as_limits(state, action.player_id, (action.material_id,), 'basic.wine', skills=self.skills, skill_id='jiuchi')
        if frame.step_index == 0:
            if not self.available(state, action.player_id, action.material_id):
                raise InvalidCardUse('酒池当前不可用')
            virtual = VirtualCard('basic.wine', (action.material_id,),
                effective_suit(state, action.material_id, action.player_id),
                effective_color(state, action.material_id, action.player_id))
            self.moves.move(state, CardMove(action.action_id + ':processing',
                (action.material_id,), ZoneRef(ZoneType.HAND, action.player_id),
                ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE,
                action.player_id, action.action_id))
            state.play_usage.record('basic.wine')
            self.events.record(CardUsedEvent(action.action_id + ':used',
                action.player_id, action.material_id, (), virtual.definition_id))
            frame.step_index = 1
            return StepResult.push(WineAction(action.action_id + ':wine', action.player_id))
        processing = ZoneRef(ZoneType.PROCESSING)
        if action.material_id in state.cards_in(processing):
            self.moves.move(state, CardMove(action.action_id + ':discard',
                (action.material_id,), processing, ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.USE, action.player_id, action.action_id))
        self.events.record(CardResolvedEvent(action.action_id + ':resolved',
                                             action.player_id, action.material_id))
        return StepResult.complete(VirtualCard('basic.wine', (action.material_id,),
            effective_suit(state, action.material_id, action.player_id),
            effective_color(state, action.material_id, action.player_id)))
