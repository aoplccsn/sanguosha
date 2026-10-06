"""Classic Mountain skills using the shared turn and card movement pipeline."""

from dataclasses import dataclass

from sanguosha.model.enums import CardCategory, Identity, Kingdom, Phase, Suit, SkillType
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .requests import PendingRequest, RequestType
from .events import CardUsedEvent
from .distance import DistanceSystem
from .card_use import UseCardAction
from .forced_cards import discardable_cards
from .pindian import PindianAction
from .forced_cards import ForcedDiscardAction
from .turnover import TurnoverAction
from .judgment import JudgmentAction, JudgmentPattern
from .suits import effective_suit
from .hp import GainMaxHpAction, LoseMaxHpAction
from .recovery import RecoverAction
from .deck import DrawCardsAction
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
class TiaoxinAction(Action):
    player_id: str


class TiaoxinHandler:
    def __init__(self, skills, moves, slash_rule, definitions):
        self.skills = skills
        self.moves = moves
        self.slash_rule = slash_rule
        self.distance = DistanceSystem(definitions)

    def targets(self, state, player_id):
        return tuple(pid for pid in state.seat_order
                     if pid != player_id and state.players[pid].is_alive
                     and self.distance.distance_between(state, player_id, pid)
                     <= self.distance.attack_range(state, player_id))

    def slashes(self, state, target, challenger):
        if challenger not in self.slash_rule.target_candidates(state, target):
            return ()
        return tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, target))
                     if state.cards[cid].definition_id in
                     ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash'))

    def available(self, state, player_id):
        return (self.skills.has(state, player_id, 'tiaoxin')
                and state.current_player_id == player_id
                and state.current_phase is Phase.PLAY
                and state.play_usage is not None
                and not state.play_usage.count('skill.tiaoxin')
                and bool(self.targets(state, player_id)))

    def step(self, state, frame):
        action = frame.action
        actor = action.player_id
        if frame.step_index == 0:
            if not self.available(state, actor):
                raise InvalidCardUse('挑衅当前不可用')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':target', actor, RequestType.CHOOSE_PLAYER,
                '挑衅：选择攻击范围内的一名角色', action.action_id, frame.frame_id,
                allowed_player_ids=self.targets(state, actor)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            if not self.available(state, actor) or target not in self.targets(state, actor):
                raise InvalidCardUse('挑衅目标不合法')
            state.play_usage.record('skill.tiaoxin')
            frame.local['target'] = target
            slashes = self.slashes(state, target, actor)
            if slashes:
                frame.step_index = 2
                return StepResult.ask(PendingRequest(
                    action.action_id + ':slash', target, RequestType.CHOOSE_OPTION,
                    '挑衅：对姜维使用一张【杀】，或拒绝', action.action_id,
                    frame.frame_id, choices=(*slashes, 'decline')))
            frame.step_index = 4
        if frame.step_index == 2:
            choice = frame.decision
            frame.decision = None
            target = frame.local['target']
            if choice != 'decline':
                if choice not in self.slashes(state, target, actor):
                    raise InvalidCardUse('挑衅所用杀不合法')
                frame.step_index = 3
                return StepResult.push(UseCardAction(
                    action.action_id + ':forced-slash', target, choice, (actor,), forced=True))
            frame.step_index = 4
        if frame.step_index == 3:
            return StepResult.complete()
        target = frame.local['target']
        cards = discardable_cards(state, target)
        if not cards:
            return StepResult.complete()
        if frame.step_index == 4:
            frame.step_index = 5
            return StepResult.ask(PendingRequest(
                action.action_id + ':discard', actor, RequestType.CHOOSE_CARD,
                '挑衅：弃置目标的一张牌', action.action_id, frame.frame_id,
                eligible_card_ids=cards, subject_player_id=target))
        card_id = frame.decision
        frame.decision = None
        if card_id not in discardable_cards(state, target):
            raise InvalidCardUse('挑衅弃牌已不可用')
        source = next(ref for ref, zone in state.zones.items()
                      if ref.player_id == target and card_id in zone.card_ids)
        self.moves.move(state, CardMove(
            action.action_id + ':discard-card', (card_id,), source,
            ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
            actor, action.action_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class ZhijiAction(Action):
    player_id: str


class ZhijiHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        actor = frame.action.player_id
        player = state.players[actor]
        if frame.step_index == 0:
            if (not player.is_alive or not self.skills.has(state, actor, 'zhiji')
                    or player.marks.get('awakened_zhiji')
                    or state.cards_in(ZoneRef(ZoneType.HAND, actor))):
                return StepResult.complete(False)
            player.marks['awakened_zhiji'] = 1
            choices = ('draw', 'recover') if player.hp < player.max_hp else ('draw',)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':choice', actor, RequestType.CHOOSE_OPTION,
                '志继：摸两张牌或回复一点体力', frame.action.action_id,
                frame.frame_id, choices=choices))
        if frame.step_index == 1:
            choice = frame.decision
            frame.decision = None
            frame.step_index = 2
            if choice == 'recover' and player.hp < player.max_hp:
                return StepResult.push(RecoverAction(
                    frame.action.action_id + ':recover', actor, actor, 1))
            return StepResult.push(DrawCardsAction(
                frame.action.action_id + ':draw', actor, 2))
        if frame.step_index == 2:
            frame.step_index = 3
            return StepResult.push(LoseMaxHpAction(
                frame.action.action_id + ':max-hp', actor, 1))
        if player.is_alive:
            player.granted_skills['guanxing'] = 'zhiji'
        return StepResult.complete(player.is_alive)


