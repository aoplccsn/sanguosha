from types import SimpleNamespace
import pytest
from sanguosha.game_modes import game_mode
from sanguosha.pregame import SetupStage
from sanguosha.engine.rng import PythonRandomSource
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session,snapshot_session

@pytest.mark.parametrize('mode_id',['military-five','military-eight'])
@pytest.mark.parametrize('seat',['p1','p2'])
def test_ganning_initial_three_six_plus_existing_lord_bonus(mode_id,seat):
    mode=game_mode(mode_id)
    generals={pid:'sunquan' for pid in mode.seats};generals[seat]='thunder_god_ganning'
    setup=SimpleNamespace(stage=SetupStage.COMPLETE,rng=PythonRandomSource(7),mode_id=mode_id,
        identities=dict(zip(mode.seats,mode.roles)),generals=generals,lord_id='p1')
    s=GameSession.new_game(military=True,setup=setup)
    p=s.state.players[seat];bonus=mode.lord_hp_bonus if seat=='p1' else 0
    assert (p.hp,p.max_hp)==(3+bonus,6+bonus)
    s=restore_session(snapshot_session(s));p=s.state.players[seat]
    assert (p.hp,p.max_hp)==(3+bonus,6+bonus)
    assert len(s.state.players)==mode.seat_count
