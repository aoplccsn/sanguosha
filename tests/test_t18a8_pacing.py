"""Room deadlines preserve readable turns without delaying human requests."""
from dataclasses import replace
from sanguosha.decisions.ai import AIDecisionProvider
from sanguosha.multiplayer.room import Controller, RoomPhase, MultiplayerRoom
from sanguosha.engine.events import DamageDealtEvent, HpRecoveredEvent
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import Identity
from sanguosha.room_snapshot import snapshot_room, restore_room
from test_t6_military_basics import game, put

def test_ai_targeting_is_invariant_to_hidden_identities_and_cards():
    s=game();ai=AIDecisionProvider('human');s.state.revealed_identities={'p1'}
    s.state.players['p1'].identity=Identity.LORD
    baseline=[ai._target_score(s.state,'p1',p) for p in ('p2','p3','p4','p5')]
    for pid in ('p2','p3','p4','p5'):s.state.players[pid].identity=Identity.REBEL
    assert baseline==[ai._target_score(s.state,'p1',p) for p in ('p2','p3','p4','p5')]
    ai.observe_public_events(s.state,[DamageDealtEvent('attack','p2','p1',1,3),HpRecoveredEvent('save','p3','p1',1,4)])
    assert ai._priority(s.state,'p1','p2')>ai._priority(s.state,'p1','p3')
    before=s.state.metadata['public_attitude'].copy()
    ai.observe_public_events(s.state,[DamageDealtEvent('attack','p2','p1',1,3),HpRecoveredEvent('save','p3','p1',1,4)])
    assert s.state.metadata['public_attitude']==before

def test_human_response_dispatches_during_action_dwell(monkeypatch):
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:1000.)
    s=game();room=MultiplayerRoom();room.session=s;room.phase=RoomPhase.IN_GAME;room.ai_presentation=True
    messages=[]
    for seat in room.seats.values():seat.controller=Controller.AI
    seat=room.seats['p2'];seat.controller=Controller.HUMAN;seat.connected=True;seat.send=messages.append
    put(s,'basic.dodge','p2');s.engine.start_action(UseCardAction('attack','p1',put(s,'basic.slash'),('p2',)))
    room.presentation_deadline=1004.5;room.pump()
    assert room.presentation_deadline==1004.5
    assert any(m['type']=='PENDING_REQUEST' for m in messages)
    assert room.request_deadline==1060.

def test_fully_skipped_ai_turn_has_observation_window_and_snapshot(monkeypatch):
    clock=[1000.];monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:clock[0])
    s=game();room=MultiplayerRoom();room.session=s;room.phase=RoomPhase.IN_GAME;room.ai_presentation=True
    for seat in room.seats.values():seat.controller=Controller.AI
    for player in s.state.players.values():player.face_up=False
    room.pump();actor=s.state.current_player_id
    assert room.presentation_deadline==clock[0]+5.5
    restored=restore_room(snapshot_room(room));assert restored.turn_visible_until==room.turn_visible_until
    clock[0]+=5.4;room.pump();assert s.state.current_player_id==actor
    clock[0]+=.2;room.poll();assert s.state.current_player_id!=actor

def test_expired_dwell_clears_while_human_prompt_remains_actionable(monkeypatch):
    clock=[1000.];monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:clock[0])
    s=game();room=MultiplayerRoom();room.session=s;room.phase=RoomPhase.IN_GAME
    for seat in room.seats.values():seat.controller=Controller.HUMAN;seat.connected=True
    put(s,'basic.dodge','p2');s.engine.start_action(UseCardAction('attack','p1',put(s,'basic.slash'),('p2',)))
    room.presentation_deadline=1004.5;room.pump();request=s.engine.pending_request
    clock[0]=1005.;room.poll()
    assert room.presentation_deadline is None and s.engine.pending_request is request

def test_root_trick_pass_preference_is_respected_during_presentation(monkeypatch):
    from sanguosha.engine.requests import RequestType
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:1000.)
    s=game();room=MultiplayerRoom();room.session=s;room.phase=RoomPhase.IN_GAME
    for seat in room.seats.values():seat.controller=Controller.HUMAN;seat.connected=True
    put(s,'trick.nullification','p1');put(s,'trick.nullification','p2')
    s.engine.start_action(UseCardAction('root','p1',put(s,'trick.savage_assault')))
    request=s.engine.pending_request;root=s.nullification_window_id(request)
    s.state.metadata['nullification_passes']={root:['p1']}
    room.presentation_deadline=1004.5;room.pump()
    assert s.engine.pending_request.player_id=='p2'
    assert room._last_request_id==s.engine.pending_request.request_id

from test_t9_2_cloudflare_game_room import worker_module

def test_worker_alarm_schedules_action_dwell_before_human_timeout(worker_module):
    import asyncio
    from types import SimpleNamespace
    alarms=[]
    class Storage:
        async def setAlarm(self, value):alarms.append(value)
    do=object.__new__(worker_module.GameRoomDurableObject)
    do.room=MultiplayerRoom();do.room.presentation_deadline=1004.5;do.room.request_deadline=1060.
    do.ctx=SimpleNamespace(storage=Storage());do.env=SimpleNamespace(ROOM_TTL_SECONDS='7200')
    asyncio.run(do._schedule_alarm(1000000))
    assert alarms==[1004500]
