from sanguosha.content.characters.standard import (
    ALL_65_GENERAL_POOL, DISABLED_GOD_POOL, GOD_GENERAL_POOL,
    PLAYABLE_57_GENERAL_POOL, PLAYABLE_65_GENERAL_POOL,
)


def test_t13_all_gods_are_in_the_playable_roster():
    assert len(ALL_65_GENERAL_POOL) == 65
    assert len(PLAYABLE_57_GENERAL_POOL) == 57
    assert len(GOD_GENERAL_POOL) == 8
    assert len(PLAYABLE_65_GENERAL_POOL) == 65
    assert not DISABLED_GOD_POOL
    assert all(character.metadata["playable"] for character in PLAYABLE_57_GENERAL_POOL)
    assert all(character.metadata["playable"] for character in GOD_GENERAL_POOL)
    assert {character.metadata["pack"] for character in GOD_GENERAL_POOL} == {"wind", "fire", "forest", "mountain"}


def test_god_portraits_use_the_existing_static_art():
    assert all(character.metadata["portrait_mode"] == "static" for character in PLAYABLE_57_GENERAL_POOL)
    assert all(character.metadata["portrait_mode"] == "static" for character in GOD_GENERAL_POOL)
