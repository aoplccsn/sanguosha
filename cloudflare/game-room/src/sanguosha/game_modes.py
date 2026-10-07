"""Mode definitions shared by setup, rooms and matches."""

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
        if len(self.roles) != self.seat_count or (self.victory_rule == 'classic-identity' and self.roles.count(Identity.LORD) != 1):
            raise ValueError('roles must match seats; identity modes require one lord')

    @property
    def public_sides(self) -> bool:
        return self.victory_rule != 'classic-identity'

    def team_for(self, player_id: PlayerId) -> str | None:
        if not self.public_sides:
            return None
        index = self.seats.index(player_id)
        return ('A' if index % 2 == 0 else 'B')

    def assign_roles(self, rng) -> dict[PlayerId, Identity]:
        roles = list(self.roles)
        if not self.public_sides:
            rng.shuffle(roles)
        return dict(zip(self.seats, roles))

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

DUEL_1V1 = GameModeDefinition('duel-1v1', 2, (Identity.PLAYER_A, Identity.PLAYER_B),
    lord_hp_bonus=0, victory_rule='last-side-standing')
TEAM_2V2 = GameModeDefinition('team-2v2', 4,
    (Identity.TEAM_A, Identity.TEAM_B, Identity.TEAM_A, Identity.TEAM_B),
    lord_hp_bonus=0, victory_rule='last-side-standing')

GAME_MODES = {mode.mode_id: mode for mode in (MILITARY_FIVE, MILITARY_EIGHT, DUEL_1V1, TEAM_2V2)}


def game_mode(mode_id: str) -> GameModeDefinition:
    try:
        return GAME_MODES[mode_id]
    except KeyError as exc:
        raise ValueError(f'unknown game mode: {mode_id}') from exc
