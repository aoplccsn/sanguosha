"""Repeatable full-game acceptance for the current roster and AI."""
import random

import pytest

from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.decisions.ai import AIDecisionProvider
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.session import GameSession


@pytest.mark.parametrize('mode', ['military-five', 'military-eight'])
@pytest.mark.parametrize('seed', range(20))
def test_current_roster_ai_full_game(mode, seed, monkeypatch):
    setup = Pregame.create(seed, mode)
    seats = tuple(setup.identities)
    setup.generals = dict(zip(seats, random.Random(seed).sample(
        [general.id for general in PLAYABLE_GENERAL_POOL], len(seats))))
    setup.stage = SetupStage.COMPLETE
    session = GameSession.new_game(military=True, setup=setup)
    session.human_id = 'automated'
    seen = set()
    original = AIDecisionProvider.decide

    def decide_once(provider, state, request, **kwargs):
        assert request.request_id not in seen, 'AI decision repeated'
        seen.add(request.request_id)
        decision = original(provider, state, request, **kwargs)
        request.validate(decision.value)
        return decision

    monkeypatch.setattr(AIDecisionProvider, 'decide', decide_once)
    from sanguosha.multiplayer.room import MultiplayerRoom, Controller, RoomPhase
    clock = [1000.0]
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time', lambda: clock[0])
    room = MultiplayerRoom(mode_id=mode)
    room.session = session
    room.phase = RoomPhase.IN_GAME
    room.ai_presentation = True
    for seat in room.seats.values():
        seat.controller = Controller.AI
    room.pump()
    for _ in range(20_000):
        if room.phase is RoomPhase.FINISHED:
            break
        deadline = room.ai_deadline or room.presentation_deadline
        assert deadline is not None, 'AI progression stalled'
        clock[0] = deadline + .01
        room.poll()
    assert seen
    assert session.state.status.value == 'finished'
    assert session.state.victory is not None
    assert session.engine.pending_request is None
    assert session.engine.stack.is_empty()
    session.state.__post_init__()

def test_ai_thinking_wait_survives_snapshot_without_repeating_decision(monkeypatch):
    from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase, Controller
    from sanguosha.room_snapshot import snapshot_room, restore_room
    from sanguosha.engine.requests import Decision
    from test_t8_multiplayer import choose
    clock = [1000.0]
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time', lambda: clock[0])
    room = MultiplayerRoom(seed=3)
    p1, _ = room.join('local audit', lambda _: None)
    room.ai_presentation = True
    room.start(p1)
    request = room.draft_requests[p1]
    room.submit(p1, Decision(request.request_id, p1, request.choices[0]))
    calls = []
    original = AIDecisionProvider.decide
    def tracked(ai, state, request, **kwargs):
        calls.append(request.request_id)
        return original(ai, state, request, **kwargs)
    monkeypatch.setattr(AIDecisionProvider, 'decide', tracked)
    for _ in range(30):
        if room.ai_deadline is not None:
            break
        request = room.session.engine.pending_request
        assert request is not None and request.player_id == p1
        from sanguosha.multiplayer.protocol import serialize_request
        room.submit(p1, Decision(request.request_id, p1, choose(serialize_request(request,60000))))
    assert room.ai_deadline is not None
    pending = room.session.engine.pending_request
    assert room.seats[pending.player_id].controller is Controller.AI
    event = room.session.events.events[-1]
    public = room._public_event(event)
    assert public['kind'] == 'AIThinkingEvent'
    assert public['source_id'] == pending.player_id
    assert pending.request_id not in str(public)
    room.poll()
    room.pump()
    assert calls == []
    restored = restore_room(snapshot_room(room))
    assert restored.ai_deadline == room.ai_deadline
    assert restored._ai_wait_request == pending.request_id
    clock[0] = room.ai_deadline + .01
    restored.poll()
    assert calls.count(pending.request_id) == 1
    restored.poll()
    assert calls.count(pending.request_id) == 1
    assert len({e.event_id for e in restored.session.events.events}) == len(restored.session.events.events)
