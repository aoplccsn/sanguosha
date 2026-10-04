"""Timing, legality, privacy and resumability of the six remaining locked generals."""
from dataclasses import replace
import pytest
from sanguosha.engine.yj2011_tier3 import (YJSkillAction, hand, equipped_cards, reactions,
    scoped_target, protected, clear_turn)
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService, EquipmentExchangeTransaction, InvalidCardMove
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.military_basics import MilitaryDamageAction, MilitaryStrike
from sanguosha.engine.military_tricks import TargetTrick
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.death import DeathAction
from sanguosha.engine.requests import RequestType, PASS_RESPONSE
from sanguosha.engine.events import Event, CardUsedEvent, CardRespondedEvent, PlayerDiedEvent, KillRewardEvent
from sanguosha.model.enums import Phase, Suit, EquipmentSlot, Identity
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.state import GameStatus
from sanguosha.model.usage import PlayUsageState
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.projection import project_for_human
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.room_snapshot import snapshot_room, restore_room
from test_t17b_tier1 import game, answer, finish
from test_t6_military_basics import put


def active(s, general):
    s.state.players['p1'].character_id = 'yj2011_' + general
    s.state.players['p1'].hp = s.state.players['p1'].max_hp = 4
    s.state.current_player_id = 'p1'
    s.state.current_phase = Phase.PLAY
    s.state.turn_number = 5
    s.state.play_usage = PlayUsageState('p1', 5)
    s.state.metadata['reaction_event_cursor'] = len(s.events.events)


def restore(s):
    request = s.engine.pending_request
    result = restore_session(snapshot_session(s))
    assert result.engine.pending_request == request
    return result


def drain(s):
    for _ in range(150):
        r = s.engine.pending_request
        if r is None:
            assert s.engine.stack.is_empty()
            return s
        s = restore(s)
        answer(s, r.timeout_value())
    pytest.fail('resolution exceeded limit')


def discard(s, cards, pid='p2', reason=CardMoveReason.DISCARD):
    moves = s.engine.reaction_provider.__self__
    moves.move(s.state, CardMove('batch', tuple(cards), ZoneRef(ZoneType.HAND, pid),
        ZoneRef(ZoneType.DISCARD_PILE), reason, pid))
    s.engine.start_action(YJSkillAction('flush', 'p1', 'jiushi_return'))


@pytest.mark.parametrize('reason',list(CardMoveReason))
@pytest.mark.parametrize('suit',[Suit.CLUB,Suit.HEART])
def test_luoying_move_facts_include_only_other_discard(reason,suit):
    s=game(); active(s,'cao_zhi')
    cid=put(s,'basic.slash','p2'); s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    discard(s,(cid,),reason=reason)
    r=s.engine.pending_request
    expected=reason is CardMoveReason.DISCARD and suit is Suit.CLUB
    assert ('【落英】' in r.prompt)==expected
    if expected:
        s=restore(s); answer(s,True); s=restore(s); answer(s,(cid,))
        assert cid in hand(s.state,'p1')
    drain(s)


def test_luoying_batch_subset_rechecks_and_judgment_provenance():
    s=game(); active(s,'cao_zhi')
    cards=[put(s,'basic.slash','p2') for _ in range(3)]
    for cid in cards: s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.CLUB)
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    discard(s,cards); answer(s,True)
    assert set(s.engine.pending_request.eligible_card_ids)==set(cards)
    s=restore(s); answer(s,(cards[1],)); s=drain(s)
    assert cards[1] in hand(s.state,'p1') and cards[0] in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    event=Event('judge','after_judgment','p2',metadata={'card_id':cards[0]})
    assert reactions(s.state,event,s.skills)[0].card_ids==(cards[0],)
    assert not reactions(s.state,replace(event,source_id='p1'),s.skills)
    CardMoveService(s.events).move(s.state,CardMove('taken',(cards[0],),ZoneRef(ZoneType.DISCARD_PILE),ZoneRef(ZoneType.HAND,'p3'),CardMoveReason.SYSTEM))
    assert not reactions(s.state,event,s.skills)


