import pytest

from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.engine.mobile_gods import MobileGodAction
from sanguosha.game_modes import game_mode
from sanguosha.model.enums import Identity
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from test_t17b_tier1 import answer


@pytest.mark.parametrize('mode', ['military-five', 'military-eight'])
def test_tamo_full_nonlord_order_including_actor_after_reconnect(mode):
    setup = Pregame.create(192, mode)
    seats = game_mode(mode).seats
    actor = next(pid for pid in seats if setup.identities[pid] is not Identity.LORD)
    others = (c.id for c in PLAYABLE_GENERAL_POOL if c.id != 'mobile_god_lusu')
    setup.generals = {pid: 'mobile_god_lusu' if pid == actor else next(others) for pid in seats}
    setup.stage = SetupStage.COMPLETE
    session = GameSession.new_game(seed=192, military=True, setup=setup)
    before = tuple(session.state.seat_order)
    nonlords = tuple(pid for pid in before if session.state.players[pid].identity is not Identity.LORD)
    lord = next(pid for pid in before if pid not in nonlords)
    session.engine.start_action(MobileGodAction('tamo:real', actor, 'tamo'))
    answer(session, True)
    request = session.engine.pending_request
    assert len(request.allowed_player_ids) == len(seats) - 1
    assert actor in request.allowed_player_ids
    assert set(request.allowed_player_ids) == set(nonlords)
    session = restore_session(snapshot_session(session))
    assert session.engine.pending_request == request
    answer(session, tuple(reversed(nonlords)))
    assert session.engine.pending_request is None
    assert session.state.seat_order[before.index(lord)] == lord
    lord_index = session.state.seat_order.index(lord)
    clockwise = tuple(session.state.seat_order[(lord_index + offset) % len(seats)]
                      for offset in range(1, len(seats)))
    assert clockwise == tuple(reversed(nonlords))
