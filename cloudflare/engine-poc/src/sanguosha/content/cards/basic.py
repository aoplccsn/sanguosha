"""T4 classic base cards: ordinary Slash, Dodge, and Peach only."""

from typing import Protocol

from sanguosha.engine.actions import Action
from sanguosha.engine.card_effects import PeachEffectAction, SlashEffectAction
from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.engine.card_rules import CardRuleRegistry, InvalidCardUse
from sanguosha.engine.distance import DistanceSystem
from sanguosha.model.card import CardDefinition
from sanguosha.model.enums import CardCategory, DamageNature, EquipmentSlot
from sanguosha.model.ids import CardDefinitionId, CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType
from .ids import DODGE_ID, PEACH_ID, SLASH_ID


class SlashTargetFilter(Protocol):
    def allows(self, state: GameState, user_id: PlayerId, target_id: PlayerId) -> bool: ...


class AnyLivingOpponent:
    """Compatibility filter used by isolated T4 rule tests."""

    def allows(self, state: GameState, user_id: PlayerId, target_id: PlayerId) -> bool:
        return target_id != user_id and target_id in state.players and state.players[target_id].is_alive


class SlashLimitProvider(Protocol):
    def limit(self, state: GameState, user_id: PlayerId) -> int | None: ...


class DefaultSlashLimit:
    def limit(self, state: GameState, user_id: PlayerId) -> int:
        return 1


class EquipmentSlashLimit:
    """One place for equipment-based Slash usage changes."""

    def limit(self, state: GameState, user_id: PlayerId) -> int | None:
        weapon = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, user_id, EquipmentSlot.WEAPON))
        if weapon and state.cards[weapon[0]].definition_id == "equipment.weapon.crossbow":
            return None
        return 1


class ReachableOpponent:
    def __init__(self, distance: DistanceSystem) -> None:
        self.distance = distance

    def allows(self, state: GameState, user_id: PlayerId, target_id: PlayerId) -> bool:
        return self.distance.can_reach_with_slash(state, user_id, target_id)


class SlashRule:
    requires_target_selection = True

    def __init__(self, target_filter: SlashTargetFilter | None = None, limit_provider: SlashLimitProvider | None = None) -> None:
        self.target_filter = target_filter or AnyLivingOpponent()
        self.limit_provider = limit_provider or DefaultSlashLimit()

    def can_use(self, state: GameState, user_id: PlayerId) -> bool:
        return True

    def target_candidates(self, state: GameState, user_id: PlayerId) -> tuple[PlayerId, ...]:
        return tuple(pid for pid in state.seat_order if self.target_filter.allows(state, user_id, pid))

    def validate_targets(self, state: GameState, user_id: PlayerId, targets: tuple[PlayerId, ...]) -> None:
        if len(targets) != 1 or targets[0] not in self.target_candidates(state, user_id):
            raise InvalidCardUse("Slash needs one other living legal target")

    def usage_limit(self, state: GameState, user_id: PlayerId) -> int | None:
        return self.limit_provider.limit(state, user_id)

    def effect_action(self, action_id: str, user_id: PlayerId, card_id: CardInstanceId, targets: tuple[PlayerId, ...]) -> Action:
        return SlashEffectAction(action_id, user_id, targets[0], card_id, DODGE_ID)


class DodgeRule:
    requires_target_selection = False

    def can_use(self, state: GameState, user_id: PlayerId) -> bool:
        return False

    def target_candidates(self, state: GameState, user_id: PlayerId) -> tuple[PlayerId, ...]:
        return ()

    def validate_targets(self, state: GameState, user_id: PlayerId, targets: tuple[PlayerId, ...]) -> None:
        raise InvalidCardUse("Dodge is response only")

    def usage_limit(self, state: GameState, user_id: PlayerId) -> None:
        return None

    def effect_action(self, action_id: str, user_id: PlayerId, card_id: CardInstanceId, targets: tuple[PlayerId, ...]) -> Action:
        raise InvalidCardUse("Dodge is response only")


class PeachRule:
    requires_target_selection = False

    def can_use(self, state: GameState, user_id: PlayerId) -> bool:
        player = state.players[user_id]
        return player.hp < player.max_hp

    def target_candidates(self, state: GameState, user_id: PlayerId) -> tuple[PlayerId, ...]:
        return (user_id,)

    def validate_targets(self, state: GameState, user_id: PlayerId, targets: tuple[PlayerId, ...]) -> None:
        if targets not in ((), (user_id,)):
            raise InvalidCardUse("Peach can only target its user in T4")

    def usage_limit(self, state: GameState, user_id: PlayerId) -> None:
        return None

    def effect_action(self, action_id: str, user_id: PlayerId, card_id: CardInstanceId, targets: tuple[PlayerId, ...]) -> Action:
        return PeachEffectAction(action_id, user_id, card_id)


def register_basic_cards(definitions: CardDefinitionRegistry, rules: CardRuleRegistry,
                         distance: DistanceSystem | None = None,
                         limit_provider: SlashLimitProvider | None = None) -> None:
    definitions.register(CardDefinition(SLASH_ID, "杀", CardCategory.BASIC, nature=DamageNature.NORMAL))
    definitions.register(CardDefinition(DODGE_ID, "闪", CardCategory.BASIC))
    definitions.register(CardDefinition(PEACH_ID, "桃", CardCategory.BASIC))
    rules.register(SLASH_ID, SlashRule(ReachableOpponent(distance) if distance else None, limit_provider))
    rules.register(DODGE_ID, DodgeRule())
    rules.register(PEACH_ID, PeachRule())
