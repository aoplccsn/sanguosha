"""Explicit, synchronous T2 action resolution infrastructure."""

from .actions import Action, ActionHandler, ResultValue, StepKind, StepResult
from .engine import EngineStatus, GameEngine
from .errors import EngineError, InvalidDecision, InvalidEngineState, ResolutionError, UnknownActionHandler, UnknownRequest
from .events import Event, EventRecorder
from .registry import ActionHandlerRegistry
from .requests import ChoiceValue, Decision, PendingRequest, RequestType
from .resolution import FrameStatus, ResolutionFrame, ResolutionStack
from .events import PhaseEndedEvent, PhaseSkippedEvent, PhaseStartedEvent, TurnEndedEvent, TurnStartedEvent
from .phases import (
    END_PLAY_PHASE, EndOnlyPlayOptions, NoOpPhaseBody, PhaseAction,
    PhaseActionHandler, PhaseBodyRegistry, PlayOptionProvider,
    PlayPhaseBody, standard_phase_bodies,
)
from .turn_order import InvalidTurn, next_alive_player
from .turns import STANDARD_PHASE_ORDER, TurnAction, TurnActionHandler
from .card_registry import CardDefinitionRegistry, UnknownCardDefinition
from .card_moves import CardMove, CardMoveReason, CardMoveService, InvalidCardMove
from .card_rules import CardRuleRegistry, CardUseValidator, InvalidCardUse, TargetValidator
from .card_use import LegalPlayActionProvider, UseCardAction, UseCardActionHandler
from .damage import DamageAction, DamageActionHandler, InvalidDamage
from .recovery import RecoverAction, RecoverActionHandler, InvalidRecovery
from .response import InvalidResponse, RespondWithCardAction, RespondWithCardHandler
from .card_effects import PeachEffectAction, PeachEffectHandler, SlashEffectAction, SlashEffectHandler
from .requests import PASS_RESPONSE, ResponsePass
from .events import (
    AfterDamageEvent, BeforeDamageEvent, CardMovedEvent, CardRespondedEvent,
    CardResolvedEvent, CardUsedEvent, DamageDealtEvent, DyingRequiredEvent,
    HpRecoveredEvent,
)
from .deck import DeckService, DrawCardsAction, DrawCardsHandler, DrawPhaseBody, basic_deck
from .discard import DiscardPhaseBody
from .dying import DyingAction, DyingActionHandler
from .death import DeathAction, DeathActionHandler
from .identity import IdentitySystem
from .events import (
    DyingRescuedEvent, PlayerDiedEvent, KillRewardEvent,
    LordPenaltyEvent, GameEndedEvent,
)
