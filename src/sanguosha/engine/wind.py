"""Classic Wind skills integrated with shared turn and resolution services."""

from dataclasses import dataclass

from sanguosha.model.enums import CardCategory, DamageNature, Phase, Suit
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .military_basics import MilitaryDamageAction, SlashSequence
from .judgment import JudgmentAction, JudgmentPattern
from .deck import DrawCardsAction
from .suits import effective_suit
from .requests import PendingRequest, RequestType
from .recovery import RecoverAction


@dataclass(frozen=True, slots=True)
class ShensuAction(Action):
    player_id: str
    branch: str


class WindPhaseOffers:
    """Offer registered phase-boundary actions before scheduling a phase."""

    def __init__(self, skills, definitions):
        self.skills = skills
        self.definitions = definitions

    def equipment_cards(self, state, player_id):
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == player_id
                     and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                     for cid in zone.card_ids
                     if self.definitions.get(state.cards[cid].definition_id).category
                     is CardCategory.EQUIPMENT)

    def targets(self, state, player_id):
        return tuple(pid for pid in state.seat_order if pid != player_id
                     and state.players[pid].is_alive
                     and not (self.skills.has(state, pid, 'kongcheng')
                              and not state.cards_in(ZoneRef(ZoneType.HAND, pid))))

    def __call__(self, state, player_id, phase, action_id):
        if phase is Phase.PREPARATION and self.skills.has(state, player_id, 'ruoyu'):
            from .mountain import RuoyuAction
            player = state.players[player_id]
            if (not player.marks.get('awakened_ruoyu')
                    and all(not other.is_alive or other.hp >= player.hp
                            for other in state.players.values())):
                return RuoyuAction(action_id + ':ruoyu', player_id)
        if phase is Phase.PREPARATION and self.skills.has(state, player_id, 'zaoxian'):
            from .mountain import ZaoxianAction, field_zone
            if (not state.players[player_id].marks.get('awakened_zaoxian')
                    and len(state.cards_in(field_zone(player_id))) >= 3):
                return ZaoxianAction(action_id + ':zaoxian', player_id)
        if phase is Phase.PLAY and self.skills.has(state, player_id, 'fangquan'):
            from .mountain import FangquanSkipAction
            return FangquanSkipAction(action_id + ':fangquan', player_id)
        if phase in (Phase.JUDGMENT, Phase.DRAW, Phase.PLAY, Phase.DISCARD) and self.skills.has(state, player_id, 'qiaobian'):
            if state.cards_in(ZoneRef(ZoneType.HAND, player_id)):
                from .mountain import QiaobianAction
                return QiaobianAction(action_id + ':qiaobian', player_id, phase)
        if phase is Phase.DRAW and self.skills.has(state, player_id, 'shuangxiong'):
            from .fire import ShuangxiongAction
            return ShuangxiongAction(action_id + ':shuangxiong', player_id)
        if not self.skills.has(state, player_id, 'shensu') or not self.targets(state, player_id):
            return None
        if phase is Phase.JUDGMENT:
            return ShensuAction(action_id + ':shensu-a', player_id, 'A')
        if phase is Phase.PLAY and self.equipment_cards(state, player_id):
            return ShensuAction(action_id + ':shensu-b', player_id, 'B')
        return None


class ShensuHandler:
    def __init__(self, offers, moves):
        self.offers = offers
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        player_id = action.player_id
        if not state.players[player_id].is_alive:
            return StepResult.complete()
        if frame.step_index == 0:
            if not self.offers.targets(state, player_id):
                return StepResult.complete()
            if action.branch == 'B' and not self.offers.equipment_cards(state, player_id):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':offer', player_id, RequestType.YES_NO,
                '是否发动【神速】' + action.branch + '？', action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            if action.branch == 'B':
                eligible = self.offers.equipment_cards(state, player_id)
                if not eligible:
                    return StepResult.complete()
                frame.step_index = 2
                return StepResult.ask(PendingRequest(
                    action.action_id + ':cost', player_id, RequestType.CHOOSE_CARD,
                    '神速：选择弃置的一张装备牌', action.action_id, frame.frame_id,
                    eligible_card_ids=eligible))
            frame.step_index = 3
            return self._ask_target(state, frame)
        if frame.step_index == 2:
            cost = frame.decision
            frame.decision = None
            if cost not in self.offers.equipment_cards(state, player_id):
                raise InvalidCardUse('神速装备牌代价不合法')
            frame.local['cost'] = cost
            frame.step_index = 3
            return self._ask_target(state, frame)
        if frame.step_index == 3:
            target = frame.decision
            frame.decision = None
            if target not in self.offers.targets(state, player_id):
                raise InvalidCardUse('神速目标不合法')
            if action.branch == 'B':
                cost = frame.local['cost']
                if cost not in self.offers.equipment_cards(state, player_id):
                    raise InvalidCardUse('神速装备牌代价已不可用')
                source = next(ref for ref, zone in state.zones.items() if cost in zone.card_ids)
                self.moves.move(state, CardMove(action.action_id + ':discard', (cost,), source,
                    ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, player_id))
                state.players[player_id].marks['skip_play'] = 1
            else:
                state.players[player_id].marks['skip_judgment'] = 1
                state.players[player_id].marks['skip_draw'] = 1
            frame.step_index = 4
            return StepResult.push(SlashSequence(action.action_id + ':slash', player_id, '',
                (target,), VirtualCard('basic.slash', (), None, None)))
        return StepResult.complete(frame.child_result)

    def _ask_target(self, state, frame):
        action = frame.action
        targets = self.offers.targets(state, action.player_id)
        if not targets:
            return StepResult.complete()
        return StepResult.ask(PendingRequest(
            action.action_id + ':target', action.player_id, RequestType.CHOOSE_PLAYER,
            '神速：选择一名【杀】的目标（无距离限制）', action.action_id,
            frame.frame_id, allowed_player_ids=targets))


