"""Finite physical deck and draw action, using the shared move service."""

from dataclasses import dataclass
import json
from pathlib import Path

from sanguosha.content.cards.ids import DODGE_ID, PEACH_ID, SLASH_ID
from sanguosha.model.card import CardInstance
from sanguosha.model.enums import Suit
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .events import Event
from .resolution import ResolutionFrame
from .requests import PendingRequest, RequestType
from .rng import RandomSource


DRAW = ZoneRef(ZoneType.DRAW_PILE)
DISCARD = ZoneRef(ZoneType.DISCARD_PILE)


CLASSIC_MILITARY_MANIFEST = Path(__file__).resolve().parents[3] / "data" / "decks" / "classic_military.json"


def classic_military_deck(rng: RandomSource) -> tuple[dict[CardInstanceId, CardInstance], CardZone]:
    """Load the fixed Standard + EX + Military physical prints, then shuffle order."""
    from collections import Counter

    if CLASSIC_MILITARY_MANIFEST.is_file():
        manifest = json.loads(CLASSIC_MILITARY_MANIFEST.read_text(encoding="utf-8"))
    else:
        # The Cloudflare Python bundle contains modules, not the repository JSON file.
        # Its build step generates this module directly from the same manifest.
        from .cloudflare_deck_data import MANIFEST
        manifest = MANIFEST
    prints = manifest["cards"]
    if len(prints) != 160 or Counter(item["set"] for item in prints) != {"standard": 104, "military": 52, "ex": 4}:
        raise ValueError("classic military manifest has the wrong print count")
    cards: dict[CardInstanceId, CardInstance] = {}
    for item in prints:
        card_id = CardInstanceId(item["instance_id"])
        if card_id in cards:
            raise ValueError(f"duplicate physical card id: {card_id}")
        cards[card_id] = CardInstance(card_id, item["definition_id"], Suit(item["suit"]), item["rank"])
    order = list(cards)
    rng.shuffle(order)
    return cards, CardZone(DRAW, order)


def basic_deck(rng: RandomSource) -> tuple[dict[CardInstanceId, CardInstance], CardZone]:
    """Temporary 80-card deck; order and identities are deterministic for a seed."""
    definitions = (SLASH_ID,) * 48 + (DODGE_ID,) * 20 + (PEACH_ID,) * 12
    suits = (Suit.SPADE, Suit.HEART, Suit.CLUB, Suit.DIAMOND)
    cards: dict[CardInstanceId, CardInstance] = {}
    order: list[CardInstanceId] = []
    for index, definition_id in enumerate(definitions, start=1):
        card_id = CardInstanceId(f"card-{index:03d}")
        cards[card_id] = CardInstance(card_id, definition_id, suits[(index - 1) % 4], (index - 1) % 13 + 1)
        order.append(card_id)
    rng.shuffle(order)
    return cards, CardZone(DRAW, order)


class DeckService:
    def __init__(self, rng: RandomSource, moves: CardMoveService) -> None:
        self.rng = rng
        self.moves = moves

    def ensure_draw(self, state: GameState, action_id: str) -> bool:
        if state.cards_in(DRAW):
            return True
        recycled = list(state.cards_in(DISCARD))
        if not recycled:
            return False
        self.rng.shuffle(recycled)
        self.moves.move(state, CardMove(action_id+':reshuffle', tuple(recycled), DISCARD, DRAW,
                                       CardMoveReason.SYSTEM, related_action_id=action_id))
        return True

    def draw(self, state: GameState, player_id: PlayerId, count: int, action_id: str) -> int:
        drawn = 0
        cycle = 0
        hand = ZoneRef(ZoneType.HAND, player_id)
        while drawn < count:
            available = state.cards_in(DRAW)
            if not available:
                recycled = list(state.cards_in(DISCARD))
                if not recycled:
                    break
                self.rng.shuffle(recycled)
                self.moves.move(state, CardMove(
                    f"{action_id}:reshuffle:{cycle}", tuple(recycled), DISCARD, DRAW,
                    CardMoveReason.SYSTEM, related_action_id=action_id,
                ))
                cycle += 1
                available = state.cards_in(DRAW)
            batch = available[: count - drawn]
            self.moves.move(state, CardMove(
                f"{action_id}:draw:{cycle}", batch, DRAW, hand,
                CardMoveReason.SYSTEM, player_id, action_id,
            ))
            drawn += len(batch)
            cycle += 1
        return drawn


@dataclass(frozen=True, slots=True)
class DrawCardsAction(Action):
    player_id: PlayerId
    count: int


class DrawCardsHandler:
    def __init__(self, deck: DeckService) -> None:
        self.deck = deck

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, DrawCardsAction)
        return StepResult.complete(self.deck.draw(state, action.player_id, action.count, action.action_id))


@dataclass(frozen=True, slots=True)
class RevealTopCardsAction(Action):
    player_id: PlayerId
    count: int