@pytest.mark.parametrize('face_up',[False,True])
def test_jiushi_active_legality_turnover_and_wine_quota(face_up):
    s=game(); active(s,'cao_zhi'); s.state.players['p1'].face_up=face_up
    action=YJSkillAction('jiushi','p1','jiushi')
    if not face_up:
        with pytest.raises(InvalidCardUse): s.engine.start_action(action)
        assert not s.state.players['p1'].marks.get('wine')
        return
    s.engine.start_action(action)
    assert not s.state.players['p1'].face_up and s.state.players['p1'].marks['wine']==1
    assert s.state.play_usage.count('basic.wine')==1
    assert any(isinstance(e,CardUsedEvent) and e.virtual_definition_id=='basic.wine' for e in s.events.events)


@pytest.mark.parametrize('face_up',[False,True])
@pytest.mark.parametrize('amount',[1,2])
def test_jiushi_damage_uses_orientation_before_hp_deduction(face_up,amount):
    s=game(); active(s,'cao_zhi'); s.state.players['p1'].face_up=face_up
    s.engine.start_action(MilitaryDamageAction('damage','p2','p1',amount))
    if face_up:
        assert s.engine.pending_request is None
    else:
        assert '酒诗' in s.engine.pending_request.prompt
        s=restore(s); answer(s,True)
        assert s.state.players['p1'].face_up
    assert s.state.players['p1'].hp==4-amount


def test_jiushi_dying_self_rescue_does_not_grant_after_damage_flip():
    s=game(); active(s,'cao_zhi'); s.state.players['p1'].hp=1
    s.engine.start_action(MilitaryDamageAction('fatal','p2','p1',1))
    r=s.engine.pending_request; assert 'virtual:jiushi' in r.eligible_card_ids
    s=restore(s); answer(s,'virtual:jiushi')
    assert s.engine.pending_request is None and s.state.players['p1'].hp==1
    assert not s.state.players['p1'].face_up


@pytest.mark.parametrize('count',[1,2,3])
def test_enyuan_same_acquisition_batch_source_threshold(count):
    s=game(); active(s,'fa_zheng')
    cards=tuple(put(s,'basic.slash','p2') for _ in range(count))
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    moves=s.engine.reaction_provider.__self__
    moves.move(s.state,CardMove('gift',cards,ZoneRef(ZoneType.HAND,'p2'),ZoneRef(ZoneType.HAND,'p1'),CardMoveReason.SYSTEM,'p2'))
    event=s.events.events[-1]
    offers=reactions(s.state,event,s.skills)
    assert bool(offers)==(count>=2)
    if offers:
        before=len(hand(s.state,'p2'))
        s.state.metadata['reaction_event_cursor']=len(s.events.events)
        s.engine.start_action(offers[0]); s=restore(s); answer(s,True)
        assert len(hand(s.state,'p2'))==before+1


@pytest.mark.parametrize('source',[None,'p2'])
@pytest.mark.parametrize('amount',[1,2])
def test_enyuan_each_damage_point_source_gives_or_loses_hp(source,amount):
    s=game(); active(s,'fa_zheng')
    hp=s.state.players['p2'].hp
    s.engine.start_action(MilitaryDamageAction('damage',source,'p1',amount))
    if source is None:
        assert s.engine.pending_request is None
        return
    for i in range(amount):
        s=restore(s); answer(s,True)
        s=restore(s); answer(s,'lose_hp')
    assert s.state.players['p2'].hp==hp-amount and s.engine.pending_request is None


