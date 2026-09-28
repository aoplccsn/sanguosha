from dataclasses import FrozenInstanceError

import pytest

from sanguosha.model.card import CardDefinition, CardInstance
from sanguosha.model.character import CharacterDefinition
from sanguosha.model.enums import (
    CardCategory,
    Color,
    Gender,
    Identity,
    Kingdom,
    PlayerStatus,
    SkillType,
    Suit,
)
from sanguosha.model.ids import (
    CardDefinitionId,
    CardInstanceId,
    CharacterId,
    PlayerId,
    SkillId,
)
from sanguosha.model.player import PlayerState
from sanguosha.model.skill import SkillDefinition
from sanguosha.model.state import GameState
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType


def player(number: int) -> PlayerState:
    return PlayerState(
        player_id=PlayerId(f"p{number}"),
        seat=number,
        character_id=CharacterId("test_character"),
        identity=Identity.LORD if number == 0 else Identity.REBEL,
        hp=4,
        max_hp=4,
    )


def test_card_definition_is_separate_and_immutable() -> None:
    source = {"edition": "test"}
    definition = CardDefinition(CardDefinitionId("slash"), "杀", CardCategory.BASIC, metadata=source)
    source["edition"] = "changed"
    assert definition.metadata["edition"] == "test"
    with pytest.raises(FrozenInstanceError):
        definition.name = "闪"  # type: ignore[misc]
    with pytest.raises(TypeError):
        definition.metadata["edition"] = "changed"  # type: ignore[index]
    assert not hasattr(definition, "instance_id")
    assert not hasattr(definition, "suit")


def test_card_instances_have_stable_independent_ids_and_colors() -> None:
    red = CardInstance(CardInstanceId("card-1"), CardDefinitionId("slash"), Suit.HEART, 7)
    black = CardInstance(CardInstanceId("card-2"), CardDefinitionId("slash"), Suit.SPADE, 7)
    duplicate_print = CardInstance(CardInstanceId("card-3"), CardDefinitionId("slash"), Suit.HEART, 7)
    assert (red.color, black.color) == (Color.RED, Color.BLACK)
    assert red != black and red != duplicate_print
    assert duplicate_print.instance_id != red.instance_id
    assert CardInstance(CardInstanceId("card-4"), CardDefinitionId("slash"), Suit.DIAMOND, 1).color is Color.RED
    assert CardInstance(CardInstanceId("card-5"), CardDefinitionId("slash"), Suit.CLUB, 1).color is Color.BLACK


def test_character_and_skill_definitions_are_immutable() -> None:
    skills = [SkillId("test_skill")]
    character = CharacterDefinition(
        CharacterId("test_character"), "测试武将", Kingdom.WEI, 4, Gender.MALE, skills
    )
    skills.append(SkillId("another"))
    skill = SkillDefinition(SkillId("test_skill"), "测试技能", "仅供模型测试", SkillType.TRIGGERED)
    assert character.skill_ids == (SkillId("test_skill"),)
    assert character.kingdom is Kingdom.WEI and character.max_hp == 4
    with pytest.raises(FrozenInstanceError):
        character.max_hp = 5  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        skill.name = "changed"  # type: ignore[misc]


def test_player_runtime_state_is_independent() -> None:
    first, second = player(0), player(1)
    first.hp = 2
    first.chained = True
    first.marks["test"] = 1
    first.status = PlayerStatus.DEAD
    assert (first.identity, first.seat, first.status) == (Identity.LORD, 0, PlayerStatus.DEAD)
    assert second.hp == 4 and not second.chained and second.marks == {}
    assert not first.is_alive and second.is_alive
    assert not hasattr(first, "hand")


def test_zones_keep_ids_without_shared_defaults() -> None:
    first = CardZone(ZoneRef(ZoneType.DRAW_PILE))
    second = CardZone(ZoneRef(ZoneType.DISCARD_PILE))
    first.card_ids.append(CardInstanceId("c1"))
    assert second.card_ids == []
    with pytest.raises(ValueError):
        CardZone(first.ref, [CardInstanceId("c1"), CardInstanceId("c1")])
    with pytest.raises(ValueError):
        ZoneRef(ZoneType.HAND)


def test_game_state_has_one_location_source_and_five_players() -> None:
    players = {p.player_id: p for p in (player(i) for i in range(5))}
    cards = {
        CardInstanceId("c1"): CardInstance(CardInstanceId("c1"), CardDefinitionId("slash"), Suit.HEART, 7),
        CardInstanceId("c2"): CardInstance(CardInstanceId("c2"), CardDefinitionId("slash"), Suit.SPADE, 7),
    }
    hand = ZoneRef(ZoneType.HAND, PlayerId("p0"))
    draw = ZoneRef(ZoneType.DRAW_PILE)
    state = GameState(
        ruleset_id="classic-test",
        players=players,
        seat_order=tuple(players),
        cards=cards,
        zones={hand: CardZone(hand, [CardInstanceId("c1")]), draw: CardZone(draw, [CardInstanceId("c2")])},
    )
    assert len(state.players) == 5
    assert state.get_player(PlayerId("p0")).identity is Identity.LORD
    assert state.cards_in(hand) == (CardInstanceId("c1"),)
    assert state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) == ()
    assert not hasattr(state.get_player(PlayerId("p0")), "hand")


def test_game_state_rejects_duplicate_or_missing_card_locations() -> None:
    card_id = CardInstanceId("c1")
    card = CardInstance(card_id, CardDefinitionId("slash"), Suit.HEART, 7)
    draw, discard = ZoneRef(ZoneType.DRAW_PILE), ZoneRef(ZoneType.DISCARD_PILE)
    with pytest.raises(ValueError, match="exactly one"):
        GameState("test", cards={card_id: card}, zones={draw: CardZone(draw, [card_id]), discard: CardZone(discard, [card_id])})
    with pytest.raises(ValueError, match="exactly one"):
        GameState("test", cards={card_id: card})


def test_game_state_defaults_are_not_shared() -> None:
    first, second = GameState("test"), GameState("test")
    first.metadata["x"] = 1
    first.players[PlayerId("p0")] = player(0)
    assert second.metadata == {} and second.players == {}
