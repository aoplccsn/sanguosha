from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer
from test_t17c_juece import empty
from test_t6_military_basics import put
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.events import AfterDamageEvent
from sanguosha.engine.requests import RequestType,PASS_RESPONSE
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.model.enums import EquipmentSlot

def finish(s):
    for _ in range(100):
        r=s.engine.pending_request
        if r is None:return
        if r.request_type is RequestType.CHOOSE_CARD:answer(s,r.eligible_card_ids[0])
        elif r.request_type is RequestType.YES_NO:answer(s,False)
        else:answer(s,PASS_RESPONSE)
    raise AssertionError('card did not settle')

def wang():
    s=setup('wang_yi');s.state.players['p1'].hp=s.state.players['p1'].max_hp=3
    s.state.current_player_id='p2';s.state.play_usage=PlayUsageState('p2',s.state.turn_number)
    return s

@pytest.mark.parametrize('definition',['basic.slash','basic.fire_slash','basic.thunder_slash','trick.duel','trick.dismantlement'])
@pytest.mark.parametrize('wanted',[True,False])
def test_zhenlie_physical_card_cost_then_only_self_cancel_restore(definition,wanted):
    s=wang();card=put(s,definition,'p2');cost=put(s,'basic.dodge','p2')
    s.engine.start_action(UseCardAction('card','p2',card,('p1',)))
    assert s.engine.pending_request.request_type is RequestType.YES_NO
    s=restore(s);answer(s,wanted)
    if wanted:
        s=restore(s);assert card not in s.engine.pending_request.eligible_card_ids
        assert cost in s.engine.pending_request.eligible_card_ids;answer(s,cost)
    finish(s)
    assert (cost in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))==wanted
    if wanted:
        assert s.state.players['p1'].hp==2
        assert not any(isinstance(e,AfterDamageEvent) and e.target_id=='p1' for e in s.events.events)
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

def test_zhenlie_aoe_does_not_cancel_other_targets():
    s=wang();card=put(s,'trick.savage_assault','p2');cost=put(s,'basic.dodge','p2')
    s.engine.start_action(UseCardAction('aoe','p2',card));s=restore(s);answer(s,True)
    s=restore(s);answer(s,cost);finish(s)
    victims={e.target_id for e in s.events.events if isinstance(e,AfterDamageEvent)}
    assert 'p1' not in victims and {'p3','p4','p5'}<=victims
    assert s.state.players['p1'].hp==2

def test_zhenlie_no_source_cards_still_cancels():
    s=wang();empty(s,'p2');card=put(s,'basic.slash','p2')
    s.engine.start_action(UseCardAction('slash','p2',card,('p1',)));answer(s,True)
    assert s.engine.pending_request is None and s.state.players['p1'].hp==2

def test_zhenlie_dying_rescued_then_discard_and_cancel():
    s=wang();s.state.players['p1'].hp=1;peach=put(s,'basic.peach','p1');card=put(s,'basic.slash','p2')
    s.engine.start_action(UseCardAction('slash','p2',card,('p1',)));answer(s,True)
    assert s.engine.pending_request.required_definition_id=='basic.peach';s=restore(s);answer(s,peach)
    assert s.engine.pending_request.request_type is RequestType.CHOOSE_CARD
    s=restore(s);answer(s,s.engine.pending_request.eligible_card_ids[0]);finish(s)
    assert s.state.players['p1'].is_alive and s.state.players['p1'].hp==1

def test_zhenlie_dying_dead_does_not_discard_source_after_death():
    s=wang();s.state.players['p1'].hp=1;card=put(s,'basic.slash','p2');cost=put(s,'basic.dodge','p2')
    s.engine.start_action(UseCardAction('slash','p2',card,('p1',)));answer(s,True);finish(s)
    assert not s.state.players['p1'].is_alive
    assert cost in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

def test_delayed_trick_and_self_use_have_no_zhenlie_offer():
    s=wang();card=put(s,'delayed.indulgence','p2')
    s.engine.start_action(UseCardAction('delay','p2',card,('p1',)))
    assert s.engine.pending_request is None or s.engine.pending_request.request_type is RequestType.RESPOND_WITH_CARD;finish(s)
    s.state.current_player_id='p1';s.state.play_usage=PlayUsageState('p1',s.state.turn_number)
    card=put(s,'trick.ex_nihilo','p1');s.engine.start_action(UseCardAction('draw','p1',card))
    assert s.engine.pending_request is None or s.engine.pending_request.request_type is RequestType.RESPOND_WITH_CARD;finish(s)
