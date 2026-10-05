from dataclasses import replace
import pytest
from test_t17c_first_batch import setup, restore
from test_t17b_tier1 import answer
from test_t17c_juece import empty
from test_t6_military_basics import put
from sanguosha.engine.yj2012 import YJ2012Action
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import PendingRequest, RequestType
from sanguosha.engine.errors import InvalidDecision
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.card_limits import card_allowed, legal_pairs, clear_source
from sanguosha.model.enums import Suit, Phase, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.usage import PlayUsageState
from sanguosha.multiplayer.protocol import serialize_request


def colored(s, suit, definition='basic.slash', owner='p2'):
    cid=put(s,definition,owner)
    s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    return cid


def limit(s,color='red',target='p2'):
    s.state.metadata['qianxi_limits']={'p1':{'target':target,'color':color,'turn':s.state.turn_number}}
    s.state.players[target].marks['qianxi_'+color+'_p1']=1


@pytest.mark.parametrize('suit,color',[(Suit.HEART,'red'),(Suit.CLUB,'black')])
def test_qianxi_preparation_judgment_target_and_restore(suit,color):
    s=setup('ma_dai');top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top]=replace(s.state.cards[top],suit=suit)
    s.engine.start_action(PhaseAction('prep','p1',Phase.PREPARATION))
    assert '潜袭' in s.engine.pending_request.prompt
    s=restore(s);answer(s,True);s=restore(s)
    assert 'p1' not in s.engine.pending_request.allowed_player_ids
    assert 'p2' in s.engine.pending_request.allowed_player_ids
    answer(s,'p2')
    assert s.state.metadata['qianxi_limits']['p1']=={'target':'p2','color':color,'turn':4}
    assert top in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_qianxi_decline_has_no_judgment_or_limit():
    s=setup('ma_dai');before=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))
    s.engine.start_action(YJ2012Action('skill','p1','qianxi'));answer(s,False)
    assert s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))==before
    assert not s.state.metadata.get('qianxi_limits')


@pytest.mark.parametrize('color,suit,other',[('red',Suit.HEART,Suit.CLUB),('black',Suit.CLUB,Suit.HEART)])
def test_qianxi_physical_response_filters_but_discard_is_legal(color,suit,other):
    s=setup('ma_dai');empty(s,'p2');bad=colored(s,suit);good=colored(s,other);limit(s,color)
    s=restore(s);s.engine.start_action(RespondWithCardAction('respond','p2','basic.slash','slash'))
    assert bad not in s.engine.pending_request.eligible_card_ids
    assert good in s.engine.pending_request.eligible_card_ids
    with pytest.raises(InvalidDecision):s.engine.pending_request.validate(bad)
    answer(s,good)
    s.engine.reaction_provider.__self__.move(s.state,CardMove('discard',(bad,),ZoneRef(ZoneType.HAND,'p2'),
        ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,'p2'))
    assert bad in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_qianxi_ordinary_use_rejected_before_consuming_card():
    s=setup('ma_dai');cid=colored(s,Suit.HEART);limit(s)
    s.state.current_player_id='p2';s.state.play_usage=PlayUsageState('p2',4)
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('use','p2',cid,('p1',)))
    assert cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))


def test_qianxi_mixed_spear_pair_is_legal_red_pair_is_rejected_restore():
    s=setup('ma_dai');empty(s,'p2');red=colored(s,Suit.HEART);red2=colored(s,Suit.DIAMOND);black=colored(s,Suit.CLUB)
    put(s,'equipment.weapon.serpent_spear','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON);limit(s)
    s.engine.start_action(RespondWithCardAction('respond','p2','basic.slash','slash'));answer(s,'virtual:spear')
    s=restore(s);r=s.engine.pending_request
    assert (red,red2) not in r.legal_card_sets and (red,black) in r.legal_card_sets
    with pytest.raises(InvalidDecision):r.validate((red,red2))
    r.validate((black,red));answer(s,(black,red))
    assert s.engine.pending_request is None and red2 in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))


