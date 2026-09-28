from sanguosha.content.cards.classic_military import register_additional_definitions
from sanguosha.engine.card_moves import CardMoveService
from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.engine.card_rules import CardRuleRegistry, CardUseValidator, TargetValidator
from sanguosha.engine.card_use import UseCardAction, UseCardActionHandler
from sanguosha.engine.engine import EngineStatus, GameEngine
from sanguosha.engine.equipment import EquipCardAction, EquipCardHandler
from sanguosha.engine.equipment import register_equipment_rules
from sanguosha.engine.events import EventRecorder
from sanguosha.engine.registry import ActionHandlerRegistry
from sanguosha.engine.resolution import ResolutionFrame
from sanguosha.model.card import CardInstance
from sanguosha.model.enums import EquipmentSlot, Identity, Phase, Suit
from sanguosha.model.ids import CardInstanceId, CharacterId, PlayerId
from sanguosha.model.player import PlayerState
from sanguosha.model.state import GameState
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType


def test_equipment_replaces_old_card_through_move_service():
    player_id = PlayerId('p1')
    old_id, new_id = CardInstanceId('old'), CardInstanceId('new')
    old_def = 'equipment.weapon.double_sword'
    new_def = 'equipment.weapon.qinggang_sword'
    slot = ZoneRef(ZoneType.EQUIPMENT, player_id, EquipmentSlot.WEAPON)
    processing = ZoneRef(ZoneType.PROCESSING)
    cards = {
        old_id: CardInstance(old_id, old_def, Suit.SPADE, 2),
        new_id: CardInstance(new_id, new_def, Suit.SPADE, 6),
    }
    state = GameState('t6-test', {player_id: PlayerState(player_id, 0, CharacterId('test'),
                                                         Identity.LORD, 4, 4)}, (player_id,), cards,
                      {slot: CardZone(slot, [old_id]), processing: CardZone(processing, [new_id])})
    definitions = CardDefinitionRegistry()
    register_additional_definitions(definitions)
    events = EventRecorder()
    action = EquipCardAction('equip-1', player_id, new_id)
    EquipCardHandler(CardMoveService(events), definitions).step(state, ResolutionFrame('frame-1', action))
    assert state.cards_in(slot) == (new_id,)
    assert state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) == (old_id,)
    assert not state.cards_in(processing)
    assert len(events.events) == 2


def test_equipment_full_use_lifecycle_leaves_no_processing_card():
    player_id = PlayerId('p1')
    card_id = CardInstanceId('new')
    hand = ZoneRef(ZoneType.HAND, player_id)
    slot = ZoneRef(ZoneType.EQUIPMENT, player_id, EquipmentSlot.WEAPON)
    state = GameState('t6-test', {player_id: PlayerState(player_id, 0, CharacterId('test'),
                                                         Identity.LORD, 4, 4)}, (player_id,),
                      {card_id: CardInstance(card_id, 'equipment.weapon.crossbow', Suit.CLUB, 1)},
                      {hand: CardZone(hand, [card_id])}, current_player_id=player_id,
                      current_phase=Phase.PLAY, turn_number=1,
                      play_usage=PlayUsageState(player_id, 1))
    definitions = CardDefinitionRegistry()
    register_additional_definitions(definitions)
    rules = CardRuleRegistry()
    register_equipment_rules(definitions, rules)
    events = EventRecorder()
    moves = CardMoveService(events)
    registry = ActionHandlerRegistry()
    registry.register(UseCardAction, UseCardActionHandler(CardUseValidator(definitions, rules, TargetValidator()), moves, events))
    registry.register(EquipCardAction, EquipCardHandler(moves, definitions))
    engine = GameEngine(state, registry)
    assert engine.start_action(UseCardAction('use-crossbow', player_id, card_id)) is EngineStatus.COMPLETED
    assert state.cards_in(slot) == (card_id,)
    assert not state.cards_in(ZoneRef(ZoneType.PROCESSING))
    assert not state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
