"""Human-visible read-only snapshots; opponent hands and identities stay hidden."""

from dataclasses import dataclass

from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.model.enums import Identity, Suit
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType


IDENTITY_LABELS = {
    Identity.LORD: "主公", Identity.LOYALIST: "忠臣",
    Identity.REBEL: "反贼", Identity.RENEGADE: "内奸",
}
GENERAL_PRESENTATION = {
    "blank-1": ("caocao", "魏"), "blank-2": ("liubei", "蜀"),
    "blank-3": ("sunquan", "吴"), "blank-4": ("lvbu", "群"), "blank-5": ("guanyu", "蜀"),
}
SUIT_SYMBOLS = {Suit.HEART: "♥", Suit.DIAMOND: "♦", Suit.SPADE: "♠", Suit.CLUB: "♣"}
RANK_LABELS = {1: "A", 11: "J", 12: "Q", 13: "K"}


@dataclass(frozen=True, slots=True)
class CardView:
    card_id: CardInstanceId
    name: str
    suit: str
    rank: str
    definition_id: str = ""
    category: str = "basic"


@dataclass(frozen=True, slots=True)
class PlayerView:
    player_id: PlayerId
    name: str
    character_name: str
    identity_label: str
    hp: int
    max_hp: int
    hand_count: int
    alive: bool
    active: bool
    character_id: str = ""
    faction: str = "群"
    chained: bool = False
    equipment: tuple[CardView,...] = ()
    judgments: tuple[CardView,...] = ()


@dataclass(frozen=True, slots=True)
class TableView:
    players: tuple[PlayerView, ...]
    hand: tuple[CardView, ...]
    current_phase: str
    turn_number: int
    deck_count: int
    discard_count: int
    result: str | None
    discard_top: CardView | None = None
    shared_cards: tuple[CardView,...] = ()


def project_for_human(
    state: GameState, definitions: CardDefinitionRegistry,
    human_id: PlayerId, character_names: dict[PlayerId, str],
) -> TableView:
    def card_view(cid):
        card=state.cards[cid]
        definition=definitions.get(card.definition_id)
        return CardView(cid,definition.name,SUIT_SYMBOLS[card.suit],RANK_LABELS.get(card.rank,str(card.rank)),
                        str(card.definition_id),definition.category.value)
    players = []
    for pid in state.seat_order:
        player = state.players[pid]
        visible = pid == human_id or pid in state.revealed_identities or player.identity is Identity.LORD
        players.append(PlayerView(
            pid, "你" if pid == human_id else f"玩家{player.seat + 1}",
            character_names.get(pid, str(player.character_id)),
            IDENTITY_LABELS[player.identity] if visible else "未知",
            player.hp, player.max_hp,
            len(state.cards_in(ZoneRef(ZoneType.HAND, pid))),
            player.is_alive, state.current_player_id == pid,
            GENERAL_PRESENTATION.get(str(player.character_id), (str(player.character_id), "群"))[0],
            GENERAL_PRESENTATION.get(str(player.character_id), ("", "群"))[1], player.chained,
            tuple(card_view(cid) for ref,z in state.zones.items() if ref.player_id==pid and ref.zone_type is ZoneType.EQUIPMENT for cid in z.card_ids),
            tuple(card_view(cid) for cid in state.cards_in(ZoneRef(ZoneType.JUDGMENT,pid))),
        ))
    hand = tuple(
        CardView(card_id, definitions.get(state.cards[card_id].definition_id).name,
                 SUIT_SYMBOLS[state.cards[card_id].suit],
                 RANK_LABELS.get(state.cards[card_id].rank, str(state.cards[card_id].rank)),
                 str(state.cards[card_id].definition_id), definitions.get(state.cards[card_id].definition_id).category.value)
        for card_id in state.cards_in(ZoneRef(ZoneType.HAND, human_id))
    )
    discard = state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    top = discard[-1] if discard else None
    top_view = (CardView(top, definitions.get(state.cards[top].definition_id).name,
                         SUIT_SYMBOLS[state.cards[top].suit],
                         RANK_LABELS.get(state.cards[top].rank, str(state.cards[top].rank)),
                         str(state.cards[top].definition_id), definitions.get(state.cards[top].definition_id).category.value) if top else None)
    return TableView(
        tuple(players), hand, state.current_phase.value if state.current_phase else "—",
        state.turn_number, len(state.cards_in(ZoneRef(ZoneType.DRAW_PILE))),
        len(state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))),
        state.victory.label if state.victory else None, top_view,
        tuple(card_view(cid) for ref,z in state.zones.items() if ref.zone_type is ZoneType.SPECIAL for cid in z.card_ids),
    )
