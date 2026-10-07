"""Seeded identity and general draft before any engine turn begins."""

from dataclasses import dataclass, field
from enum import StrEnum

from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.engine.requests import Decision, PendingRequest, RequestType
from sanguosha.engine.rng import PythonRandomSource, RandomSource
from sanguosha.model.enums import Identity
from sanguosha.model.ids import CharacterId, PlayerId
from sanguosha.game_modes import game_mode


SEATS = tuple(PlayerId(f'p{i}') for i in range(1, 6))
ROLE_SET = (Identity.LORD, Identity.LOYALIST, Identity.REBEL, Identity.REBEL, Identity.RENEGADE)


class SetupStage(StrEnum):
    IDENTITY_REVEAL = 'identity_reveal'
    CHOOSE_GENERAL = 'choose_general'
    COMPLETE = 'complete'


@dataclass(slots=True)
class Pregame:
    rng: RandomSource
    identities: dict[PlayerId, Identity]
    candidates: tuple[CharacterId, ...]
    stage: SetupStage = SetupStage.IDENTITY_REVEAL
    generals: dict[PlayerId, CharacterId] = field(default_factory=dict)
    human_id: PlayerId = SEATS[0]
    mode_id: str = 'military-five'

    @classmethod
    def create(cls, seed: int | None = None, mode_id: str = 'military-five') -> 'Pregame':
        rng = PythonRandomSource(seed)
        mode = game_mode(mode_id)
        identities = mode.assign_roles(rng)
        roster = list(PLAYABLE_GENERAL_POOL)
        from sanguosha.general_draft import draft_general_ids
        candidates = draft_general_ids((c.id for c in roster), (), rng, mode.general_offer_count)
        return cls(rng, identities,
                   candidates,
                   mode_id=mode_id)

    @property
    def lord_id(self) -> PlayerId | None:
        return next((pid for pid, identity in self.identities.items() if identity is Identity.LORD), None)

    @property
    def human_identity(self) -> Identity:
        return self.identities[self.human_id]

    def acknowledge_identity(self) -> None:
        if self.stage is not SetupStage.IDENTITY_REVEAL:
            raise ValueError('identity reveal is not pending')
        self.stage = SetupStage.CHOOSE_GENERAL

    @property
    def pending_request(self) -> PendingRequest | None:
        if self.stage is not SetupStage.CHOOSE_GENERAL:
            return None
        return PendingRequest('setup:general', self.human_id, RequestType.CHOOSE_OPTION,
                              '选择武将并确认', 'setup', 'setup',
                              choices=tuple(map(str, self.candidates)))

    def submit(self, decision: Decision) -> None:
        request = self.pending_request
        if request is None or decision.request_id != request.request_id or decision.player_id != self.human_id:
            raise ValueError('no matching general choice is pending')
        request.validate(decision.value)
        chosen = CharacterId(decision.value)
        self.generals[self.human_id] = chosen
        available = [character.id for character in PLAYABLE_GENERAL_POOL if character.id != chosen]
        for pid in game_mode(self.mode_id).seats[1:]:
            from sanguosha.general_draft import draft_general_ids
            offer = draft_general_ids(available, (), self.rng, game_mode(self.mode_id).general_offer_count)
            selected = self.rng.choice(offer)
            available.remove(selected)
            self.generals[pid] = selected
        self.stage = SetupStage.COMPLETE

    def timeout(self) -> None:
        request = self.pending_request
        if request is None:
            raise ValueError('general choice is not pending')
        self.submit(Decision(request.request_id, self.human_id, request.timeout_value()))

