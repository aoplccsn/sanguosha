"""Equipment use and replacement through CardMoveService."""

from dataclasses import dataclass

from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .card_registry import CardDefinitionRegistry
from .card_rules import CardRuleRegistry, InvalidCardUse
from .resolution import ResolutionFrame


@dataclass(frozen=True, slots=True)
class EquipCardAction(Action):
    player_id: PlayerId
    card_id: CardInstanceId


class EquipCardHandler:
    def __init__(self, moves: CardMoveService, definitions: CardDefinitionRegistry) -> None:
        self.moves = moves
        self.definitions = definitions

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, EquipCardAction)
        definition = self.definitions.get(state.cards[action.card_id].definition_id)
        slot = definition.equipment_slot
        if slot is None:
            raise InvalidCardUse("card has no equipment slot")
        processing = ZoneRef(ZoneType.PROCESSING)
        if action.card_id not in state.cards_in(processing):
            raise InvalidCardUse("equipment card is not processing")
        destination = ZoneRef(ZoneType.EQUIPMENT, action.player_id, slot)
        old = state.cards_in(destination)
        if old:
            self.moves.move(state, CardMove(
                f"{action.action_id}:replace", old, destination, ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.DISCARD, action.player_id, action.action_id,
            ))
        self.moves.move(state, CardMove(
            f"{action.action_id}:equip", (action.card_id,), processing, destination,
            CardMoveReason.USE, action.player_id, action.action_id,
        ))
        return StepResult.complete()


class EquipmentRule:
    requires_target_selection = False

    def can_use(self, state: GameState, user_id: PlayerId) -> bool:
        return True

    def target_candidates(self, state: GameState, user_id: PlayerId) -> tuple[PlayerId, ...]:
        return ()

    def validate_targets(self, state: GameState, user_id: PlayerId, targets: tuple[PlayerId, ...]) -> None:
        if targets:
            raise InvalidCardUse("equipment does not select a target")

    def usage_limit(self, state: GameState, user_id: PlayerId) -> None:
        return None

    def effect_action(self, action_id: str, user_id: PlayerId, card_id: CardInstanceId,
                      targets: tuple[PlayerId, ...]) -> Action:
        return EquipCardAction(action_id, user_id, card_id)


def register_equipment_rules(definitions: CardDefinitionRegistry, rules: CardRuleRegistry) -> None:
    from sanguosha.content.cards.classic_military import ARMORS, HORSES, WEAPONS

    ids = [f"equipment.weapon.{key}" for key, _, _ in WEAPONS]
    ids += [f"equipment.armor.{key}" for key, _ in ARMORS]
    ids += [f"equipment.horse.{key}" for key, _, _ in HORSES]
    for definition_id in ids:
        if definitions.get(definition_id).equipment_slot is None:
            raise InvalidCardUse(f"invalid equipment slot for {definition_id}")
        rules.register(definition_id, EquipmentRule())
