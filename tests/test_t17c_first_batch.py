"""First T17C batch: gameplay timing, negative cases, privacy and mid-action restore."""
from dataclasses import replace
import pytest
from test_t17b_tier1 import game, answer, finish
from test_t6_military_basics import put
from sanguosha.engine.yj2012 import YJ2012Action, power_zone, factions
from sanguosha.engine.military_basics import MilitaryDamageAction, MilitaryStrike
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import RequestType
from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.enums import Phase, Suit, Color
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.usage import PlayUsageState
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.projection import project_for_human


def setup(name):
    s=game(); p=s.state.players['p1']; p.character_id='yj2012_'+name
    p.hp=p.max_hp=4
    s.state.current_player_id='p1'; s.state.turn_number=4
    s.state.current_phase=Phase.PLAY; s.state.play_usage=PlayUsageState('p1',4)
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return s


def restore(s):
    r=s.engine.pending_request
    s=restore_session(snapshot_session(s))
    assert s.engine.pending_request==r
    return s


def power(s,n):
    moves=s.engine.reaction_provider.__self__
    for i in range(n):
        c=put(s,'basic.slash')
        moves.move(s.state,CardMove('power:'+str(i),(c,),ZoneRef(ZoneType.HAND,'p1'),power_zone('p1'),CardMoveReason.SYSTEM,'p1'))


@pytest.mark.parametrize('amount',[1,2,3])
def test_quanji_each_point_decline_and_restore(amount):
    s=setup('zhong_hui'); s.state.players['p1'].hp=s.state.players['p1'].max_hp=8
    original=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(MilitaryDamageAction('hurt','p2','p1',amount))
    for i in range(amount):
        assert '权计' in s.engine.pending_request.prompt
        s=restore(s); answer(s,i%2==0)
        if i%2==0:
            s=restore(s); card=s.engine.pending_request.eligible_card_ids[0]
            answer(s,card)
    assert s.engine.pending_request is None
    assert len(s.state.cards_in(power_zone('p1')))==(amount+1)//2
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==original


@pytest.mark.parametrize('count',[0,2,3,4])
def test_zili_threshold_one_time_and_grant(count):
    s=setup('zhong_hui'); power(s,count)
    s.engine.start_action(YJ2012Action('zili','p1','zili'))
    if count<3:
        assert s.engine.pending_request is None
        assert not s.state.players['p1'].marks.get('zili_awakened')
        return
    s=restore(s); answer(s,'draw')
    assert s.state.players['p1'].max_hp==3
    assert s.skills.has(s.state,'p1','paiyi')
    s.engine.start_action(YJ2012Action('again','p1','zili'))
    assert s.engine.pending_request is None and s.state.players['p1'].max_hp==3


def test_zili_recover_and_preparation_hook():
    s=setup('zhong_hui'); power(s,3); s.state.players['p1'].hp=1
    s.engine.start_action(PhaseAction('prep','p1',Phase.PREPARATION))
    s=restore(s); answer(s,'recover')
    assert s.state.players['p1'].hp==2 and s.skills.has(s.state,'p1','paiyi')


@pytest.mark.parametrize('target',['p1','p2'])
def test_paiyi_draw_then_compare_and_once(target):
    s=setup('zhong_hui'); power(s,1); s.state.players['p1'].granted_skills['paiyi']='zili'
    for _ in range(7): put(s,'basic.dodge','p2')
    before=s.state.players[target].hp
    s.engine.start_action(YJ2012Action('paiyi','p1','paiyi'))
    s=restore(s); answer(s,s.engine.pending_request.eligible_card_ids[0])
    s=restore(s); answer(s,target)
    assert not s.state.cards_in(power_zone('p1'))
    assert s.state.players[target].hp==before-int(target=='p2')
    assert s.state.play_usage.count('skill.paiyi')==1
    with pytest.raises(InvalidCardUse): s.engine.start_action(YJ2012Action('again','p1','paiyi'))


