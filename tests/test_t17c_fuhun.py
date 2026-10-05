from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.fuhun import UseFuhun, clear_grants
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.engine.events import CardUsedEvent
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.enums import Phase,Suit
from sanguosha.model.zones import ZoneRef,ZoneType


def brothers():
    s=setup('guan_xing_zhang_bao')
    empty(s,'p1');empty(s,'p2')
    return s


@pytest.mark.parametrize('dodged',[True,False])
def test_fuhun_real_use_two_costs_shared_quota_damage_only_grants_restore(dodged):
    s=brothers();a=put(s,'basic.dodge');b=put(s,'basic.wine')
    if dodged:d=put(s,'basic.dodge','p2')
    s.engine.start_action(UseFuhun('fuhun','p1'));s=restore(s);answer(s,(a,b));s=restore(s);answer(s,'p2')
    s=restore(s);answer(s,d if dodged else PASS_RESPONSE)
    assert s.engine.pending_request is None
    assert s.state.play_usage.count('basic.slash')==1
    assert s.skills.has(s.state,'p1','wusheng')== (not dodged)
    assert s.skills.has(s.state,'p1','paoxiao')== (not dodged)
    assert {a,b}<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    used=[e for e in s.events.events if isinstance(e,CardUsedEvent)]
    assert len(used)==1 and used[0].virtual_card.skill_id=='fuhun'


def test_fuhun_response_does_not_grant_or_consume_play_quota():
    s=brothers();a=put(s,'basic.dodge');b=put(s,'basic.wine')
    s.engine.start_action(RespondWithCardAction('respond','p1','basic.slash','duel'))
    assert 'virtual:fuhun' in s.engine.pending_request.eligible_card_ids
    answer(s,'virtual:fuhun');s=restore(s);answer(s,(a,b))
    assert s.engine.pending_request is None and s.state.play_usage.count('basic.slash')==0
    assert not s.skills.has(s.state,'p1','paoxiao')


def test_fuhun_grant_survives_save_and_preserves_existing_sources():
    s=brothers();s.state.players['p1'].granted_skills['wusheng']='another-skill'
    a=put(s,'basic.dodge');b=put(s,'basic.wine')
    v=replace(VirtualCard.spear(s.state,(a,b)),skill_id='fuhun')
    s.engine.start_action(MilitaryDamageAction('hurt','p1','p2',1,card_kind='slash',virtual_card=v))
    assert s.state.players['p1'].granted_skills['wusheng']=='another-skill'
    s=restore(s);assert s.skills.has(s.state,'p1','paoxiao')
    clear_grants(s.state,'p1')
    assert s.state.players['p1'].granted_skills=={'wusheng':'another-skill'}


@pytest.mark.parametrize('phase',[Phase.DRAW,Phase.FINISH])
def test_fuhun_damage_outside_play_does_not_grant(phase):
    s=brothers();s.state.current_phase=phase
    v=VirtualCard('basic.slash',(),None,None,'fuhun')
    s.engine.start_action(MilitaryDamageAction('hurt','p1','p2',1,card_kind='slash',virtual_card=v))
    assert not s.state.players['p1'].granted_skills


def test_fuhun_qianxi_all_red_rejected_mixed_pair_allowed():
    s=brothers();a=put(s,'basic.dodge');b=put(s,'basic.wine')
    for cid in (a,b):s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.HEART)
    s.state.metadata['qianxi_limits']={'p2':{'target':'p1','color':'red','turn':4}}
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseFuhun('bad','p1'))
    s.state.cards[b]=replace(s.state.cards[b],suit=Suit.CLUB)
    s.engine.start_action(UseFuhun('good','p1'))
    assert s.engine.pending_request.legal_card_sets==((a,b),)


def test_fuhun_grants_removed_by_real_turn_end():
    from sanguosha.engine.turns import TurnAction
    s=brothers();s.state.current_phase=None
    a=put(s,'basic.dodge');b=put(s,'basic.wine')
    s.engine.start_action(TurnAction('turn','p1',(Phase.PLAY,)))
    answer(s,'skill:fuhun');answer(s,(a,b));answer(s,'p2');answer(s,PASS_RESPONSE)
    assert s.skills.has(s.state,'p1','paoxiao')
    answer(s,'end_play_phase')
    assert not s.skills.has(s.state,'p1','paoxiao') and not s.skills.has(s.state,'p1','wusheng')