@pytest.mark.parametrize('slash',[False,True])
def test_xuanhuo_draw_replacement_forced_slash_or_two_private_acquisitions(slash):
    s=game(); active(s,'fa_zheng')
    p1_before=len(hand(s.state,'p1')); p2_before=len(hand(s.state,'p2'))
    cid=put(s,'basic.slash','p2') if slash else None
    s.engine.start_action(PhaseAction('draw','p1',Phase.DRAW))
    answer(s,True); s=restore(s); answer(s,'p2')
    s=restore(s); answer(s,'p3')
    r=s.engine.pending_request
    if slash:
        answer(s,cid); s=drain(s)
        assert s.state.players['p3'].hp==3
        assert len(hand(s.state,'p1'))==p1_before
    else:
        answer(s,'decline')
        for i in range(2):
            r=s.engine.pending_request; assert r.subject_player_id=='p2'
            room=MultiplayerRoom(); room.session=s
            payload=room._request_payload(r)
            assert all(x.startswith('hidden-hand:') for x in payload['eligible_card_ids'])
            s=restore(s); answer(s,r.eligible_card_ids[0])
        assert len(hand(s.state,'p1'))==p1_before+2
        assert len(hand(s.state,'p2'))==p2_before
        assert '恩怨' in s.engine.pending_request.prompt
        s=restore(s); answer(s,False)
    assert s.engine.pending_request is None


@pytest.mark.parametrize('hearts',[0,1,3])
@pytest.mark.parametrize('take',[False,True])
def test_xinzhan_private_top_three_hearts_and_ordered_return(hearts,take):
    s=game(); active(s,'ma_su'); s.state.players['p1'].hp=s.state.players['p1'].max_hp=3
    while len(hand(s.state,'p1'))<=3: put(s,'basic.slash')
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:3]
    for i,cid in enumerate(top): s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.HEART if i<hearts else Suit.CLUB)
    before=len(hand(s.state,'p1'))
    s.engine.start_action(YJSkillAction('xinzhan','p1','xinzhan'))
    hidden=project_for_human(s.state,s.definitions,'p2',s.character_names)
    assert all(cid not in str(hidden) for cid in top)
    s=restore(s); selected=top[:hearts] if take else ()
    answer(s,selected)
    remaining=tuple(cid for cid in top if cid not in selected)
    if remaining:
        s=restore(s); answer(s,tuple(reversed(remaining)))
        assert s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:len(remaining)]==tuple(reversed(remaining))
    assert len(hand(s.state,'p1'))==before+len(selected)
    assert not any((ref.special_key or '').startswith('committed:xinzhan:') and z.card_ids for ref,z in s.state.zones.items())
    assert s.state.play_usage.count('skill.xinzhan')==1


def test_xinzhan_equal_max_hp_is_illegal():
    s=game(); active(s,'ma_su'); s.state.players['p1'].max_hp=len(hand(s.state,'p1'))
    with pytest.raises(InvalidCardUse): s.engine.start_action(YJSkillAction('xinzhan','p1','xinzhan'))


