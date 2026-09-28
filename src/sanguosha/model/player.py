"""Runtime player state. Card positions are not duplicated here."""

from dataclasses import dataclass, field

from .enums import Identity, PlayerStatus
from .ids import CharacterId, PlayerId


@dataclass(slots=True)
class PlayerState:
    player_id: PlayerId
    seat: int
    character_id: CharacterId
    identity: Identity
    hp: int
    max_hp: int
    status: PlayerStatus = PlayerStatus.ALIVE
    chained: bool = False
    face_up: bool = True
    marks: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.player_id or not self.character_id:
            raise ValueError("player and character ids are required")
        if self.seat < 0 or self.max_hp < 1:
            raise ValueError("seat must be nonnegative and max_hp positive")
        if self.hp > self.max_hp:
            raise ValueError("hp cannot exceed max_hp")

    @property
    def is_alive(self) -> bool:
        return self.status is PlayerStatus.ALIVE