def test_quan_owner_only_faces_other_public_count():
    s=setup('zhong_hui'); power(s,2)
    mine=project_for_human(s.state,s.definitions,'p1',s.character_names)
    other=project_for_human(s.state,s.definitions,'p2',s.character_names)
    assert len(mine.players[0].special_piles['quan'])==2
    assert all(c.card_id.startswith('hidden:') for c in other.players[0].special_piles['quan'])


@pytest.mark.parametrize('mode,count',[('default',2),('jiang',3),('chi',1)])
def test_jiangchi_draw_phase_modes(mode,count):
    s=setup('cao_zhang'); before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(PhaseAction('draw','p1',Phase.DRAW)); s=restore(s); answer(s,mode)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before+count
    assert bool(s.state.players['p1'].marks.get('slash_prohibited'))==(mode=='jiang')
    assert bool(s.state.players['p1'].marks.get('slash_ignore_distance'))==(mode=='chi')


@pytest.mark.parametrize('wanted',[False,True])
def test_zishou_draw_and_target_filter(wanted):
    s=setup('liu_biao'); before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    n=factions(s.state,s.skills)
    s.engine.start_action(PhaseAction('draw','p1',Phase.DRAW)); s=restore(s); answer(s,wanted)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before+2+wanted*n
    s.state.current_phase=Phase.PLAY
    c=put(s,'basic.slash')
    provider=s.engine.registry.handler_for(PhaseAction('x','p1',Phase.PLAY)).bodies.body_for(Phase.PLAY).provider
    assert bool(provider.validator.target_candidates(s.state,'p1',c))==(not wanted)


@pytest.mark.parametrize('suit,wine,expected',[(Suit.HEART,False,True),(Suit.SPADE,False,False),(Suit.SPADE,True,True),(Suit.HEART,True,True)])
def test_shiyong_red_or_wine_once(suit,wine,expected):
    s=setup('hua_xiong'); s.state.current_player_id='p2'
    c=put(s,'basic.slash','p2'); s.state.cards[c]=replace(s.state.cards[c],suit=suit)
    s.engine.start_action(MilitaryDamageAction('hurt','p2','p1',1,card_id=c,card_kind='slash',wine_enhanced=wine))
    assert s.state.players['p1'].max_hp==4-int(expected)


from sanguosha.engine.turns import TurnAction
from sanguosha.engine.events import PhaseStartedEvent
from sanguosha.engine.death import DeathAction
from sanguosha.engine.dying import DyingAction
from sanguosha.engine.requests import PASS_RESPONSE


@pytest.mark.parametrize('wanted',[True,False])
def test_fuli_dying_limited_once_and_resume(wanted):
    s=setup('liao_hua'); p=s.state.players['p1']; p.hp=0
    s.engine.start_action(DyingAction('dying','p1','p2'))
    assert '伏枥' in s.engine.pending_request.prompt
    s=restore(s); answer(s,wanted)
    if wanted:
        assert s.state.players['p1'].hp==factions(s.state,s.skills)
        assert s.state.players['p1'].marks['fuli_used']==1
        assert not s.state.players['p1'].face_up
    else:
        assert s.state.players['p1'].hp==0
        assert not s.state.players['p1'].marks.get('fuli_used')
        while s.engine.pending_request:
            answer(s,s.engine.pending_request.timeout_value())
        assert not s.state.players['p1'].is_alive


@pytest.mark.parametrize('face_up',[True,False])
def test_dangxian_extra_phase_then_normal_and_separate_usage(face_up):
    s=setup('liao_hua'); s.state.players['p1'].face_up=face_up
    s.engine.start_action(TurnAction('turn','p1',phases=(Phase.PREPARATION,Phase.PLAY)))
    count=0
    while s.engine.pending_request:
        r=s.engine.pending_request
        if r.request_type is RequestType.CHOOSE_OPTION and 'end_play_phase' in r.choices:
            count+=1
            s=restore(s); answer(s,'end_play_phase')
        else:
            answer(s,r.timeout_value())
    assert count==(2 if face_up else 0)
    starts=[e.phase for e in s.events.events if isinstance(e,PhaseStartedEvent)]
    assert starts==([Phase.PLAY,Phase.PREPARATION,Phase.PLAY] if face_up else [])


