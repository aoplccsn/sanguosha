"""Active-use and target validation, delegated to registered card rules."""

from typing import Protocol

from sanguosha.model.enums import Phase
from sanguosha.model.ids import CardDefinitionId, CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action
from .card_registry import CardDefinitionRegistry, UnknownCardDefinition
from .errors import EngineError


class InvalidCardUse(EngineError):
    pass


class CardRule(Protocol):
    requires_target_selection: bool

    def can_use(self, state: GameState, user_id: PlayerId) -> bool: ...

    def target_candidates(self, state: GameState, user_id: PlayerId) -> tuple[PlayerId, ...]: ...

    def validate_targets(self, state: GameState, user_id: PlayerId, targets: tuple[PlayerId, ...]) -> None: ...

    def usage_limit(self, state: GameState, user_id: PlayerId) -> int | None: ...

    def effect_action(self, action_id: str, user_id: PlayerId, card_id: CardInstanceId, targets: tuple[PlayerId, ...]) -> Action: ...


class CardRuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[CardDefinitionId, CardRule] = {}

    def register(self, definition_id: CardDefinitionId, rule: CardRule) -> None:
        if definition_id in self._rules:
            raise InvalidCardUse(f"duplicate card rule {definition_id}")
        self._rules[definition_id] = rule

    def get(self, definition_id: CardDefinitionId) -> CardRule:
        try:
            return self._rules[definition_id]
        except KeyError as exc:
            raise InvalidCardUse(f"no active-use rule for {definition_id}") from exc

    def replace(self, definition_id: CardDefinitionId, rule: CardRule) -> None:
        self.get(definition_id)
        self._rules[definition_id] = rule


class TargetValidator:
    def validate(self, rule: CardRule, state: GameState, user_id: PlayerId, targets: tuple[PlayerId, ...]) -> None:
        rule.validate_targets(state, user_id, targets)


class CardUseValidator:
    def __init__(self, definitions: CardDefinitionRegistry, rules: CardRuleRegistry, targets: TargetValidator) -> None:
        self.definitions = definitions
        self.rules = rules
        self.targets = targets

    def rule_for(self, state: GameState, card_id: CardInstanceId) -> CardRule:
        try:
            definition_id = state.cards[card_id].definition_id
            self.definitions.get(definition_id)
            return self.rules.get(definition_id)
        except KeyError as exc:
            raise InvalidCardUse(f"unknown card instance {card_id}") from exc
        except UnknownCardDefinition as exc:
            raise InvalidCardUse(f"unregistered card definition for {card_id}") from exc

    def validate_card(self, state: GameState, user_id: PlayerId, card_id: CardInstanceId) -> CardRule:
        if user_id not in state.players or not state.players[user_id].is_alive:
            raise InvalidCardUse("user is not alive")
        if state.current_player_id != user_id or state.current_phase is not Phase.PLAY:
            raise InvalidCardUse("card can only be used in the owner's play phase")
        if card_id not in state.cards_in(ZoneRef(ZoneType.HAND, user_id)):
            raise InvalidCardUse("card is not in user's hand")
        rule = self.rule_for(state, card_id)
        usage = state.play_usage
        if usage is None or usage.player_id != user_id or usage.turn_number != state.turn_number:
            raise InvalidCardUse("play phase usage state is missing")
        limit = rule.usage_limit(state, user_id)
        if limit is not None and usage.count(getattr(rule, 'usage_key', state.cards[card_id].definition_id)) >= limit:
            raise InvalidCardUse("card use limit reached")
        if not rule.can_use(state, user_id):
            raise InvalidCardUse("card's active-use condition is not met")
        return rule

    def validate_final(self, state: GameState, user_id: PlayerId, card_id: CardInstanceId, targets: tuple[PlayerId, ...]) -> CardRule:
        rule = self.validate_card(state, user_id, card_id)
        self.targets.validate(rule, state, user_id, targets)
        return rule

    def can_offer(self, state: GameState, user_id: PlayerId, card_id: CardInstanceId) -> bool:
        try:
            rule = self.validate_card(state, user_id, card_id)
            return not rule.requires_target_selection or bool(rule.target_candidates(state, user_id))
        except InvalidCardUse:
            return False
