"""Human-visible read-only snapshots; opponent hands and identities stay hidden."""

from sanguosha.engine.private_hands import can_view_hand
from dataclasses import dataclass, field

from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.suits import effective_suit
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
    "caocao": ("caocao", "魏"), "liubei": ("liubei", "蜀"),
    "sunquan": ("sunquan", "吴"), "lvbu": ("lvbu", "群"), "guanyu": ("guanyu", "蜀"),
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
    equipment_slot: str = ""
    details: str = ""


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
    base_distance: int | None = None
    effective_distance: int | None = None
    attack_range: int = 1
    skill_labels: tuple[str, ...] = ()
    # Presentation state is deliberately read-only and derived from runtime
    # state so Web and PySide can share the same avatar semantics.
    face_up: bool = True
    marks: dict[str, int] | None = None
    special_piles: dict[str, tuple[CardView, ...]] = field(default_factory=dict)
    active_transformation: str = ""
    transformation_pool: tuple[str, ...] = ()
    revealed_hand: tuple[CardView, ...] = ()
    abolished_equipment_slots: tuple[str,...] = ()


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
    from sanguosha.engine.skill_leases import suppressed
    def card_view(cid, equipment_slot="", judgment=False):
        card=state.cards[cid]
        definition_id=(state.metadata.get('virtual_delayed_cards', {}).get(cid, card.definition_id)
                       if judgment else card.definition_id)
        if not equipment_slot and not judgment and cid in state.cards_in(ZoneRef(ZoneType.HAND, human_id)):
            from sanguosha.engine.yj2011_tier3 import canonical_definition
            definition_id=canonical_definition(state, skills, human_id, definition_id,cid)
        definition=definitions.get(definition_id)
        detail = ""
        if definition.equipment_slot is not None:
            slot_name = {"weapon": "武器", "armor": "防具", "defensive_horse": "+1 坐骑",
                         "offensive_horse": "-1 坐骑"}.get(definition.equipment_slot.value, "装备")
            detail = f"{definition.name}\n{slot_name}"
            if definition.attack_range is not None:
                detail += f"\n攻击范围：{definition.attack_range}"
            summary = definition.metadata.get("effect_summary", "暂无效果说明")
            detail += f"\n效果：{summary}"
        return CardView(cid,definition.name,SUIT_SYMBOLS[effective_suit(state, cid)],RANK_LABELS.get(card.rank,str(card.rank)),
                        str(definition_id),definition.category.value, equipment_slot or (definition.equipment_slot.value if definition.equipment_slot is not None else ""), detail)
    players = []
    distance = DistanceSystem(definitions)
    from sanguosha.engine.skills import SkillRegistry
    skills = SkillRegistry()
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
            str(player.character_id) if player.character_id in skills.characters else GENERAL_PRESENTATION.get(str(player.character_id), (str(player.character_id), "群"))[0],
            {"wei":"魏", "shu":"蜀", "wu":"吴", "qun":"群"}[skills.faction(state, pid).value]
            if player.character_id in skills.characters else GENERAL_PRESENTATION.get(str(player.character_id), ("", "群"))[1], player.chained,
            tuple(card_view(cid, ref.equipment_slot.value) for ref,z in state.zones.items() if ref.player_id==pid and ref.zone_type is ZoneType.EQUIPMENT for cid in z.card_ids),
            tuple(card_view(cid, judgment=True) for cid in state.cards_in(ZoneRef(ZoneType.JUDGMENT,pid))),
            distance.base_distance(state,human_id,pid) if pid != human_id and state.players[human_id].is_alive and player.is_alive else None,
            distance.distance_between(state,human_id,pid) if pid != human_id and state.players[human_id].is_alive and player.is_alive else None,
            distance.attack_range(state,pid) if player.is_alive else 1,
            tuple(skills.skills[sid].name + (" · 已用" if sid == 'zhiheng' and state.play_usage and state.play_usage.player_id == pid
                                         and state.play_usage.count('skill.zhiheng') else "") +
                  (" · 主公技" if skills.skills[sid].metadata.get('lord') else "") +
                  (" · 已失去" if sid in player.disabled_skills or suppressed(state,pid,sid) else "")
                  for sid in dict.fromkeys((*skills.characters[player.character_id].skill_ids,
                                            *player.granted_skills,
                                            *((player.transformation_skill,) if player.transformation_skill else ()))))
            if player.character_id in skills.characters else (),
            player.face_up, {key:(1 if key in ('yj_gongqi','yj_zishou','qiaoshui_success','qiaoshui_trick_lock','zhuikong_self_only') else value)
                             for key,value in player.marks.items() if key!='quan'},
            {ref.special_key: tuple(
                card_view(cid) if ((not ref.special_key.startswith('committed:')
                    and ref.special_key != 'star')
                    or pid == human_id
                    or state.metadata.get('revealed_committed', {}).get(cid))
                else CardView('hidden:' + ref.special_key + ':' + str(index), '未知扣置牌', '', '')
                for index,cid in enumerate(zone.card_ids))
             for ref, zone in state.zones.items()
             if ref.zone_type is ZoneType.SPECIAL and ref.player_id == pid and zone.card_ids},
            player.active_transformation or "",
            tuple(player.transformation_pool) if pid == human_id else (),
            tuple(card_view(cid) for cid in state.cards_in(ZoneRef(ZoneType.HAND, pid)))
            if pid!=human_id and can_view_hand(state,human_id,pid) else (),
            tuple(sorted(slot.value for slot in player.abolished_equipment_slots)),
        ))
    hand = tuple(card_view(card_id) for card_id in state.cards_in(ZoneRef(ZoneType.HAND, human_id)))
    discard = state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    top = discard[-1] if discard else None
    concealed = state.metadata.get('concealed_discard_cards', {}).get(top)
    if top is not None and concealed:
        definition = definitions.get(concealed)
        top_view = CardView('hidden-discard', '蛊惑·' + definition.name, '', '',
                            str(concealed), definition.category.value)
    else:
        top_view = (CardView(top, definitions.get(state.cards[top].definition_id).name,
                             SUIT_SYMBOLS[state.cards[top].suit],
                             RANK_LABELS.get(state.cards[top].rank, str(state.cards[top].rank)),
                             str(state.cards[top].definition_id), definitions.get(state.cards[top].definition_id).category.value) if top else None)
    return TableView(
        tuple(players), hand, state.current_phase.value if state.current_phase else "—",
        state.turn_number, len(state.cards_in(ZoneRef(ZoneType.DRAW_PILE))),
        len(state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))),
        state.victory.label if state.victory else None, top_view,
        tuple(card_view(cid) for ref,z in state.zones.items()
              if ref.zone_type is ZoneType.SPECIAL and ref.player_id is None for cid in z.card_ids),
    )
