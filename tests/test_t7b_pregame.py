"""T7-B setup invariants, independent of animation or Qt timers."""

from collections import Counter

import pytest

from sanguosha.content.characters.standard import STANDARD_25_GENERAL_POOL, PLAYABLE_GENERAL_POOL
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import Gender, Identity
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.session import GameSession


def test_standard_roster_has_25_unique_classic_characters_and_gender():
    assert len(STANDARD_25_GENERAL_POOL) == 25
    assert len({general.id for general in STANDARD_25_GENERAL_POOL}) == 25
    assert all(general.gender in (Gender.MALE, Gender.FEMALE) for general in STANDARD_25_GENERAL_POOL)


def test_seeded_roles_candidates_and_ai_draft_across_twenty_seeds():
    human_roles = set()
    pool = {general.id for general in PLAYABLE_GENERAL_POOL}
    for seed in range(1, 21):
        first, second = Pregame.create(seed), Pregame.create(seed)
        assert first.identities == second.identities
        assert first.candidates == second.candidates
        assert Counter(first.identities.values()) == Counter({
            Identity.LORD: 1, Identity.LOYALIST: 1,
            Identity.REBEL: 2, Identity.RENEGADE: 1,
        })
        assert len(first.candidates) == len(set(first.candidates)) == 10
        assert set(first.candidates) <= pool
        human_roles.add(first.human_identity)
        for setup in (first, second):
            setup.acknowledge_identity()
            request = setup.pending_request
            setup.submit(Decision(request.request_id, setup.human_id, setup.candidates[3]))
            assert setup.stage is SetupStage.COMPLETE
            assert len(set(setup.generals.values())) == 5
        assert first.generals == second.generals
    assert len(human_roles) > 1


def test_choice_requires_identity_reveal_and_explicit_confirmation():
    setup = Pregame.create(4)
    assert setup.pending_request is None
    with pytest.raises(ValueError):
        setup.timeout()
    setup.acknowledge_identity()
    request = setup.pending_request
    assert not setup.generals
    with pytest.raises(ValueError):
        setup.submit(Decision('wrong-request', setup.human_id, setup.candidates[0]))
    with pytest.raises(Exception):
        setup.submit(Decision(request.request_id, setup.human_id, 'nonstandard-general'))
    assert not setup.generals
    setup.timeout()
    assert setup.generals[setup.human_id] == setup.candidates[0]


def test_completed_setup_reveals_only_lord_and_starts_from_lord():
    setup = next(Pregame.create(seed) for seed in range(1, 21)
                 if Pregame.create(seed).lord_id != Pregame.create(seed).human_id)
    setup.acknowledge_identity()
    setup.timeout()
    session = GameSession.new_game(military=True, setup=setup)
    assert session.state.revealed_identities == {setup.lord_id}
    assert session.state.players[setup.human_id].identity == setup.human_identity
    assert {pid: player.character_id for pid, player in session.state.players.items()} == setup.generals
    assert session.state.current_player_id is None
    session.step_auto()
    assert session.state.current_player_id == setup.lord_id