@pytest.mark.parametrize('suit,bonus',[(Suit.SPADE,False),(Suit.HEART,True)])
def test_anxu_lower_chooses_private_card_then_public_reveal(suit,bonus):
    s=setup('bu_lianshi')
    c=put(s,'basic.slash','p2'); s.state.cards[c]=replace(s.state.cards[c],suit=suit)
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(YJ2012Action('anxu','p1','anxu'))
    s=restore(s); answer(s,'p2'); s=restore(s); answer(s,'p3')
    assert s.engine.pending_request.player_id=='p3'
    assert s.engine.pending_request.subject_player_id=='p2'
    s=restore(s); answer(s,c)
    assert c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p3'))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before+bonus
    assert s.state.play_usage.count('skill.anxu')==1


def test_anxu_no_unequal_hands_negative():
    s=setup('bu_lianshi')
    with pytest.raises(InvalidCardUse): s.engine.start_action(YJ2012Action('anxu','p1','anxu'))


@pytest.mark.parametrize('wanted',[True,False])
def test_zhuiyi_dead_owner_decision_excludes_killer(wanted):
    s=setup('bu_lianshi'); s.state.players['p3'].hp=2
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))
    s.engine.start_action(DeathAction('death','p1','p2'))
    assert '追忆' in s.engine.pending_request.prompt
    s=restore(s); answer(s,wanted)
    if wanted:
        assert 'p2' not in s.engine.pending_request.allowed_player_ids
        s=restore(s); answer(s,'p3')
        assert s.state.players['p3'].hp==3
        assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))==before+3
    else:
        assert s.state.players['p3'].hp==2
        assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))==before


@pytest.mark.parametrize('count',[0,1,2])
def test_miji_current_hand_distribution_restore_all_choices(count):
    s=setup('wang_yi'); s.state.players['p1'].hp=2
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    before3=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH))
    s=restore(s); answer(s,str(count))
    if count:
        s=restore(s); answer(s,'p3')
        cards=s.engine.pending_request.eligible_card_ids[:count]
        s=restore(s); answer(s,cards)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))==before3+count


def test_zishou_global_tricks_rejected_and_self_exnihilo_allowed():
    s=setup('liu_biao'); s.state.players['p1'].marks['yj_zishou']=4
    provider=s.engine.registry.handler_for(PhaseAction('x','p1',Phase.PLAY)).bodies.body_for(Phase.PLAY).provider
    for name in ('trick.savage_assault','trick.archery_attack','trick.god_salvation','trick.amazing_grace'):
        c=put(s,name)
        assert not provider.validator.can_offer(s.state,'p1',c)
    c=put(s,'trick.ex_nihilo')
    assert provider.validator.can_offer(s.state,'p1',c)


def test_jiangchi_jiang_blocks_slash_response_even_virtual():
    from sanguosha.engine.response import RespondWithCardAction
    s=setup('cao_zhang'); s.state.players['p1'].marks['slash_prohibited']=1
    put(s,'basic.slash'); s.state.players['p1'].granted_skills['wusheng']='test'
    s.engine.start_action(RespondWithCardAction('respond','p1','basic.slash','other'))
    assert s.engine.pending_request.eligible_card_ids==()
    answer(s,PASS_RESPONSE)
    assert s.engine.pending_request is None

from sanguosha.engine.distance import DistanceSystem
from sanguosha.model.enums import EquipmentSlot