@dataclass(frozen=True, slots=True)
class JiangAction(Action):
    player_id: str


class JiangHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        actor = frame.action.player_id
        if not state.players[actor].is_alive or not self.skills.has(state, actor, 'jiang'):
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':offer', actor, RequestType.YES_NO,
                '是否发动【激昂】摸一张牌？', frame.action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(
                frame.action.action_id + ':draw', actor, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class HunziAction(Action):
    player_id: str


class HunziHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        actor = frame.action.player_id
        player = state.players[actor]
        if frame.step_index == 0:
            if (not player.is_alive or not self.skills.has(state, actor, 'hunzi')
                    or player.marks.get('awakened_hunzi') or player.hp != 1):
                return StepResult.complete(False)
            player.marks['awakened_hunzi'] = 1
            frame.step_index = 1
            return StepResult.push(LoseMaxHpAction(
                frame.action.action_id + ':max-hp', actor, 1))
        if player.is_alive:
            player.granted_skills['yingzi'] = 'hunzi'
            player.granted_skills['yinghun'] = 'hunzi'
        return StepResult.complete(player.is_alive)


@dataclass(frozen=True, slots=True)
class ZhibaAction(Action):
    player_id: str


class ZhibaHandler:
    def __init__(self, skills, moves, events):
        self.skills = skills
        self.moves = moves
        self.events = events

    def lord(self, state, challenger):
        return next((pid for pid in state.seat_order
                     if pid != challenger and state.players[pid].is_alive
                     and state.players[pid].identity is Identity.LORD
                     and self.skills.has(state, pid, 'zhiba')
                     and state.cards_in(ZoneRef(ZoneType.HAND, pid))), None)

    def available(self, state, challenger):
        return (state.players[challenger].is_alive
                and self.skills.faction(state, challenger) is Kingdom.WU
                and state.current_player_id == challenger
                and state.current_phase is Phase.PLAY
                and state.play_usage is not None
                and not state.play_usage.count('skill.zhiba')
                and bool(state.cards_in(ZoneRef(ZoneType.HAND, challenger)))
                and self.lord(state, challenger) is not None)

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 0:
            if not self.available(state, actor):
                raise InvalidCardUse('制霸当前不可用')
            lord = self.lord(state, actor)
            state.play_usage.record('skill.zhiba')
            frame.local['lord'] = lord
            if state.players[lord].marks.get('awakened_hunzi'):
                frame.step_index = 1
                return StepResult.ask(PendingRequest(
                    frame.action.action_id + ':accept', lord, RequestType.YES_NO,
                    '制霸：是否接受拼点？', frame.action.action_id, frame.frame_id))
            frame.step_index = 2
        if frame.step_index == 1:
            accepted = frame.decision is True
            frame.decision = None
            if not accepted:
                return StepResult.complete()
            frame.step_index = 2
        if frame.step_index == 2:
            frame.step_index = 3
            return StepResult.push(PindianAction(
                frame.action.action_id + ':pindian', actor, frame.local['lord']))
        if frame.step_index == 3:
            event_id = frame.action.action_id + ':pindian:shown'
            shown = next(event for event in reversed(self.events.events)
                         if getattr(event, 'event_id', None) == event_id)
            lord_rank = shown.metadata['opponent_rank']
            challenger_rank = shown.metadata['source_rank']
            if lord_rank > challenger_rank:
                return StepResult.complete()
            cards = (shown.metadata['source_card_id'], shown.metadata['opponent_card_id'])
            available = tuple(cid for cid in cards
                              if cid in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
            if not available:
                return StepResult.complete()
            frame.local['claim_cards'] = available
            frame.step_index = 4
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':claim', frame.local['lord'], RequestType.YES_NO,
                '制霸：是否获得双方拼点牌？', frame.action.action_id, frame.frame_id))
        if frame.decision is True:
            cards = tuple(cid for cid in frame.local['claim_cards']
                          if cid in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
            if cards:
                self.moves.move(state, CardMove(
                    frame.action.action_id + ':claim-cards', cards,
                    ZoneRef(ZoneType.DISCARD_PILE),
                    ZoneRef(ZoneType.HAND, frame.local['lord']),
                    CardMoveReason.SYSTEM, frame.local['lord'], frame.action.action_id))
        frame.decision = None
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class ZhijianAction(Action):
    player_id: str


class ZhijianHandler:
    def __init__(self, skills, moves, definitions):
        self.skills = skills
        self.moves = moves
        self.definitions = definitions

    def materials(self, state, actor):
        return tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, actor))
                     if self.definitions.get(state.cards[cid].definition_id).category
                     is CardCategory.EQUIPMENT and self.targets(state,actor,cid))

    def targets(self, state, actor,card=None):
        return tuple(pid for pid in state.seat_order
                     if pid != actor and state.players[pid].is_alive and (card is None or self.definitions.get(state.cards[card].definition_id).equipment_slot not in state.players[pid].abolished_equipment_slots))

    def available(self, state, actor):
        return (self.skills.has(state, actor, 'zhijian')
                and state.current_player_id == actor
                and state.current_phase is Phase.PLAY
                and self.materials(state, actor) and self.targets(state, actor))

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 0:
            if not self.available(state, actor):
                raise InvalidCardUse('直谏当前不可用')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':equipment', actor, RequestType.CHOOSE_CARD,
                '直谏：选择一张手牌中的装备牌', frame.action.action_id,
                frame.frame_id, eligible_card_ids=self.materials(state, actor)))
        if frame.step_index == 1:
            card_id = frame.decision
            frame.decision = None
            if card_id not in self.materials(state, actor):
                raise InvalidCardUse('直谏装备牌已不可用')
            frame.local['equipment'] = card_id
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':target', actor, RequestType.CHOOSE_PLAYER,
                '直谏：选择装备的其他角色', frame.action.action_id, frame.frame_id,
                allowed_player_ids=self.targets(state, actor,card_id)))
        if frame.step_index == 2:
            target = frame.decision
            frame.decision = None
            card_id = frame.local['equipment']
            if target not in self.targets(state, actor,card_id) or card_id not in self.materials(state, actor):
                raise InvalidCardUse('直谏目标或装备已不可用')
            slot = self.definitions.get(state.cards[card_id].definition_id).equipment_slot
            destination = ZoneRef(ZoneType.EQUIPMENT, target, slot)
            old = state.cards_in(destination)
            if old:
                self.moves.move(state, CardMove(
                    frame.action.action_id + ':replace', old, destination,
                    ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
                    actor, frame.action.action_id))
            self.moves.move(state, CardMove(
                frame.action.action_id + ':equip', (card_id,),
                ZoneRef(ZoneType.HAND, actor), destination,
                CardMoveReason.USE, actor, frame.action.action_id))
            frame.step_index = 3
            return StepResult.push(DrawCardsAction(
                frame.action.action_id + ':draw', actor, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class GuzhengAction(Action):
    owner_id: str
    discard_player_id: str
    card_ids: tuple[str, ...]


class GuzhengHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def available_cards(self, state, action):
        discard = state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
        return tuple(cid for cid in action.card_ids if cid in discard)

    def step(self, state, frame):
        action = frame.action
        if (not state.players[action.owner_id].is_alive
                or not state.players[action.discard_player_id].is_alive
                or not self.skills.has(state, action.owner_id, 'guzheng')):
            return StepResult.complete()
        cards = self.available_cards(state, action)
        if frame.step_index == 0:
            if not cards:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':offer', action.owner_id, RequestType.YES_NO,
                '是否发动【固政】？', action.action_id, frame.frame_id,
                subject_player_id=action.discard_player_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not cards:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                action.action_id + ':return', action.owner_id, RequestType.CHOOSE_CARD,
                '固政：选择一张牌归还给弃牌角色', action.action_id,
                frame.frame_id, eligible_card_ids=cards,
                subject_player_id=action.discard_player_id))
        chosen = frame.decision
        frame.decision = None
        if chosen not in cards:
            raise InvalidCardUse('固政归还牌已不可用')
        discard_ref = ZoneRef(ZoneType.DISCARD_PILE)
        self.moves.move(state, CardMove(
            action.action_id + ':return-card', (chosen,), discard_ref,
            ZoneRef(ZoneType.HAND, action.discard_player_id),
            CardMoveReason.SYSTEM, action.owner_id, action.action_id))
        remaining = tuple(cid for cid in cards if cid != chosen
                          and cid in state.cards_in(discard_ref))
        if remaining:
            self.moves.move(state, CardMove(
                action.action_id + ':gain-rest', remaining, discard_ref,
                ZoneRef(ZoneType.HAND, action.owner_id),
                CardMoveReason.SYSTEM, action.owner_id, action.action_id))
        return StepResult.complete()


