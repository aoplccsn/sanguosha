"""Room response UX keeps authoritative legality for physical and ViewAs cards."""

from types import SimpleNamespace

import pytest

from sanguosha.engine.requests import Decision, PASS_RESPONSE, PendingRequest, RequestType
from sanguosha.model.state import GameStatus
from sanguosha.multiplayer.room import MultiplayerRoom


@pytest.mark.parametrize("eligible,auto_pass", [
    ((), True),
    (("card-dodge",), False),
    (("virtual:kanpo:black-card",), False),
    (("virtual:longhun:card-a",), False),
])
def test_room_skips_only_pass_only_human_responses(eligible, auto_pass):
    room = MultiplayerRoom()
    player, _ = room.join("human", lambda _: None)
    request = PendingRequest("response-1", player, RequestType.RESPOND_WITH_CARD,
                             "Respond", "action", "frame", eligible_card_ids=eligible,
                             allow_pass=True)
    submitted: list[Decision] = []
    dispatched: list[PendingRequest] = []
    engine = SimpleNamespace(pending_request=request)

    def submit(decision):
        submitted.append(decision)
        engine.pending_request = None

    engine.submit_decision = submit
    room.session = SimpleNamespace(state=SimpleNamespace(status=GameStatus.ACTIVE, metadata={}, turn_number=0), engine=engine,
                                   step_auto=lambda: None,
                                   clear_finished_nullification_windows=lambda: None,
                                   nullification_window_id=lambda request: None)
    room.network_decisions.dispatch = dispatched.append
    room.suspend_on_budget = True
    room.pump(max_steps=1)
    if auto_pass:
        assert submitted == [Decision("response-1", player, PASS_RESPONSE)]
        assert not dispatched
    else:
        assert dispatched == [request]
        assert not submitted