class RevealTopCardsHandler:
    """Reveal physical top cards publicly without drawing them into a hand."""

    def __init__(self, deck: DeckService, events):
        self.deck, self.events = deck, events

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        if action.count < 0:
            raise ValueError('reveal count must be nonnegative')
        revealed = []
        for index in range(action.count):
            if not self.deck.ensure_draw(state, f'{action.action_id}:ensure:{index}'):
                break
            card_id = state.cards_in(DRAW)[0]
            self.deck.moves.move(state, CardMove(
                f'{action.action_id}:reveal:{index}', (card_id,), DRAW,
                ZoneRef(ZoneType.PROCESSING), CardMoveReason.SYSTEM,
                action.player_id, action.action_id))
            self.events.record(Event(f'{action.action_id}:shown:{index}',
                'card_revealed', action.player_id,
                metadata={'card_id': str(card_id)}))
            revealed.append(card_id)
        return StepResult.complete(tuple(revealed))


class DrawPhaseBody:
    def __init__(self, skills=None):
        self.skills = skills

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        if frame.step_index == 1:
            action = frame.action
            state.players[action.player_id].marks.pop('luoyi', None)
            if (self.skills is not None and not frame.local.get('haoshi_offered')
                    and self.skills.has(state, action.player_id, 'haoshi')):
                frame.local['haoshi_offered'] = True
                frame.step_index = 9
                return StepResult.ask(PendingRequest(action.action_id + ':haoshi',
                    action.player_id, RequestType.YES_NO,
                    '是否发动【好施】额外摸两张牌？', action.action_id, frame.frame_id))
            if (self.skills is not None and not frame.local.get('zaiqi_offered')
                    and self.skills.has(state, action.player_id, 'zaiqi')
                    and state.players[action.player_id].hp < state.players[action.player_id].max_hp):
                frame.local['zaiqi_offered'] = True
                frame.step_index = 7
                return StepResult.ask(PendingRequest(action.action_id + ':zaiqi',
                    action.player_id, RequestType.YES_NO,
                    '是否发动【再起】代替正常摸牌？', action.action_id, frame.frame_id))
            if (self.skills is not None and self.skills.has(state, action.player_id, 'tuxi')
                    and any(pid != action.player_id and state.players[pid].is_alive
                            and state.cards_in(ZoneRef(ZoneType.HAND, pid)) for pid in state.seat_order)):
                frame.step_index = 5
                return StepResult.ask(PendingRequest(action.action_id + ':tuxi', action.player_id,
                    RequestType.YES_NO, '是否发动【突袭】改为取得其他角色的手牌？',
                    action.action_id, frame.frame_id))
            if self.skills is not None and self.skills.has(state, action.player_id, 'luoyi'):
                frame.step_index = 3
                return StepResult.ask(PendingRequest(action.action_id + ':luoyi', action.player_id,
                    RequestType.YES_NO, '是否发动【裸衣】少摸一张牌，使本回合杀与决斗伤害增加？',
                    action.action_id, frame.frame_id))
            frame.step_index = 2
            bonus = int(self.skills is not None and self.skills.has(state, action.player_id, 'yingzi'))
            return StepResult.push(DrawCardsAction(f"{action.action_id}:draw", action.player_id, 2 + bonus))
        if frame.step_index == 3:
            action = frame.action
            activate = frame.decision is True
            frame.decision = None
            if activate:
                state.players[action.player_id].marks['luoyi'] = 1
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(f"{action.action_id}:draw", action.player_id,
                                                   1 if activate else 2))
        if frame.step_index == 5:
            action = frame.action
            activate = frame.decision is True
            frame.decision = None
            frame.step_index = 2
            if activate:
                from .skills import TuxiAction
                return StepResult.push(TuxiAction(action.action_id + ':tuxi', action.player_id))
            return StepResult.push(DrawCardsAction(f"{action.action_id}:draw", action.player_id, 2))
        if frame.step_index == 7:
            action = frame.action
            wanted = frame.decision is True
            frame.decision = None
            if wanted:
                from .forest import ZaiqiAction
                frame.step_index = 2
                return StepResult.push(ZaiqiAction(action.action_id + ':zaiqi', action.player_id))
            frame.step_index = 1
            return StepResult.continue_()
        if frame.step_index == 9:
            action = frame.action
            wanted = frame.decision is True
            frame.decision = None
            if wanted:
                frame.step_index = 10
                return StepResult.push(DrawCardsAction(action.action_id + ':haoshi-draw',
                                                       action.player_id, 4))
            frame.step_index = 1
            return StepResult.continue_()
        if frame.step_index == 10:
            from .forest import HaoshiGiveAction
            action = frame.action
            frame.step_index = 2
            return StepResult.push(HaoshiGiveAction(action.action_id + ':haoshi-give',
                                                    action.player_id))
        return StepResult.complete(frame.child_result)