@pytest.mark.parametrize('killer',[None,'p1','p2'])
def test_huilei_death_killer_discard_before_rebel_reward(killer):
    s=game(); active(s,'ma_su'); s.state.players['p1'].identity=Identity.REBEL
    put(s,'equipment.armor.eight_trigrams','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    old=set(hand(s.state,'p2'))|set(equipped_cards(s.state,'p2'))
    s.engine.start_action(DeathAction('death','p1',killer)); s=drain(s)
    if killer=='p2':
        assert old.isdisjoint(hand(s.state,'p2')) and not equipped_cards(s.state,'p2')
        assert len(hand(s.state,'p2'))==3
        events=s.events.events
        cleanup=[i for i,e in enumerate(events) if ':huilei:' in e.event_id]
        reward=next(i for i,e in enumerate(events) if isinstance(e,KillRewardEvent))
        assert max(cleanup)<reward
    else:
        assert old <= set(hand(s.state,'p2'))|set(equipped_cards(s.state,'p2'))


@pytest.mark.parametrize('both',[False,True])
def test_ganlu_atomic_same_slot_multiple_slots_mid_request_restore(both):
    s=game(); active(s,'wu_guotai'); s.state.players['p1'].hp=2
    a=put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    armor=put(s,'equipment.armor.eight_trigrams','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    b=put(s,'equipment.weapon.qinggang_sword','p3',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON) if both else None
    s.engine.start_action(YJSkillAction('ganlu','p1','ganlu'))
    s=restore(s); answer(s,'p2'); s=restore(s); answer(s,'p3')
    s=restore(s)
    assert set(equipped_cards(s.state,'p3'))=={a,armor}
    assert equipped_cards(s.state,'p2')==((b,) if both else ())
    assert s.state.play_usage.count('skill.ganlu')==1


def test_ganlu_illegal_count_not_offered_and_exchange_invalid_has_no_effects():
    s=game(); active(s,'wu_guotai')
    put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    s.engine.start_action(YJSkillAction('ganlu','p1','ganlu')); answer(s,'p3')
    assert 'p2' not in s.engine.pending_request.allowed_player_ids
    moves=s.engine.reaction_provider.__self__; before=snapshot_session(s)
    with pytest.raises(InvalidCardMove): moves.exchange_equipment(s.state,EquipmentExchangeTransaction('bad',('p2','p2'),'p1'))
    assert snapshot_session(s)==before


def test_exchange_silver_lion_xiaoji_and_xuanfeng_departure_reactions():
    s=game(); active(s,'wu_guotai'); s.state.players['p1'].hp=2
    s.state.players['p2'].character_id='sunshangxiang'; s.state.players['p2'].hp=2
    s.state.players['p3'].character_id='yj2011_ling_tong'
    put(s,'equipment.armor.silver_lion','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    put(s,'equipment.weapon.crossbow','p3',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    before=len(hand(s.state,'p2'))
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    s.engine.start_action(YJSkillAction('ganlu','p1','ganlu')); answer(s,'p2'); answer(s,'p3')
    assert s.state.players['p2'].hp==3
    # Xiaoji's optional draw and Xuanfeng remain ordinary resumable reactions.
    seen=[]
    while s.engine.pending_request:
        r=s.engine.pending_request; seen.append(r.prompt); s=restore(s)
        answer(s,True if '枭姬' in r.prompt else r.timeout_value())
    assert len(hand(s.state,'p2'))==before+2
    assert any('旋风' in text for text in seen)


@pytest.mark.parametrize('definition,healed',[('basic.slash',False),('trick.duel',True),('equipment.weapon.crossbow',True)])
def test_buyi_dying_choice_card_type_restore_and_privacy(definition,healed):
    s=game(); active(s,'wu_guotai'); s.state.players['p2'].hp=1
    cid=put(s,definition,'p2')
    s.engine.start_action(MilitaryDamageAction('fatal','p3','p2',1)); answer(s,True)
    room=MultiplayerRoom(); room.session=s
    r=s.engine.pending_request; payload=room._request_payload(r)
    assert cid not in str(payload)
    room=restore_room(snapshot_room(room)); s=room.session
    answer(s,cid); s=drain(s)
    assert s.state.players['p2'].is_alive==healed
    if healed: assert s.state.players['p2'].hp==1
    assert any(isinstance(e,Event) and e.event_type=='card_revealed' and e.metadata['card_id']==cid for e in s.events.events)


@pytest.mark.parametrize('choice',['draw','use_slash'])
def test_mingce_gift_virtual_slash_normal_response_or_draw(choice):
    s=game(); active(s,'chen_gong'); cid=put(s,'basic.slash')
    before=len(hand(s.state,'p2'))
    s.engine.start_action(YJSkillAction('mingce','p1','mingce'))
    s=restore(s); answer(s,cid); s=restore(s); answer(s,'p2')
    s=restore(s); answer(s,'p3'); s=restore(s); answer(s,choice)
    if choice=='use_slash':
        assert s.engine.pending_request.required_definition_id=='basic.dodge'
    s=drain(s)
    assert cid in hand(s.state,'p2')
    assert s.state.players['p3'].hp==(3 if choice=='use_slash' else 4)
    assert len(hand(s.state,'p2'))==before+(1 if choice=='use_slash' else 2)


@pytest.mark.parametrize('own_turn',[False,True])
def test_zhichi_first_damage_then_slash_and_non_delayed_effect_immunity(own_turn):
    s=game(); active(s,'chen_gong')
    s.state.current_player_id='p1' if own_turn else 'p2'
    s.engine.start_action(MilitaryDamageAction('first','p2','p1',1))
    assert s.state.players['p1'].hp==3 and protected(s.state,'p1')==(not own_turn)
    s=restore(s); cid=put(s,'basic.slash','p2')
    s.engine.start_action(MilitaryStrike('slash','p2','p1',cid,'basic.dodge')); s=drain(s)
    assert s.state.players['p1'].hp==(2 if own_turn else 3)
    s.engine.start_action(TargetTrick('trick','p2','p1',cid,'trick.iron_chain'))
    assert s.state.players['p1'].chained==own_turn
    clear_turn(s.state); assert not protected(s.state,'p1')


@pytest.mark.parametrize('ranks,win',[( (13,1),True),((1,13),False),((7,7),False)])
def test_xianzhen_pindian_snapshot_result_and_scoped_quota(ranks,win):
    s=game(); active(s,'gao_shun')
    a=put(s,'basic.dodge'); b=put(s,'basic.dodge','p3')
    s.state.cards[a]=replace(s.state.cards[a],rank=ranks[0]); s.state.cards[b]=replace(s.state.cards[b],rank=ranks[1])
    s.engine.start_action(YJSkillAction('xianzhen','p1','xianzhen')); answer(s,'p3')
    s=restore(s); answer(s,a); s=restore(s); answer(s,b); s=restore(s)
    assert scoped_target(s.state,'p1','p3')==win
    slash=put(s,'basic.slash'); validator=s.engine.registry.handler_for(UseCardAction('probe','p1',slash)).validator
    if win:
        put(s,'equipment.armor.eight_trigrams','p3',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
        s.state.play_usage.record('basic.slash')
        assert validator.target_candidates(s.state,'p1',slash)==('p3',)
        s.engine.start_action(UseCardAction('hit','p1',slash,('p3',)))
        assert s.engine.pending_request.request_type is RequestType.RESPOND_WITH_CARD
        assert '八卦' not in s.engine.pending_request.prompt
        s=drain(s)
        assert s.state.players['p3'].hp==3 and s.state.play_usage.count('basic.slash')==1
    else:
        assert not validator.can_offer(s.state,'p1',slash)
    clear_turn(s.state)
    assert not any(k.startswith('yj_xianzhen') for k in s.state.players['p1'].marks)


def test_jinjiu_wine_is_slash_use_and_response_no_self_rescue():
    from sanguosha.engine.response import RespondWithCardAction
    s=game(); active(s,'gao_shun'); cid=put(s,'basic.wine')
    s.engine.start_action(UseCardAction('wine-slash','p1',cid,('p2',))); s=drain(s)
    assert s.state.players['p2'].hp==3 and not s.state.players['p1'].marks.get('wine')
    assert s.state.play_usage.count('basic.slash')==1
    cid=put(s,'basic.wine')
    s.engine.start_action(RespondWithCardAction('respond','p1','basic.slash','source','请打出杀'))
    assert cid in s.engine.pending_request.eligible_card_ids
    s=restore(s); answer(s,cid)
    assert any(isinstance(e,CardRespondedEvent) and e.card_id==cid and e.response_definition_id=='basic.slash' for e in s.events.events)
    cid=put(s,'basic.wine'); s.state.players['p1'].hp=1
    s.engine.start_action(MilitaryDamageAction('fatal','p2','p1',1))
    assert cid not in s.engine.pending_request.eligible_card_ids


@pytest.mark.parametrize('skill,general,target',[('xuanhuo','fa_zheng','p2'),('buyi','wu_guotai','p2')])
def test_private_hand_ai_invariant_under_enemy_card_changes(skill,general,target):
    s=game(); active(s,general)
    if skill=='buyi': s.state.players[target].hp=0
    s.engine.start_action(YJSkillAction('skill','p1',skill,target))
    answer(s,True)
    if skill=='xuanhuo':
        answer(s,target); answer(s,'p3'); answer(s,'decline')
    r=s.engine.pending_request; first=s.ai.decide(s.state,r)
    for cid in r.eligible_card_ids:
        s.state.cards[cid]=replace(s.state.cards[cid],definition_id='basic.peach',rank=13)
    assert s.ai.decide(s.state,r)==first
