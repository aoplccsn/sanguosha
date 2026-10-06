"""Shared final-card limits apply to ViewAs actions as to physical uses."""
from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t17c_qice import clear_hand
from test_t6_military_basics import put
from sanguosha.engine.skills import QixiUse,GuoseUse,LongdanUse
from sanguosha.engine.fire import FireViewAsTrick
from sanguosha.engine.forest import DuanliangUse
from sanguosha.engine.gods import LonghunUse
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.enums import Suit
from sanguosha.model.zones import ZoneRef,ZoneType

CASES=[('qixi','ganning',Suit.CLUB,'basic.slash'),('guose','daqiao',Suit.DIAMOND,'basic.slash'),
       ('longdan','zhaoyun',Suit.HEART,'basic.dodge'),('huoji','fire_wolong',Suit.HEART,'basic.slash'),
       ('duanliang','forest_xuhuang',Suit.CLUB,'basic.slash'),('longhun','mountain_god_zhaoyun',Suit.HEART,'basic.slash')]

def action(skill,cid):
    if skill=='qixi':return QixiUse('audit-view-limit','p1',cid)
    if skill=='guose':return GuoseUse('audit-view-limit','p1',cid)
    if skill=='longdan':return LongdanUse('audit-view-limit','p1',cid)
    if skill=='huoji':return FireViewAsTrick('audit-view-limit','p1',cid,skill)
    if skill=='duanliang':return DuanliangUse('audit-view-limit','p1',cid)
    return LonghunUse('audit-view-limit','p1',(cid,),'basic.peach')

@pytest.mark.parametrize('skill,general,suit,definition',CASES)
def test_view_as_cannot_use_qianxi_forbidden_hand_color(skill,general,suit,definition):
    s=setup('xun_you');s.state.players['p1'].character_id=general;clear_hand(s)
    if skill=='longhun':s.state.players['p1'].hp=1;s.state.players['p1'].max_hp=2
    cid=put(s,definition);s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    s.state.metadata['qianxi_limits']={'p2':{'target':'p1','color':'red' if suit in (Suit.HEART,Suit.DIAMOND) else 'black','turn':s.state.turn_number}}
    with pytest.raises(InvalidCardUse):s.engine.start_action(action(skill,cid))
    assert cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))

@pytest.mark.parametrize('skill,general,suit,definition',[c for c in CASES if c[0] in ('qixi','guose','huoji','duanliang')])
def test_view_as_trick_cannot_bypass_qiaoshui_lock(skill,general,suit,definition):
    s=setup('xun_you');s.state.players['p1'].character_id=general;clear_hand(s)
    cid=put(s,definition);s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    s.state.players['p1'].marks['qiaoshui_trick_lock']=s.state.turn_number
    with pytest.raises(InvalidCardUse):s.engine.start_action(action(skill,cid))
    assert cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))

@pytest.mark.parametrize('definition',['basic.slash','basic.fire_slash','basic.thunder_slash'])
def test_longdan_all_slash_prints_can_respond_as_dodge(definition):
    from sanguosha.engine.response import RespondWithCardAction
    s=setup('xun_you');s.state.players['p1'].character_id='zhaoyun';clear_hand(s)
    cid=put(s,definition)
    s.engine.start_action(RespondWithCardAction('audit-longdan-prints','p1','basic.dodge','slash'))
    assert 'virtual:longdan:'+cid in s.engine.pending_request.eligible_card_ids
    s=restore(s);answer(s,'virtual:longdan:'+cid)
    assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert s.engine.last_result.definition_id=='basic.dodge'

@pytest.mark.parametrize('skill,general,required,suit,definition,zone',[
    ('wusheng','guanyu','basic.slash',Suit.HEART,'equipment.weapon.crossbow','equipment'),
    ('qingguo','zhenji','basic.dodge',Suit.CLUB,'basic.slash','hand'),
    ('longdan','zhaoyun','basic.slash',Suit.HEART,'basic.dodge','hand'),
    ('jijiu','huatuo','basic.peach',Suit.HEART,'equipment.weapon.crossbow','equipment'),
])
@pytest.mark.parametrize('suppressed',[False,True])
def test_basic_view_as_material_permissions_cost_and_response_number(skill,general,required,suit,definition,zone,suppressed):
    from sanguosha.engine.response import RespondWithCardAction
    from sanguosha.engine.events import CardRespondedEvent
    from sanguosha.model.enums import EquipmentSlot
    s=setup('xun_you');s.state.players['p1'].character_id=general;clear_hand(s)
    if skill=='jijiu':s.state.current_player_id='p2';s.state.players['p2'].hp=0
    cid=put(s,definition,'p1',ZoneType.EQUIPMENT if zone=='equipment' else ZoneType.HAND,EquipmentSlot.WEAPON if zone=='equipment' else None)
    s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    if suppressed:s.state.players['p1'].disabled_skills.add(skill)
    s.engine.start_action(RespondWithCardAction('audit-basic-view-response','p1',required,'source',subject_player_id='p2',response_number=2,response_total=2))
    option='virtual:'+skill+':'+cid
    assert (option in s.engine.pending_request.eligible_card_ids)==(not suppressed)
    if suppressed:return
    s=restore(s);answer(s,option)
    assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    events=[e for e in s.events.events if isinstance(e,CardRespondedEvent) and e.source_action_id=='source']
    assert len(events)==1 and events[0].response_definition_id==required
    assert events[0].response_number==2 and events[0].response_total==2
    assert not s.state.play_usage.count('basic.slash')

