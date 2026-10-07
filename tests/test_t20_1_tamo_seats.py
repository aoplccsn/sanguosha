"""T20.1: 榻谟 changes the authoritative ring used by rules and projections."""

from dataclasses import asdict

import pytest

from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.events import TurnStartedEvent
from sanguosha.engine.military_tricks import MilitaryTrickRule
from sanguosha.engine.mobile_gods import MobileGodAction
from sanguosha.engine.turn_order import next_alive_player, next_scheduled_player
from sanguosha.engine.turns import TurnAction
from sanguosha.game_modes import game_mode
from sanguosha.model.enums import EquipmentSlot, Identity, Phase
from sanguosha.model.zones import ZoneType
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.projection import project_for_human
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from test_t17b_tier1 import answer
from test_t6_military_basics import put


CASES = [
    ('military-five', ('p5', 'p4', 'p1', 'p2'), ('p1', 'p2', 'p3', 'p5', 'p4')),
    ('military-eight', ('p6', 'p4', 'p8', 'p1', 'p7', 'p2', 'p5'),
     ('p2', 'p5', 'p3', 'p6', 'p4', 'p8', 'p1', 'p7')),
]


def identity_game(mode):
    setup = Pregame.create(192, mode)
    lord = setup.lord_id
    setup.identities[lord], setup.identities['p3'] = setup.identities['p3'], Identity.LORD
    generals = ('sunquan', 'caocao', 'liubei', 'mobile_god_lusu',
                'simayi', 'zhangliao', 'zhaoyun', 'huangyueying')
    setup.generals = dict(zip(game_mode(mode).seats, generals))
    setup.stage = SetupStage.COMPLETE
    return GameSession.new_game(seed=192, military=True, setup=setup)


def player_owned_state(session):
    return {
        pid: ({key: value for key, value in asdict(player).items() if key != 'seat'},
              {ref: tuple(zone.card_ids) for ref, zone in session.state.zones.items()
               if ref.player_id == pid})
        for pid, player in session.state.players.items()
    }


@pytest.mark.parametrize('mode,chosen,expected', CASES)
def test_tamo_authoritative_seats_distance_and_reconnect_projection(mode, chosen, expected):
    session = identity_game(mode)
    state = session.state
    for index, player in enumerate(state.players.values()):
        player.hp = 1 + index % 3
        player.marks['tamo-owner'] = index + 1
    put(session, 'equipment.horse.chitu', 'p4', ZoneType.EQUIPMENT, EquipmentSlot.OFFENSIVE_HORSE)
    put(session, 'equipment.horse.jueying', chosen[0], ZoneType.EQUIPMENT, EquipmentSlot.DEFENSIVE_HORSE)
    put(session, 'equipment.weapon.qinggang_sword', 'p4', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    owned = player_owned_state(session)
    distance = DistanceSystem(session.definitions)
    assert distance.base_distance(state, 'p3', 'p4') == 1
    session.engine.start_action(MobileGodAction('t20.1:tamo', 'p4', 'tamo'))
    answer(session, True)
    assert set(session.engine.pending_request.allowed_player_ids) == set(chosen)
    answer(session, chosen)

    assert session.engine.pending_request is None
    assert state.seat_order == expected
    assert state.players['p3'].seat == 2
    assert state.players['p3'].identity is Identity.LORD
    assert {pid: player.seat for pid, player in state.players.items()} == {
        pid: index for index, pid in enumerate(expected)
    }
    assert player_owned_state(session) == owned
    state.__post_init__()
    clockwise = ('p3', *chosen)
    assert tuple(next_alive_player(state, pid) for pid in clockwise) == clockwise[1:] + clockwise[:1]
    assert distance.base_distance(state, 'p3', 'p4') == 2
    for i, source in enumerate(expected):
        for j, target in enumerate(expected):
            if source == target:
                continue
            base = min(abs(i - j), len(expected) - abs(i - j))
            effective = max(1, base - int(source == 'p4') + int(target == chosen[0]))
            assert distance.base_distance(state, source, target) == base
            assert distance.distance_between(state, source, target) == effective
    assert distance.attack_range(state, 'p4') == 2
    assert tuple(pid for pid in expected if pid != 'p4' and distance.can_reach_with_slash(state, 'p4', pid)) == tuple(
        pid for pid in expected if pid != 'p4' and distance.distance_between(state, 'p4', pid) <= 2
    )
    snatch = MilitaryTrickRule('trick.snatch', distance, session.skills)
    assert snatch.target_candidates(state, 'p4') == tuple(
        pid for pid in expected if pid != 'p4' and distance.distance_between(state, 'p4', pid) <= 1
    )

    restored = restore_session(snapshot_session(session))
    assert restored.state.seat_order == expected
    assert player_owned_state(restored) == owned
    for viewer in expected:
        view = project_for_human(restored.state, restored.definitions, viewer, restored.character_names)
        assert tuple(player.player_id for player in view.players) == expected
        assert len({player.player_id for player in view.players}) == len(expected)
        assert view == project_for_human(state, session.definitions, viewer, session.character_names)


@pytest.mark.parametrize('mode,chosen,expected', CASES)
def test_tamo_finishes_before_first_turn_and_uses_final_clockwise_order(mode, chosen, expected):
    session = identity_game(mode)
    session.engine.start_action(TurnAction('t20.1:first', next_scheduled_player(session.state),
                                          phases=(Phase.PREPARATION,)))
    # The god-general faction choice precedes the opening 榻谟 window.
    while ':tamo:' not in session.engine.pending_request.request_id:
        answer(session, session.engine.pending_request.timeout_value())
    assert session.state.turn_number == 0
    assert session.state.current_player_id is None
    assert not any(isinstance(event, TurnStartedEvent) for event in session.events.events)
    answer(session, True)
    assert session.state.turn_number == 0
    answer(session, chosen)
    assert session.state.seat_order == expected
    assert session.state.current_player_id == 'p3'
    assert session.state.turn_number == 1

    for index, pid in enumerate(chosen, start=2):
        assert next_scheduled_player(session.state) == pid
        session.engine.start_action(TurnAction(f't20.1:turn-{index}', pid, phases=(Phase.PREPARATION,)))
        while session.engine.pending_request is not None:
            answer(session, session.engine.pending_request.timeout_value())
    turns = tuple(event for event in session.events.events if isinstance(event, TurnStartedEvent))
    assert tuple(event.player_id for event in turns) == ('p3', *chosen)
    assert tuple(event.turn_number for event in turns) == tuple(range(1, len(expected) + 1))
    assert next_scheduled_player(session.state) == 'p3'
