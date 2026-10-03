"""Identity-game mode definitions shared by setup, rooms and matches."""

from dataclasses import dataclass

from sanguosha.model.enums import Identity
from sanguosha.model.ids import PlayerId


@dataclass(frozen=True, slots=True)
class GameModeDefinition:
    mode_id: str
    seat_count: int
    roles: tuple[Identity, ...]
    general_offer_count: int = 10
    lord_hp_bonus: int = 1
    victory_rule: str = 'classic-identity'
    allow_gods_default: bool = False

    def __post_init__(self):
        if len(self.roles) != self.seat_count or self.roles.count(Identity.LORD) != 1:
            raise ValueError('identity mode roles must match seats and contain one lord')

    @property
    def seats(self) -> tuple[PlayerId, ...]:
        return tuple(PlayerId(f'p{index}') for index in range(1, self.seat_count + 1))


MILITARY_FIVE = GameModeDefinition('military-five', 5, (
    Identity.LORD, Identity.LOYALIST, Identity.REBEL,
    Identity.REBEL, Identity.RENEGADE))
MILITARY_EIGHT = GameModeDefinition('military-eight', 8, (
    Identity.LORD, Identity.LOYALIST, Identity.LOYALIST,
    Identity.REBEL, Identity.REBEL, Identity.REBEL,
    Identity.REBEL, Identity.RENEGADE))

GAME_MODES = {mode.mode_id: mode for mode in (MILITARY_FIVE, MILITARY_EIGHT)}


def game_mode(mode_id: str) -> GameModeDefinition:
    try:
        return GAME_MODES[mode_id]
    except KeyError as exc:
        raise ValueError(f'unknown game mode: {mode_id}') from exc