def transformable_skills(skills, general_id):
    general = skills.characters[general_id]
    return tuple(skill_id for skill_id in general.skill_ids
                 if skill_id not in general.metadata.get('derived_skills', ())
                 and skill_id in skills.skills
                 and skills.skills[skill_id].skill_type not in (SkillType.LIMITED, SkillType.AWAKENING)
                 and not any(skills.skills[skill_id].metadata.get(flag)
                             for flag in ('lord', 'limited', 'awakening', 'hidden', 'hidden_skill',
                                          'special', 'attached_lord'))
                 and skills.skills[skill_id].metadata.get('transferable') is not False)


def draw_transformations(state, player_id, count, skills, rng):
    in_play = {player.character_id for player in state.players.values()}
    held = set(state.players[player_id].transformation_pool)
    eligible = [general.id for general in skills.characters.values()
                if general.id not in in_play and general.id not in held
                and general.metadata.get('playable', True)
                and general.id != 'mountain_zuoci'
                and not general.metadata.get('god', False)
                and not general.metadata.get('development_only', False)]
    selected = []
    for _ in range(min(count, len(eligible))):
        general_id = rng.choice(eligible)
        eligible.remove(general_id)
        state.players[player_id].transformation_pool.append(general_id)
        selected.append(general_id)
    return tuple(selected)