@pytest.mark.parametrize('mode',['spear','fuhun'])
def test_two_materials_are_one_numbered_slash_response(mode):
    from sanguosha.engine.response import RespondWithCardAction
    from sanguosha.engine.events import CardRespondedEvent
    from sanguosha.model.enums import EquipmentSlot
    s=setup('xun_you');clear_hand(s)
    if mode=='fuhun':s.state.players['p1'].character_id='yj2012_guan_xing_zhang_bao'
    else:put(s,'equipment.weapon.serpent_spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    cards=tuple(put(s,'basic.dodge') for _ in range(2))
    s.engine.start_action(RespondWithCardAction('audit-two-response','p1','basic.slash','duel',response_number=2,response_total=2))
    answer(s,'virtual:'+mode);s=restore(s);answer(s,cards)
    events=[e for e in s.events.events if isinstance(e,CardRespondedEvent) and e.source_action_id=='duel']
    assert len(events)==1 and events[0].response_number==2 and events[0].response_total==2
    assert s.engine.last_result.material_ids==cards
    assert set(cards)<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))

@pytest.mark.parametrize('skill,general,suit,definition',[c for c in CASES if c[0]!='longhun'])
def test_view_as_target_submission_rechecks_skill_without_paying(skill,general,suit,definition):
    s=setup('xun_you');s.state.players['p1'].character_id=general;clear_hand(s)
    cid=put(s,definition);s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    s.engine.start_action(action(skill,cid));s=restore(s)
    r=s.engine.pending_request
    assert r is not None
    s.state.players['p1'].disabled_skills.add(skill)
    choice=r.allowed_player_ids[0]
    from sanguosha.engine.requests import RequestType
    if r.request_type is RequestType.CHOOSE_PLAYERS:choice=(choice,)
    with pytest.raises(InvalidCardUse):answer(s,choice)
    assert cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))

@pytest.mark.parametrize('skill,general,required,suit,condition',[
 ('qingguo','zhenji','basic.dodge',Suit.HEART,'wrong-color'),
 ('qingguo','zhenji','basic.dodge',Suit.CLUB,'equipment'),
 ('qingguo','zhenji','basic.slash',Suit.CLUB,'wrong-pattern'),
 ('jijiu','huatuo','basic.peach',Suit.CLUB,'wrong-color'),
 ('jijiu','huatuo','basic.peach',Suit.HEART,'own-turn'),
 ('jijiu','huatuo','basic.dodge',Suit.HEART,'wrong-pattern'),
])
def test_basic_response_invalid_material_context_is_not_offered(skill,general,required,suit,condition):
    from sanguosha.engine.response import RespondWithCardAction
    from sanguosha.model.enums import EquipmentSlot
    s=setup('xun_you');s.state.players['p1'].character_id=general;clear_hand(s)
    if skill=='jijiu' and condition!='own-turn':s.state.current_player_id='p2'
    equipment=condition=='equipment'
    cid=put(s,'equipment.weapon.crossbow' if equipment else 'basic.slash','p1',ZoneType.EQUIPMENT if equipment else ZoneType.HAND,EquipmentSlot.WEAPON if equipment else None)
    s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    s.engine.start_action(RespondWithCardAction('audit-response-invalid','p1',required,'source',subject_player_id='p2'))
    assert 'virtual:'+skill+':'+cid not in s.engine.pending_request.eligible_card_ids

@pytest.mark.parametrize('skill,general,suit,definition',[c for c in CASES if c[0] in ('qixi','guose','huoji','duanliang')])
def test_trick_view_as_valid_use_reconnect_cost_and_final_identity(skill,general,suit,definition):
    from sanguosha.engine.events import CardUsedEvent
    s=setup('xun_you');s.state.players['p1'].character_id=general;clear_hand(s)
    cid=put(s,definition);s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    s.engine.start_action(action(skill,cid))
    for _ in range(120):
        r=s.engine.pending_request
        if r is None:break
        s=restore(s)
        from sanguosha.engine.requests import RequestType
        if r.request_type is RequestType.CHOOSE_PLAYER:choice='p2' if 'p2' in r.allowed_player_ids else r.allowed_player_ids[0]
        elif r.request_type is RequestType.CHOOSE_PLAYERS:choice=('p2',)
        elif r.request_type is RequestType.CHOOSE_CARD:choice=r.eligible_card_ids[0]
        else:choice=r.timeout_value()
        answer(s,choice)
    else:raise AssertionError('view-as did not finish')
    uses=[e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='audit-view-limit:used']
    expected={'qixi':'trick.dismantlement','guose':'delayed.indulgence','huoji':'trick.fire_attack','duanliang':'delayed.supply_shortage'}[skill]
    assert len(uses)==1 and uses[0].virtual_definition_id==expected
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    dest=ZoneRef(ZoneType.JUDGMENT,'p2') if skill in ('guose','duanliang') else ZoneRef(ZoneType.DISCARD_PILE)
    assert cid in s.state.cards_in(dest)
    s.state.__post_init__()

@pytest.mark.parametrize('recast',[False,True])
def test_lianhuan_qianxi_banned_color_still_allows_only_recast(recast):
    s=setup('xun_you');s.state.players['p1'].character_id='fire_pang_tong';clear_hand(s)
    cid=put(s,'basic.slash');s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.CLUB)
    s.state.metadata['qianxi_limits']={'p2':{'target':'p1','color':'black','turn':s.state.turn_number}}
    s.engine.start_action(FireViewAsTrick('audit-lianhuan-limit','p1',cid,'lianhuan'));s=restore(s)
    if not recast:
        with pytest.raises(InvalidCardUse):answer(s,('p2',))
        assert cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    else:
        answer(s,());finish(s)
        assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
        assert not s.state.play_usage.count('trick.iron_chain')
