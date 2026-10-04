import asyncio
import json
from types import SimpleNamespace
from test_t9_2_cloudflare_game_room import worker_module
from sanguosha.engine.events import CardMovedEvent, DyingRequiredEvent, TurnStartedEvent, Event
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.multiplayer.room import MultiplayerRoom

def test_public_presentation_never_leaks_card_ids_in_discard_event_identity():
    room = MultiplayerRoom()
    event = CardMovedEvent('move:hidden-card', ('hidden-card',), ZoneRef(ZoneType.HAND, 'p2'),
                          ZoneRef(ZoneType.DISCARD_PILE), 'discard', 'p2', None)
    public = room._public_event(event)
    assert public['count'] == 1
    assert 'hidden-card' not in json.dumps(public)
    assert room._public_event(DyingRequiredEvent('dying', 'p2', 0))['player_id'] == 'p2'
    assert room._public_event(TurnStartedEvent('turn', 'p2', 3))['turn_number'] == 3
    assert room._public_event(Event('judgment', 'after_judgment', 'p2', metadata={'matched':True,'card_id':'secret'})) == {
        'kind':'JudgmentEvent','event_id':'judgment','source_id':'p2','matched':True}

def test_diagnostic_worker_ping_does_not_load_room_or_accept_decisions(worker_module,monkeypatch):
    do = object.__new__(worker_module.GameRoomDurableObject)
    messages=[]
    ws=SimpleNamespace(send=lambda payload:messages.append(json.loads(payload)))
    monkeypatch.setattr(worker_module,'_attachment',lambda _: {'diagnostic':True})
    async def run():
        await do.webSocketMessage(ws,json.dumps({'type':'PING'}))
        await do.webSocketMessage(ws,json.dumps({'type':'SUBMIT_DECISION','decision':{'value':'secret'}}))
        await do.webSocketMessage(ws,'[]')
        await do._disconnect(ws)
    asyncio.run(run())
    assert messages == [{'type':'PONG'}]