@dataclass(frozen=True, slots=True)
class HuashenAction(Action):
    player_id: str


class HuashenHandler:
    def __init__(self, skills, rng):
        self.skills = skills
        self.rng = rng

    def step(self, state, frame):
        actor = frame.action.player_id
        player = state.players[actor]
        if frame.step_index == 0:
            if not player.is_alive or not self.skills.has(state, actor, 'huashen'):
                return StepResult.complete()
            if not player.transformation_pool:
                draw_transformations(state, actor, 2, self.skills, self.rng)
            choices = tuple(f'{general_id}:{skill_id}'
                for general_id in player.transformation_pool
                for skill_id in transformable_skills(self.skills, general_id))
            if player.active_transformation is not None:
                choices += ('keep',)
            if not choices:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':choose', actor, RequestType.CHOOSE_OPTION,
                '化身：选择化身武将及其一项合法技能',
                frame.action.action_id, frame.frame_id, choices=choices))
        choice = frame.decision
        frame.decision = None
        if choice == 'keep':
            return StepResult.complete()
        general_id, skill_id = choice.rsplit(':', 1)
        if (general_id not in player.transformation_pool
                or skill_id not in transformable_skills(self.skills, general_id)):
            raise InvalidCardUse('化身选择不合法')
        player.active_transformation = general_id
        player.transformation_skill = skill_id
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class XinshengAction(Action):
    player_id: str
    damage_points: int


