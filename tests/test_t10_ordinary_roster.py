from sanguosha.content.characters.standard import (
    ALL_65_GENERAL_POOL, DISABLED_GOD_POOL, PLAYABLE_57_GENERAL_POOL,
)


def test_t10_playability_boundary_is_explicit():
    assert len(ALL_65_GENERAL_POOL) == 65
    assert len(PLAYABLE_57_GENERAL_POOL) == 57
    assert len(DISABLED_GOD_POOL) == 8
    assert all(character.metadata["playable"] for character in PLAYABLE_57_GENERAL_POOL)
    assert all(not character.metadata["playable"] for character in DISABLED_GOD_POOL)
    assert {character.metadata["pack"] for character in DISABLED_GOD_POOL} == {"wind", "fire", "forest", "mountain"}


def test_god_portraits_are_reserved_for_future_animated_pipeline():
    assert all(character.metadata["portrait_mode"] == "static" for character in PLAYABLE_57_GENERAL_POOL)
    assert all(character.metadata["portrait_mode"] == "animated" for character in DISABLED_GOD_POOL)
