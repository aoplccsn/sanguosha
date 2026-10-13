"""Official Ju Shou initial shield, HP payment and lost-HP distinctions."""
from sanguosha.session import GameSession
from sanguosha.pregame import Pregame,SetupStage
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.hp import LoseHpAction
from sanguosha.engine.events import DamageDealtEvent
from sanguosha.snapshot import snapshot_session,restore_session
from sanguosha.projection import project_for_human
from test_t22_combat import drain

def prepared():
    setup=Pregame.create(2213,'military-five')
    setup.generals={q:('boundary_ju_shou' if q=='p2' else 'sunquan') for q in setup.identities}
    setup.stage=SetupStage.COMPLETE
    return GameSession.new_game(military=True,setup=setup)

def test_official_initial_hp_shield_projection_and_reconnect():
    s=prepared();p=s.state.players['p2']
    assert (p.hp,p.max_hp,p.marks['shield'])==(2,3,3)
    s=restore_session(snapshot_session(s))
    view=project_for_human(s.state,s.definitions,'p1',s.character_names)
    assert next(p for p in view.players if p.player_id=='p2').marks['shield']==3

def test_shield_reduces_hp_payment_but_damage_events_and_shibei_count_packets():
    s=prepared()
    s.engine.start_action(MilitaryDamageAction('first','p1','p2',1));drain(s)
    assert s.state.players['p2'].marks['shield']==2
    assert s.state.players['p2'].hp==3
    s=restore_session(snapshot_session(s))
    s.engine.start_action(MilitaryDamageAction('second','p1','p2',1));drain(s)
    assert s.state.players['p2'].marks['shield']==1
    assert s.state.players['p2'].hp==2
    events=[e for e in s.events.events if isinstance(e,DamageDealtEvent)]
    assert [e.amount for e in events]==[1,1]

def test_lost_hp_bypasses_shield_and_does_not_trigger_shibei():
    s=prepared();before=len(s.events.events)
    s.engine.start_action(LoseHpAction('lost','p2',1));drain(s)
    assert s.state.players['p2'].hp==1 and s.state.players['p2'].marks['shield']==3
    assert not any(isinstance(e,DamageDealtEvent) for e in s.events.events[before:])