class XinshengHandler:
    def __init__(self, skills, rng):
        self.skills = skills
        self.rng = rng

    def step(self, state, frame):
        actor = frame.action.player_id
        if not state.players[actor].is_alive or not self.skills.has(state, actor, 'xinsheng'):
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':offer', actor, RequestType.YES_NO,
                f'是否发动【新生】获得至多 {frame.action.damage_points} 张化身牌？',
                frame.action.action_id, frame.frame_id))
        if frame.decision is True:
            draw_transformations(state, actor, frame.action.damage_points,
                                 self.skills, self.rng)
        frame.decision = None
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class BeigeAction(Action):
    owner_id: str
    victim_id: str
    source_id: str | None


class BeigeHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def costs(self, state, owner):
        return discardable_cards(state, owner)

    def step(self, state, frame):
        action = frame.action
        owner = action.owner_id
        if (not state.players[owner].is_alive
                or not self.skills.has(state, owner, 'beige')):
            return StepResult.complete()
        if frame.step_index == 0:
            if not self.costs(state, owner):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':offer', owner, RequestType.YES_NO,
                '是否弃置一张牌发动【悲歌】？', action.action_id, frame.frame_id,
                subject_player_id=action.victim_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                action.action_id + ':cost', owner, RequestType.CHOOSE_CARD,
                '悲歌：选择弃置的一张牌', action.action_id, frame.frame_id,
                eligible_card_ids=self.costs(state, owner)))
        if frame.step_index == 2:
            cost = frame.decision
            frame.decision = None
            if cost not in self.costs(state, owner):
                raise InvalidCardUse('悲歌弃牌已不可用')
            source = next(ref for ref, zone in state.zones.items()
                          if ref.player_id == owner and cost in zone.card_ids)
            self.moves.move(state, CardMove(
                action.action_id + ':cost-move', (cost,), source,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
                owner, action.action_id))
            frame.step_index = 3
            return StepResult.push(JudgmentAction(
                action.action_id + ':judgment', action.victim_id,
                JudgmentPattern(), return_card_id=True))
        if frame.step_index == 3:
            card_id = frame.child_result
            suit = effective_suit(state, card_id, action.victim_id)
            frame.step_index = 4
            if suit is Suit.HEART and state.players[action.victim_id].is_alive:
                return StepResult.push(RecoverAction(
                    action.action_id + ':heart', owner, action.victim_id, 1))
            if suit is Suit.DIAMOND and state.players[action.victim_id].is_alive:
                return StepResult.push(DrawCardsAction(
                    action.action_id + ':diamond', action.victim_id, 2))
            if (action.source_id is not None and state.players[action.source_id].is_alive):
                if suit is Suit.CLUB:
                    return StepResult.push(ForcedDiscardAction(
                        action.action_id + ':club', action.source_id, 2))
                if suit is Suit.SPADE:
                    return StepResult.push(TurnoverAction(
                        action.action_id + ':spade', action.source_id))
        return StepResult.complete()


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
                from .forest import weimu_blocks
                if (definition == 'delayed.indulgence' and self.skills.has(state, pid, 'qianxun')
                        or weimu_blocks(state, pid, card_id, definition,
                                        source.player_id, self.skills)):
                    continue
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
