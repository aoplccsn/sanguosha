"""Twenty complete seeded standard matches verify roster and stack integrity."""

from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession


def test_seed_1_to_20_drafted_matches_resolve_without_residue():
    assignments = set()
    seen_generals = set()
    for seed in range(1, 21):
        setup = Pregame.create(seed)
        setup.acknowledge_identity()
        setup.timeout()
        session = GameSession.new_game(military=True, setup=setup)
        assignments.add(tuple(setup.generals.values()))
        seen_generals.update(setup.generals.values())
        for _ in range(12000):
            if session.state.status is GameStatus.FINISHED:
                break
            request = session.engine.pending_request
            if request is not None and request.player_id == session.human_id:
                session.submit_human(session.ai.decide(session.state, request))
            elif not session.step_auto():
                break
        assert session.state.status is GameStatus.FINISHED, seed
        assert session.engine.pending_request is None, seed
        assert session.engine.stack.is_empty(), seed
        assert not session.state.cards_in(ZoneRef(ZoneType.PROCESSING)), seed
        session.state.__post_init__()
    assert len(assignments) > 1
    assert len(seen_generals) == 25
