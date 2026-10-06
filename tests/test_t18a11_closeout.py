"""Minimal reproductions of confirmed closeout product differences."""
import pytest
from test_t17c_jianyong_zongshi import game as pindian_game
from test_t17b_tier1 import answer
from test_t17c_first_batch import setup, restore
from test_t18a7_flow import room_for
from test_t6_military_basics import put
from sanguosha.engine.pindian import PindianAction
from sanguosha.engine.turns import TurnAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.events import Event, TurnStartedEvent
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.requests import RequestType
from sanguosha.model.enums import Phase
from sanguosha.projection import project_for_human
from sanguosha.snapshot import snapshot_session, restore_session


def test_pindian_public_faces_and_ownership_survive_reconnect():
    s,a,b=pindian_game(ranks=(7,7)); room=room_for(s)
    s.engine.start_action(PindianAction('close-compare','p1','p2'))
    answer(s,a)
    assert not any(isinstance(e,Event) and e.event_type=='pindian_revealed' for e in s.events.events)
    answer(s,b)
    event=next(e for e in s.events.events if isinstance(e,Event) and e.event_type=='pindian_revealed')
    public=room._public_event(event)
    assert public is not None
    assert public['source_id']=='p1' and public['target_ids']==['p2']
    assert [c['rank'] for c in public['cards']]==['7','7']
    assert public['card_owner_ids']==['p1','p2']
    room.session=restore_session(snapshot_session(s))
    view=room._named_projection(project_for_human(room.session.state,room.session.definitions,'p3',room.session.character_names),'p3')
    assert any(e.get('reason')=='pindian' and e['cards']==public['cards'] for e in view['public_card_history'])


@pytest.mark.parametrize('general,phase', [('wind_god_lvmeng',Phase.DRAW),('mountain_liushan',Phase.PLAY),('mountain_zhang_he',Phase.DISCARD)])
@pytest.mark.parametrize('marked',[False,True])
def test_already_skipped_phase_does_not_offer_replacement(general,phase,marked):
    s=setup('cao_zhang');s.state.players['p1'].character_id=general
    if marked:s.state.players['p1'].marks['skip_'+phase.value]=1
    s.engine.start_action(TurnAction('close-skip','p1',phases=(phase,),skipped_phases=frozenset() if marked else frozenset((phase,))))
    assert s.engine.pending_request is None
    assert s.engine.stack.is_empty()


@pytest.mark.parametrize('max_hp,hp',[(4,3),(1,1)])
def test_zhiji_max_hp_payment_precedes_reward(max_hp,hp):
    from sanguosha.engine.mountain import ZhijiAction
    from test_t17c_juece import empty
    s=setup('cao_zhang');p=s.state.players['p1'];p.character_id='mountain_jiang_wei'
    empty(s,'p1');p.max_hp=max_hp;p.hp=hp
    s.engine.start_action(ZhijiAction('close-zhiji','p1'))
    assert p.max_hp==max_hp-1
    if max_hp==1:
        assert not p.is_alive and s.engine.pending_request is None
    else:
        assert s.engine.pending_request.choices==('draw',)
        s=restore(s);answer(s,'draw')
        assert s.skills.has(s.state,'p1','guanxing')
        s.engine.start_action(ZhijiAction('close-zhiji-repeat','p1'))
        assert s.state.players['p1'].max_hp==max_hp-1



def test_nested_extra_turn_precedes_already_pending_extra_turn():
    from sanguosha.engine.turn_order import queue_extra_turn, next_scheduled_player
    s=setup('cao_zhang');s.state.current_player_id='p1'
    queue_extra_turn(s.state,'p3');queue_extra_turn(s.state,'p4')
    assert next_scheduled_player(s.state)=='p3'
    s.state.current_player_id='p3';queue_extra_turn(s.state,'p5')
    s=restore_session(snapshot_session(s))
    assert next_scheduled_player(s.state)=='p5'
    s.state.current_player_id='p5'
    assert next_scheduled_player(s.state)=='p4'
    s.state.current_player_id='p4'
    assert next_scheduled_player(s.state)=='p2'



@pytest.mark.parametrize('skip_finish',[False,True])
def test_fangquan_cost_offer_is_at_turn_end_even_if_finish_is_skipped(skip_finish):
    from sanguosha.engine.events import PhaseEndedEvent, PhaseSkippedEvent
    s=setup('cao_zhang');s.state.players['p1'].character_id='mountain_liushan'
    s.engine.start_action(TurnAction('close-fangquan','p1',phases=(Phase.PLAY,Phase.FINISH),skipped_phases=frozenset((Phase.FINISH,)) if skip_finish else frozenset()))
    answer(s,True)
    assert s.engine.pending_request is not None and '弃置一张手牌' in s.engine.pending_request.prompt
    assert s.state.current_phase is None
    expected=PhaseSkippedEvent if skip_finish else PhaseEndedEvent
    assert any(isinstance(e,expected) and e.phase is Phase.FINISH for e in s.events.events)
    s=restore(s);answer(s,False)
    assert s.engine.pending_request is None