def test_gongqi_discard_weapon_range_and_optional_target_private_choice():
    s=setup('han_dang'); weapon=put(s,'equipment.weapon.crossbow')
    enemy=put(s,'basic.dodge','p2'); before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    s.engine.start_action(YJ2012Action('gongqi','p1','gongqi'))
    s=restore(s); answer(s,weapon)
    assert s.state.players['p1'].marks['yj_gongqi']==4
    assert DistanceSystem(s.definitions).attack_range(s.state,'p1')>=len(s.state.players)
    s=restore(s); answer(s,True); s=restore(s); answer(s,'p2')
    assert s.engine.pending_request.subject_player_id=='p2'
    s=restore(s); answer(s,enemy)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==before-1
    assert s.state.play_usage.count('skill.gongqi')==1


def test_gongqi_nonequipment_no_second_discard_and_once():
    s=setup('han_dang'); c=put(s,'basic.slash')
    s.engine.start_action(YJ2012Action('gongqi','p1','gongqi')); answer(s,c)
    assert s.engine.pending_request is None
    with pytest.raises(InvalidCardUse): s.engine.start_action(YJ2012Action('again','p1','gongqi'))


@pytest.mark.parametrize('discard',[False,True])
def test_jiefan_snapshot_payer_order_discard_or_draw_limited(discard):
    s=setup('han_dang')
    weapon=put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))
    s.engine.start_action(YJ2012Action('jiefan','p1','jiefan')); s=restore(s); answer(s,'p3')
    payers=[]; drew=0
    while s.engine.pending_request:
        r=s.engine.pending_request; payers.append(r.player_id)
        assert '解烦' in r.prompt
        cards=(weapon,) if discard and r.player_id=='p2' else ()
        drew+=not bool(cards)
        s=restore(s); answer(s,cards)
    assert len(payers)==len(set(payers)) and 'p3' not in payers
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))==before+drew
    assert s.state.players['p1'].marks['jiefan_used']==1
    with pytest.raises(InvalidCardUse): s.engine.start_action(YJ2012Action('again','p1','jiefan'))


def test_mashu_dynamic_grant_and_disable_are_authoritative():
    s=setup('ma_dai'); d=DistanceSystem(s.definitions)
    assert d.distance_between(s.state,'p1','p3')==1
    s.state.players['p1'].disabled_skills.add('mashu')
    assert d.distance_between(s.state,'p1','p3')==2
    s.state.players['p1'].character_id='sunquan'; s.state.players['p1'].disabled_skills.clear()
    s.state.players['p1'].granted_skills['mashu']='test'
    assert d.distance_between(s.state,'p1','p3')==1


def test_anxu_ai_hidden_hand_definition_invariance():
    from sanguosha.decisions.ai import AIDecisionProvider
    from sanguosha.engine.requests import PendingRequest
    s=setup('bu_lianshi'); cards=tuple(put(s,'basic.slash','p2') for _ in range(3))
    r=PendingRequest('anxu-card','p3',RequestType.CHOOSE_CARD,'【安恤】选择获得的一张背面手牌','a','f',eligible_card_ids=cards,subject_player_id='p2')
    ai=AIDecisionProvider('p3'); before=ai.decide(s.state,r)
    for i,c in enumerate(cards): s.state.cards[c]=replace(s.state.cards[c],definition_id=('basic.peach','trick.duel','basic.dodge')[i],rank=13-i)
    assert ai.decide(s.state,r)==before


@pytest.mark.parametrize('color,wine,expected',[(None,False,False),(None,True,True),
    (Color.RED,False,True)])
def test_shiyong_virtual_uses_virtual_definition_and_color(color,wine,expected):
    from sanguosha.model.virtual_card import VirtualCard
    s=setup('hua_xiong');c=put(s,'basic.dodge','p2')
    s.state.cards[c]=replace(s.state.cards[c],suit=Suit.HEART)
    virtual=VirtualCard('basic.slash',(c,),None,color)
    s.engine.start_action(MilitaryDamageAction('hurt','p2','p1',1,card_id=c,card_kind='slash',wine_enhanced=wine,virtual_card=virtual))
    assert s.state.players['p1'].max_hp==4-int(expected)
