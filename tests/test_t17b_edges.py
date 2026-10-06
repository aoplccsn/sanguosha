from dataclasses import replace
import pytest
from sanguosha.engine.card_moves import CardMove,CardMoveReason,EquipmentExchangeTransaction,InvalidCardMove
from sanguosha.engine.yj2011_tier3 import YJSkillAction,hand,equipped_cards,protected,scoped_target
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_basics import MilitaryDamageAction,MilitaryStrike
from sanguosha.engine.turns import TurnAction
from sanguosha.engine.death import DeathAction
from sanguosha.engine.events import Event
from sanguosha.engine.requests import RequestType
from sanguosha.engine.distance import DistanceSystem
from sanguosha.model.enums import EquipmentSlot,Phase,Identity
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.snapshot import snapshot_session
from test_t17b_tier1 import game,answer
from test_t17b_tier3 import active,restore,drain
from test_t6_military_basics import put


def test_enyuan_cross_hand_equipment_single_batch_and_no_mixed_source_merge():
    s=game(); active(s,'fa_zheng')
    cid=put(s,'basic.slash','p2'); equip=put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    moves=s.engine.reaction_provider.__self__; s.state.metadata['reaction_event_cursor']=len(s.events.events)
    moves.obtain_cards(s.state,(cid,equip),'p1','p1','obtain')
    offer=moves.next_reaction(s.state)
    assert offer.skill=='enyuan_gain' and offer.target_id=='p2'
    assert moves.next_reaction(s.state) is None
    a=put(s,'basic.slash','p2'); b=put(s,'basic.slash','p3')
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    moves.obtain_cards(s.state,(a,b),'p1','p1','mixed')
    assert moves.next_reaction(s.state) is None


def test_exchange_multislot_xuanfeng_triggers_once_per_owner():
    s=game(); active(s,'wu_guotai'); s.state.players['p2'].character_id='yj2011_ling_tong'
    for definition,slot in [('equipment.weapon.crossbow',EquipmentSlot.WEAPON),('equipment.armor.eight_trigrams',EquipmentSlot.ARMOR)]:
        put(s,definition,'p2',ZoneType.EQUIPMENT,slot)
    moves=s.engine.reaction_provider.__self__; s.state.metadata['reaction_event_cursor']=len(s.events.events)
    moves.exchange_equipment(s.state,EquipmentExchangeTransaction('exchange',('p2','p3'),'p1'))
    offer=moves.next_reaction(s.state)
    assert type(offer).__name__=='XuanfengAction'
    assert moves.next_reaction(s.state) is None
    assert len(equipped_cards(s.state,'p3'))==2


def test_exchange_validation_late_slot_rolls_back_without_events_or_reactions():
    s=game(); active(s,'wu_guotai')
    put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    armor=put(s,'equipment.armor.eight_trigrams','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.state.zones[ZoneRef(ZoneType.HAND,'p3')].card_ids.append(armor)
    before=snapshot_session(s); moves=s.engine.reaction_provider.__self__
    with pytest.raises(InvalidCardMove): moves.exchange_equipment(s.state,EquipmentExchangeTransaction('bad',('p2','p3'),'p1'))
    assert snapshot_session(s)==before and not moves.reactions


def test_xianzhen_spear_virtual_slash_exempt_target_does_not_consume_normal_quota():
    from sanguosha.engine.view_as import UseSpear
    s=game(); active(s,'gao_shun'); s.state.players['p1'].marks['yj_xianzhen:p3']=s.state.turn_number
    put(s,'equipment.weapon.serpent_spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    costs=hand(s.state,'p1')[:2]
    s.engine.start_action(UseSpear('spear','p1')); answer(s,costs); answer(s,'p3'); s=drain(s)
    assert s.state.play_usage.count('basic.slash')==0
    assert s.state.players['p3'].hp==3
    assert DistanceSystem(s.definitions).distance_between(s.state,'p1','p3')==1


@pytest.mark.parametrize('source_death',[False,True])
def test_zhichi_and_xianzhen_all_players_clear_at_real_turn_end(source_death):
    s=game(); active(s,'gao_shun')
    s.state.players['p1'].marks['yj_xianzhen:p3']=s.state.turn_number
    s.state.players['p3'].marks['yj_zhichi']=s.state.turn_number
    if source_death:
        from sanguosha.model.enums import Identity
        s.state.players['p1'].identity=Identity.LOYALIST
        s.state.players['p2'].identity=Identity.LORD
        s.engine.start_action(DeathAction('death','p1',None)); s=drain(s)
    # A face-down owner ends a turn without phase bodies, using the real cleanup.
    pid='p2' if source_death else 'p1'; s.state.players[pid].face_up=False
    s.engine.start_action(TurnAction('end',pid))
    assert not any(k.startswith('yj_xianzhen') or k=='yj_zhichi' for p in s.state.players.values() for k in p.marks)


def test_jiushi_initial_face_down_fatal_rescue_flip_is_after_dying_resolution():
    from sanguosha.engine.requests import PASS_RESPONSE
    s=game(); active(s,'cao_zhi'); s.state.players['p1'].face_up=False; s.state.players['p1'].hp=1
    peach=put(s,'basic.peach','p2')
    s.engine.start_action(MilitaryDamageAction('fatal','p3','p1',1))
    assert '酒诗' not in s.engine.pending_request.prompt
    answer(s,PASS_RESPONSE); answer(s,peach)
    assert '酒诗' in s.engine.pending_request.prompt and s.state.players['p1'].hp==1
    s=restore(s); answer(s,True); assert s.state.players['p1'].face_up


@pytest.mark.parametrize('scenario',['replacement','death','skill_move'])
def test_luoying_semantic_boundaries_for_equipment_death_and_system_move(scenario):
    from sanguosha.model.enums import Suit
    s=game(); active(s,'cao_zhi'); cid=put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.CLUB)
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    if scenario=='death':
        s.engine.start_action(DeathAction('death','p2',None)); assert s.engine.pending_request is None
        assert cid not in hand(s.state,'p1')
    else:
        moves=s.engine.reaction_provider.__self__
        moves.move(s.state,CardMove('move',(cid,),ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.WEAPON),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD if scenario=='replacement' else CardMoveReason.SYSTEM,'p2'))
        reaction=moves.next_reaction(s.state)
        assert (reaction is not None)==(scenario=='replacement')


def test_reveal_public_event_contains_only_selected_card_definition():
    from sanguosha.multiplayer.room import MultiplayerRoom
    s=game(); room=MultiplayerRoom(); room.session=s
    cid=put(s,'trick.duel','p2'); secret=put(s,'basic.peach','p2')
    event=Event('reveal','card_revealed','p2',metadata={'card_id':cid,'skill_id':'buyi'})
    payload=room._public_event(event)
    assert payload['definition_id']=='trick.duel' and '决斗' in payload['card_name']
    assert cid not in str(payload) and secret not in str(payload)
