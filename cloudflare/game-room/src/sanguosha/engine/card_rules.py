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
    def __init__(self, definitions: CardDefinitionRegistry, rules: CardRuleRegistry, targets: TargetValidator, skills=None) -> None:
        self.definitions = definitions
        self.rules = rules
        self.targets = targets
        self.skills = skills

    def rule_for(self, state: GameState, card_id: CardInstanceId, user_id=None) -> CardRule:
        try:
            definition_id = state.cards[card_id].definition_id
            if user_id is None:
                user_id = next((ref.player_id for ref, zone in state.zones.items()
                    if ref.zone_type is ZoneType.HAND and card_id in zone.card_ids), None)
            if user_id is not None:
                from .yj2011_tier3 import canonical_definition
                definition_id = canonical_definition(state, self.skills, user_id, definition_id,card_id)
            self.definitions.get(definition_id)
            return self.rules.get(definition_id)
        except KeyError as exc:
            raise InvalidCardUse(f"unknown card instance {card_id}") from exc
        except UnknownCardDefinition as exc:
            raise InvalidCardUse(f"unregistered card definition for {card_id}") from exc

    def target_candidates(self, state: GameState, user_id: PlayerId, card_id: CardInstanceId) -> tuple[PlayerId, ...]:
        rule = self.rule_for(state, card_id, user_id)
        candidates = rule.target_candidates(state, user_id)
        from .longnu import modifiers
        ignore_distance,unlimited=modifiers(state,self.skills,user_id,card_id)
        if getattr(rule,'usage_key',None)=='basic.slash' and (ignore_distance or unlimited) and rule.can_use(state,user_id):
            from .distance import DistanceSystem
            from .yj2011_tier3 import scoped_target,hand
            distance=DistanceSystem(self.definitions)
            ordinary_limit=rule.limit_provider.limit(state,user_id)
            candidates=tuple(q for q in state.seat_order if q!=user_id and state.players[q].is_alive
                and (ignore_distance or distance.can_reach_with_slash(state,user_id,q) or scoped_target(state,user_id,q))
                and (unlimited or ordinary_limit is None or state.play_usage is None or state.play_usage.count('basic.slash')<ordinary_limit or scoped_target(state,user_id,q))
                and not (self.skills.has(state,q,'kongcheng') and not hand(state,q)))
        if (state.current_phase is Phase.PLAY and state.players[user_id].marks.get('yj_zishou') == state.turn_number):
            candidates = tuple(pid for pid in candidates if pid == user_id)
        from .fuhuanghou import target_allowed
        candidates=tuple(q for q in candidates if target_allowed(state,user_id,q))
        if self.skills is None:
            return candidates
        from .forest import weimu_blocks
        from .yj2011_tier3 import canonical_definition
        definition_id = canonical_definition(state,self.skills,user_id,str(state.cards[card_id].definition_id),card_id)
        return tuple(pid for pid in candidates if not weimu_blocks(
            state, pid, card_id, definition_id, user_id, self.skills))

    def validate_targets_for_card(self, rule: CardRule, state: GameState,
                                  user_id: PlayerId, card_id: CardInstanceId,
                                  targets: tuple[PlayerId, ...]) -> None:
        from .longnu import modifiers
        ignore_distance,unlimited=modifiers(state,self.skills,user_id,card_id)
        if getattr(rule,'usage_key',None)=='basic.slash' and (ignore_distance or unlimited):
            low,high=rule.target_bounds(state,user_id,card_id)
            if not low<=len(targets)<=high or len(set(targets))!=len(targets):raise InvalidCardUse('invalid Slash targets')
        else:
            self.targets.validate(rule, state, user_id, targets)
        if any(pid not in self.target_candidates(state, user_id, card_id) for pid in targets):
            raise InvalidCardUse("target is protected from this card")

    def validate_card(self, state: GameState, user_id: PlayerId, card_id: CardInstanceId) -> CardRule:
        if user_id not in state.players or not state.players[user_id].is_alive:
            raise InvalidCardUse("user is not alive")
        if state.current_player_id != user_id or state.current_phase is not Phase.PLAY:
            raise InvalidCardUse("card can only be used in the owner's play phase")
        if card_id not in state.cards_in(ZoneRef(ZoneType.HAND, user_id)):
            raise InvalidCardUse("card is not in user's hand")
        from .card_limits import card_allowed
        if not card_allowed(state, user_id, (card_id,)):
            raise InvalidCardUse("card color is prohibited by Qianxi")
        rule = self.rule_for(state, card_id, user_id)
        from .forest import weimu_blocks
        from .yj2011_tier3 import canonical_definition
        definition=canonical_definition(state,self.skills,user_id,state.cards[card_id].definition_id,card_id)
        if definition in ('delayed.lightning','trick.ex_nihilo') and weimu_blocks(state,user_id,card_id,definition,user_id,self.skills):
            raise InvalidCardUse('帷幕禁止此牌指定自己')
        usage = state.play_usage
        if usage is None or usage.player_id != user_id or usage.turn_number != state.turn_number:
            raise InvalidCardUse("play phase usage state is missing")
        from .longnu import modifiers
        limit = None if modifiers(state,self.skills,user_id,card_id)[1] else rule.usage_limit(state, user_id)
        if limit is not None and usage.count(getattr(rule, 'usage_key', state.cards[card_id].definition_id)) >= limit:
            raise InvalidCardUse("card use limit reached")
        if not rule.can_use(state, user_id):
            raise InvalidCardUse("card's active-use condition is not met")
        return rule

    def validate_final(self, state: GameState, user_id: PlayerId, card_id: CardInstanceId, targets: tuple[PlayerId, ...]) -> CardRule:
        rule = self.validate_card(state, user_id, card_id)
        self.validate_targets_for_card(rule, state, user_id, card_id, targets)
        return rule

    def can_offer(self, state: GameState, user_id: PlayerId, card_id: CardInstanceId) -> bool:
        try:
            rule = self.validate_card(state, user_id, card_id)
            return not rule.requires_target_selection or bool(self.target_candidates(state, user_id, card_id))
        except InvalidCardUse:
            return False
