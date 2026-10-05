from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.yj2012 import YJ2012Action
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.hp import LoseHpAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.events import CardUsedEvent, AfterDamageEvent
from sanguosha.engine.requests import PASS_RESPONSE,RequestType
from sanguosha.model.enums import Phase,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType


def cheng():
    s=setup('cheng_pu')
    for q in s.state.seat_order:empty(s,q)
    return s


def finish(s):
    for _ in range(100):
        r=s.engine.pending_request
        if r is None:return
        assert r.request_type is RequestType.RESPOND_WITH_CARD
        answer(s,PASS_RESPONSE)
    raise AssertionError('not settled')


@pytest.mark.parametrize('dodged',[True,False])
def test_lihuo_real_fire_damage_and_single_hp_cost_restore(dodged):
    s=cheng();card=put(s,'basic.slash');d=put(s,'basic.dodge','p2') if dodged else None
    hp=s.state.players['p1'].hp
    s.engine.start_action(YJ2012Action('lihuo','p1','lihuo'));s=restore(s);answer(s,card)
    s=restore(s);assert s.engine.pending_request.max_count==2;answer(s,('p2',))
    s=restore(s);answer(s,d if dodged else PASS_RESPONSE)
    assert s.engine.pending_request is None
    assert s.state.players['p1'].hp==hp-int(not dodged)
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    used=next(e for e in s.events.events if isinstance(e,CardUsedEvent))
    assert used.virtual_card.definition_id=='basic.fire_slash' and used.virtual_card.skill_id=='lihuo'


def test_lihuo_multiple_targets_and_chain_pay_hp_only_once():
    s=cheng();card=put(s,'basic.slash')
    s.state.players['p2'].chained=s.state.players['p3'].chained=True
    s.engine.start_action(YJ2012Action('lihuo','p1','lihuo'));answer(s,card)
    answer(s,('p2','p5'));finish(s)
    victims={e.target_id for e in s.events.events if isinstance(e,AfterDamageEvent)}
    assert {'p2','p3','p5'}<=victims and s.state.players['p1'].hp==3
    assert not s.state.metadata.get('lihuo_hits')


def test_printed_fire_slash_has_extra_target_but_no_hp_cost():
    s=cheng();card=put(s,'basic.fire_slash')
    s.engine.start_action(UseCardAction('fire','p1',card,('p2','p5')));finish(s)
    assert s.state.players['p1'].hp==4
    assert s.state.players['p2'].hp==3 and s.state.players['p5'].hp==3


def test_lihuo_hp_loss_can_dying_after_card_finishes():
    s=cheng();s.state.players['p1'].hp=1;card=put(s,'basic.slash');peach=put(s,'basic.peach')
    s.engine.start_action(YJ2012Action('lihuo','p1','lihuo'));answer(s,card);answer(s,('p2',));answer(s,PASS_RESPONSE)
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert s.engine.pending_request.required_definition_id=='basic.peach'
    s=restore(s);answer(s,peach)
    assert s.state.players['p1'].hp==1 and s.engine.pending_request is None


def test_chunlao_finish_store_multiple_slash_and_nonempty_no_refill():
    s=cheng();a=put(s,'basic.slash');b=put(s,'basic.fire_slash');other=put(s,'basic.dodge')
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH));s=restore(s);answer(s,True)
    s=restore(s);assert other not in s.engine.pending_request.eligible_card_ids;answer(s,(a,b))
    wine=ZoneRef(ZoneType.SPECIAL,'p1',special_key='wine')
    assert s.state.cards_in(wine)==(a,b)
    s.engine.start_action(YJ2012Action('again','p1','chunlao'))
    assert s.engine.pending_request is None


def test_chunlao_saves_other_via_their_wine_without_jiuyuan_double_bonus():
    s=cheng();a=put(s,'basic.slash');s.engine.start_action(YJ2012Action('store','p1','chunlao'))
    answer(s,True);answer(s,(a,));s.state.players['p2'].hp=1
    s.state.players['p2'].granted_skills['jiuyuan']='test'
    from sanguosha.model.enums import Identity
    s.state.players['p2'].identity=Identity.LORD
    s.engine.start_action(LoseHpAction('dying','p2',1))
    for _ in range(8):
        r=s.engine.pending_request
        if r.player_id=='p1':break
        answer(s,PASS_RESPONSE)
    s=restore(s);assert 'virtual:chunlao:'+a in s.engine.pending_request.eligible_card_ids
    answer(s,'virtual:chunlao:'+a)
    assert s.engine.pending_request is None and s.state.players['p2'].hp==1
    wineuse=next(e for e in s.events.events if isinstance(e,CardUsedEvent) and e.virtual_definition_id=='basic.wine')
    assert wineuse.player_id=='p2' and wineuse.virtual_card.material_ids==()
    assert not s.state.cards_in(ZoneRef(ZoneType.SPECIAL,'p1',special_key='wine'))
