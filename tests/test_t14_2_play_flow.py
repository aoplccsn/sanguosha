"""A physical card and its targets commit in one authoritative decision."""

import pytest

from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import Phase
from sanguosha.multiplayer.protocol import decision_from_wire, decision_to_wire, serialize_request
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
from sanguosha.room_snapshot import snapshot_room, restore_room
from sanguosha.engine.errors import InvalidDecision
from sanguosha.model.zones import ZoneRef, ZoneType

from test_t6_military_basics import game, put


@pytest.mark.parametrize("definition,target", [
    ("basic.slash", "p2"),
    ("trick.duel", "p2"),
    ("equipment.horse.dilu", None),
])
def test_card_target_confirm_is_one_decision(definition, target):
    session = game()
    card_id = put(session, definition)
    session.engine.start_action(PhaseAction("play-flow", "p1", Phase.PLAY))
    request = session.engine.pending_request
    assert request is not None
    option = f"use:{card_id}"
    assert option in request.choices
    spec = request.play_card_targets[option]
    assert spec[1] == (1 if target else 0)
    assert target is None or target in spec[0]
    assert option in serialize_request(request, 60000)["play_card_targets"]
    wire = {"request_id": request.request_id,
            "value": {"option": option, "targets": [target] if target else []}}
    decision = decision_from_wire(wire, "p1")
    assert decision_to_wire(decision) == wire
    session.engine.submit_decision(decision)
    next_request = session.engine.pending_request
    assert next_request is None or not next_request.request_id.endswith(":target")


def test_invalid_combined_target_is_rejected_before_engine_accepts():
    session = game()
    card_id = put(session, "basic.slash")
    session.engine.start_action(PhaseAction("play-flow-invalid", "p1", Phase.PLAY))
    request = session.engine.pending_request
    with pytest.raises(InvalidDecision):
        request.validate({"option": f"use:{card_id}", "targets": ("p1",)})
    assert session.engine.pending_request is request


def test_room_accept_does_not_run_resolution_and_snapshot_can_resume(monkeypatch):
    messages = []
    room = MultiplayerRoom()
    pid, _ = room.join('host', messages.append)
    room.session = game()
    room.phase = RoomPhase.IN_GAME
    cid = put(room.session, 'equipment.horse.dilu')
    room.session.engine.start_action(PhaseAction('deferred-play', pid, Phase.PLAY))
    request = room.session.engine.pending_request
    room.network_decisions.dispatch(request)
    def cannot_run():
        raise AssertionError('resolution must not run during accept')
    monkeypatch.setattr(room.session.engine, 'run_until_blocked', cannot_run)
    room.submit(pid, Decision(request.request_id, pid,
                {'option': f'use:{cid}', 'targets': ()}), defer_resolution=True)
    assert room.session.engine.pending_request is None
    assert room.request_deadline is None
    assert room.accepted_request_id == request.request_id
    assert any(message['type'] == 'DECISION_RESULT' for message in messages)
    restored = restore_room(snapshot_room(room))
    restored.seats[pid].connected = True
    restored.resolve_accepted()
    assert restored.accepted_request_id is None
    assert cid not in restored.session.state.cards_in(ZoneRef(ZoneType.HAND, pid))