def test_qianxi_all_banned_spear_does_not_offer_activation():
    s=setup('ma_dai');empty(s,'p2');colored(s,Suit.HEART);colored(s,Suit.DIAMOND)
    put(s,'equipment.weapon.serpent_spear','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON);limit(s)
    s.engine.start_action(RespondWithCardAction('respond','p2','basic.slash','slash'))
    assert 'virtual:spear' not in s.engine.pending_request.eligible_card_ids


def test_qianxi_equipment_and_mixed_zone_materials_are_unrestricted():
    s=setup('ma_dai');hand=colored(s,Suit.HEART);equip=put(s,'equipment.armor.eight_trigrams','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.state.cards[equip]=replace(s.state.cards[equip],suit=Suit.HEART);limit(s)
    assert not card_allowed(s.state,'p2',(hand,))
    assert card_allowed(s.state,'p2',(equip,)) and card_allowed(s.state,'p2',(hand,equip))
    assert card_allowed(s.state,'p2',())


def test_qianxi_effective_hongyan_and_source_death_expiration():
    s=setup('ma_dai');s.state.players['p2'].granted_skills['hongyan']='test'
    cid=colored(s,Suit.SPADE);limit(s)
    assert not card_allowed(s.state,'p2',(cid,))
    s.state.players['p2'].disabled_skills.add('hongyan')
    assert card_allowed(s.state,'p2',(cid,))
    clear_source(s.state,'p1');assert not s.state.players['p2'].marks.get('qianxi_red_p1')
    limit(s);s.state.turn_number+=1;assert card_allowed(s.state,'p2',(cid,))


def test_combination_request_timeout_and_wire_keep_legal_pair():
    r=PendingRequest('r','p2',RequestType.CHOOSE_CARDS,'组合','a','f',eligible_card_ids=('a','b','c'),
        min_count=2,max_count=2,legal_card_sets=(('a','c'),('b','c')))
    assert r.timeout_value()==('a','c')
    assert serialize_request(r,1)['legal_card_sets']==[['a','c'],['b','c']]
    with pytest.raises(InvalidDecision):r.validate(('a','b'))


def test_qianxi_real_source_death_removes_mark_and_limit():
    from sanguosha.engine.death import DeathAction
    s=setup('ma_dai');cid=colored(s,Suit.HEART);limit(s)
    s.engine.start_action(DeathAction('death','p1',None))
    assert not s.state.metadata.get('qianxi_limits')
    assert not s.state.players['p2'].marks.get('qianxi_red_p1')
    assert card_allowed(s.state,'p2',(cid,))


def test_qianxi_owner_turn_end_clears_limit_and_mark():
    from sanguosha.engine.turns import TurnAction
    s=setup('ma_dai')
    s.state.current_phase=None
    # A one-phase scheduled turn allows expiry to run through the real handler.
    s.engine.start_action(TurnAction('turn','p1',(Phase.PLAY,)))
    limit(s);assert s.engine.pending_request is not None
    answer(s,'end_play_phase')
    assert not s.state.metadata.get('qianxi_limits')
    assert not s.state.players['p2'].marks.get('qianxi_red_p1')


def test_qianxi_single_view_as_filtered_and_equipment_jijiu_remains():
    s=setup('ma_dai');empty(s,'p2');s.state.players['p2'].granted_skills.update({'longdan':'test','wusheng':'test','jijiu':'test'})
    red=colored(s,Suit.HEART,'basic.dodge');limit(s)
    s.engine.start_action(RespondWithCardAction('respond','p2','basic.slash','slash'))
    assert 'virtual:longdan:'+red not in s.engine.pending_request.eligible_card_ids
    assert 'virtual:wusheng:'+red not in s.engine.pending_request.eligible_card_ids
    from sanguosha.engine.requests import PASS_RESPONSE
    answer(s,PASS_RESPONSE)
    equip=put(s,'equipment.armor.eight_trigrams','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.state.cards[equip]=replace(s.state.cards[equip],suit=Suit.HEART)
    s.engine.start_action(RespondWithCardAction('heal','p2','basic.peach','dying',subject_player_id='p3'))
    assert 'virtual:jijiu:'+equip in s.engine.pending_request.eligible_card_ids
    assert 'virtual:jijiu:'+red not in s.engine.pending_request.eligible_card_ids
