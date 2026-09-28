from sanguosha.engine.card_moves import CardMoveService
from sanguosha.engine.engine import EngineStatus, GameEngine
from sanguosha.engine.events import EventRecorder
from sanguosha.engine.judgment import JudgmentAction, JudgmentHandler, JudgmentPattern
from sanguosha.engine.registry import ActionHandlerRegistry
from sanguosha.model.card import CardInstance
from sanguosha.model.enums import Identity, Suit
from sanguosha.model.ids import CardInstanceId, CharacterId, PlayerId
from sanguosha.model.player import PlayerState
from sanguosha.model.state import GameState
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType


def test_judgment_reveals_matches_and_discards_same_physical_card():
    player_id = PlayerId('p1')
    card_id = CardInstanceId('judgment-card')
    draw = ZoneRef(ZoneType.DRAW_PILE)
    state = GameState('t6-test', {player_id: PlayerState(player_id, 0, CharacterId('test'),
                                                         Identity.LORD, 4, 4)}, (player_id,),
                      {card_id: CardInstance(card_id, 'basic.slash', Suit.HEART, 7)},
                      {draw: CardZone(draw, [card_id])})
    events = EventRecorder()
    registry = ActionHandlerRegistry()
    registry.register(JudgmentAction, JudgmentHandler(CardMoveService(events), events))
    engine = GameEngine(state, registry)
    assert engine.start_action(JudgmentAction('judge-1', player_id, JudgmentPattern(suit=Suit.HEART))) is EngineStatus.COMPLETED
    assert engine.last_result is True
    assert state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) == (card_id,)
    assert not state.cards_in(ZoneRef(ZoneType.PROCESSING))
    assert [event.event_type for event in events.events if hasattr(event, 'event_type')] == [
        'before_judgment', 'judgment_card_revealed', 'judgment_result', 'after_judgment',
    ]