def buqu_pile(player_id):
    return ZoneRef(ZoneType.SPECIAL, player_id, special_key='buqu')


@dataclass(frozen=True, slots=True)
class BuquAction(Action):
    player_id: str


class BuquOffer:
    def __init__(self, skills):
        self.skills = skills

    def __call__(self, state, player_id, action_id):
        if self.skills.has(state, player_id, 'buqu') and state.players[player_id].is_alive:
            return BuquAction(action_id + ':buqu', player_id)
        return None


class BuquHandler:
    def __init__(self, deck, moves):
        self.deck = deck
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            self.deck.ensure_draw(state, action.action_id)
            draw = ZoneRef(ZoneType.DRAW_PILE)
            available = state.cards_in(draw)
            if not available:
                return StepResult.complete(False)
            card_id = available[0]
            pile = buqu_pile(action.player_id)
            existing_ranks = {state.cards[cid].rank for cid in state.cards_in(pile)}
            unique = state.cards[card_id].rank not in existing_ranks
            destination = pile if unique else ZoneRef(ZoneType.DISCARD_PILE)
            self.moves.move(state, CardMove(action.action_id + ':reveal', (card_id,),
                draw, destination, CardMoveReason.SYSTEM, action.player_id, action.action_id))
            if not unique:
                return StepResult.complete(False)
            frame.step_index = 1
            return StepResult.push(RecoverAction(action.action_id + ':recover',
                action.player_id, action.player_id, 1 - state.players[action.player_id].hp))
        return StepResult.complete(True)


class WindHandLimit:
    def __call__(self, state, player_id):
        pile_count = len(state.cards_in(buqu_pile(player_id)))
        return pile_count if pile_count else max(0, state.players[player_id].hp)


@dataclass(frozen=True, slots=True)
class LeijiAction(Action):
    player_id: str


class LeijiHandler:
    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            targets = tuple(pid for pid in state.seat_order if pid != action.player_id
                            and state.players[pid].is_alive)
            if not targets:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', action.player_id,
                RequestType.YES_NO, '使用或打出【闪】后，是否发动【雷击】？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            targets = tuple(pid for pid in state.seat_order if pid != action.player_id
                            and state.players[pid].is_alive)
            if not targets:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '雷击：选择一名其他角色判定',
                action.action_id, frame.frame_id, allowed_player_ids=targets))
        if frame.step_index == 2:
            target = frame.decision
            frame.decision = None
            if target == action.player_id or not state.players[target].is_alive:
                raise InvalidCardUse('雷击目标不合法')
            frame.local['target'] = target
            frame.step_index = 3
            return StepResult.push(JudgmentAction(action.action_id + ':judgment', target,
                JudgmentPattern(), return_card_id=True))
        if frame.step_index == 3:
            target = frame.local['target']
            card_id = frame.child_result
            if not isinstance(card_id, str) or not state.players[target].is_alive:
                return StepResult.complete()
            suit = effective_suit(state, card_id, target)
            if suit is Suit.SPADE:
                frame.step_index = 5
                return StepResult.push(MilitaryDamageAction(action.action_id + ':thunder-2',
                    action.player_id, target, 2, DamageNature.THUNDER))
            if suit is Suit.CLUB:
                frame.step_index = 4
                return StepResult.push(RecoverAction(action.action_id + ':recover',
                    action.player_id, action.player_id, 1))
            return StepResult.complete()
        if frame.step_index == 4:
            target = frame.local['target']
            if not state.players[target].is_alive:
                return StepResult.complete()
            frame.step_index = 5
            return StepResult.push(MilitaryDamageAction(action.action_id + ':thunder-1',
                action.player_id, target, 1, DamageNature.THUNDER))
        return StepResult.complete()
