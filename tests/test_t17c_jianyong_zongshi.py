from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.pindian import PindianAction
from sanguosha.engine.events import Event
from sanguosha.model.enums import Suit
from sanguosha.model.zones import ZoneRef,ZoneType


def game(owner='p1',ranks=(12,3)):
    s=setup('cao_zhang')
    for q in s.state.seat_order:empty(s,q)
    s.state.players[owner].character_id='yj2013_jian_yong'
    a=put(s,'basic.slash','p1');b=put(s,'basic.dodge','p2')
    s.state.cards[a]=replace(s.state.cards[a],rank=ranks[0]);s.state.cards[b]=replace(s.state.cards[b],rank=ranks[1])
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return s,a,b


@pytest.mark.parametrize('owner',['p1','p2'])
@pytest.mark.parametrize('ranks',[(12,3),(3,12),(7,7)])
def test_zongshi_each_pindian_side_win_loss_tie_before_discard_restore(owner,ranks):
    s,a,b=game(owner,ranks);s.engine.start_action(PindianAction('compare','p1','p2'));s=restore(s)
    answer(s,a);s=restore(s);answer(s,b);s=restore(s)
    assert s.engine.pending_request.player_id==owner and '纵适' in s.engine.pending_request.prompt
    assert {a,b}<=set(s.state.cards_in(ZoneRef(ZoneType.PROCESSING)))
    wins=ranks[0]>ranks[1] if owner=='p1' else ranks[1]>ranks[0]
    expected=(b if owner=='p1' else a) if wins else (a if owner=='p1' else b)
    answer(s,True)
    assert expected in s.state.cards_in(ZoneRef(ZoneType.HAND,owner))
    assert ({a,b}-{expected})<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert s.engine.stack.is_empty()
    revealed=next(e for e in s.events.events if isinstance(e,Event) and e.event_type=='pindian_revealed')
    assert revealed.target_ids==('p2',) and revealed.metadata['source_rank']==ranks[0]


def test_zongshi_decline_discards_both_and_dual_holders_prioritize_initiator():
    s,a,b=game();s.state.players['p2'].granted_skills['zongshi_jianyong']='test'
    s.engine.start_action(PindianAction('compare','p1','p2'));answer(s,a);answer(s,b)
    assert s.engine.pending_request.player_id=='p1'
    answer(s,False);assert s.engine.pending_request is None
    assert {a,b}<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))


def test_zongshi_acquires_before_remaining_pindian_discard_without_luoying_claim():
    s,a,b=game();s.state.players['p3'].character_id='yj2011_cao_zhi'
    for c in (a,b):s.state.cards[c]=replace(s.state.cards[c],suit=Suit.CLUB)
    s.engine.start_action(PindianAction('compare','p1','p2'));answer(s,a);answer(s,b);answer(s,True)
    assert b in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    assert s.engine.pending_request is None
    assert a in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert a not in s.state.cards_in(ZoneRef(ZoneType.HAND,'p3'))
