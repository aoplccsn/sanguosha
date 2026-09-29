from sanguosha.engine.requests import Decision
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_tricks import NullificationWindow
from sanguosha.model.enums import Phase
from sanguosha.model.usage import PlayUsageState
from sanguosha.multiplayer.protocol import serialize_request
from test_t8_network_chains import configure, decide
from test_t6_military_basics import put
import json
import pytest


def test_snapshot_continuation():
    setup = Pregame.create(17)
    setup.acknowledge_identity()
    request = setup.pending_request
    setup.submit(Decision(request.request_id, request.player_id, request.choices[0]))
    original = GameSession.new_game(military=True, setup=setup)
    original.step_auto()
    assert original.engine.pending_request is not None
    restored = restore_session(snapshot_session(original))
    assert snapshot_session(original) == snapshot_session(restored)

    for _ in range(70):
        for session in (original, restored):
            request = session.engine.pending_request
            if request is None:
                session.step_auto()
            else:
                session.engine.submit_decision(session.ai.decide(session.state, request))
        assert snapshot_session(original) == snapshot_session(restored)
        restored = restore_session(snapshot_session(restored))


@pytest.mark.parametrize("case", [
    "slash_dodge", "eight_trigrams", "nullification_chain", "duel",
    "iron_chain", "amazing_grace", "dying_peaches", "wushuang",
    "hujia", "jijiang", "skill_trigger",
])
def test_nested_resolution_snapshot(case):
    continuous = GameSession.new_game(seed=6, military=True, five_generals=True)
    action, facts = configure(case, continuous)
    continuous.engine.start_action(action)
    resumed = restore_session(snapshot_session(continuous))

    for _ in range(100):
        assert snapshot_session(continuous) == snapshot_session(resumed)
        if not any(frame.action.action_id == action.action_id for frame in continuous.engine.stack.snapshot()):
            break
        request = continuous.engine.pending_request
        assert request is not None
        value = decide(case, serialize_request(request, 30000), facts)
        decision = Decision(request.request_id, request.player_id, value)
        continuous.engine.submit_decision(decision)
        resumed.engine.submit_decision(decision)
        resumed = restore_session(snapshot_session(resumed))
    else:
        raise AssertionError(f"{case} did not finish")
    assert snapshot_session(continuous) == snapshot_session(resumed)


def test_trick_nullification_window_restores():
    continuous = GameSession.new_game(seed=6, military=True, five_generals=True)
    state = continuous.state
    state.current_player_id = "p1"
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState("p1", 1)
    trick = put(continuous, "trick.duel")
    counter = put(continuous, "trick.nullification", "p2")
    continuous.engine.start_action(UseCardAction("snapshot-trick", "p1", trick, ("p3",)))
    resumed = restore_session(snapshot_session(continuous))
    saw_window = False
    used_counter = False
    for _ in range(100):
        assert snapshot_session(continuous) == snapshot_session(resumed)
        request = continuous.engine.pending_request
        if request is None:
            break
        saw_window |= any(isinstance(frame.action, NullificationWindow) for frame in continuous.engine.stack.snapshot())
        value = counter if not used_counter and counter in request.eligible_card_ids else request.timeout_value()
        used_counter |= value == counter
        decision = Decision(request.request_id, request.player_id, value)
        continuous.engine.submit_decision(decision)
        resumed.engine.submit_decision(decision)
        resumed = restore_session(snapshot_session(resumed))
    assert saw_window and used_counter
    assert snapshot_session(continuous) == snapshot_session(resumed)


def test_snapshot_version_mismatch_fails_explicitly():
    session = GameSession.new_game(seed=1)
    data = json.loads(snapshot_session(session))
    data["schema_version"] = 999
    with pytest.raises(ValueError, match="incompatible GameSnapshot schema"):
        restore_session(json.dumps(data).encode())
