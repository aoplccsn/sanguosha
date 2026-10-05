"""Real root trick, wire, snapshot, public targets and unified decision gateway."""
from dataclasses import replace
import pytest
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.events import TrickTargetsDeclaredEvent
from sanguosha.engine.requests import Decision, RequestType, PASS_RESPONSE
from sanguosha.multiplayer.room import MultiplayerRoom, Controller, RoomPhase, RoomError
from sanguosha.multiplayer.protocol import decision_from_wire
from sanguosha.room_snapshot import snapshot_room, restore_room
from sanguosha.model.enums import EquipmentSlot, PlayerStatus, Identity
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.decisions.ai import AIDecisionProvider
from test_t6_military_basics import game, put

def room_for(s):
    room=MultiplayerRoom(); room.session=s; room.phase=RoomPhase.IN_GAME
    room.host_id='p1'
    for seat in room.seats.values(): seat.controller=Controller.HUMAN; seat.connected=True
    return room

def send(room, value):
    r=room.session.engine.pending_request
    room.submit(r.player_id, Decision(r.request_id,r.player_id,value))

def test_plain_pass_only_current_request_and_counter_chain_reasks():
    s=game(); counter=put(s,'trick.nullification'); other=put(s,'trick.nullification','p2')
    room=room_for(s)
    s.engine.start_action(UseCardAction('aoe','p1',put(s,'trick.savage_assault')))
    room.pump(); first=s.engine.pending_request
    send(room,PASS_RESPONSE)
    assert s.engine.pending_request.player_id=='p2'
    send(room,other)
    while s.engine.pending_request.player_id!='p1': send(room,s.engine.pending_request.timeout_value())
    assert s.engine.pending_request.request_id!=first.request_id
    assert counter in s.engine.pending_request.eligible_card_ids
    assert not s.state.metadata.get('nullification_passes')

def test_root_pass_all_targets_and_counter_chain_snapshot_next_trick():
    from sanguosha.engine.phases import PhaseAction
    from sanguosha.model.enums import Phase
    s=game(); counter=put(s,'trick.nullification'); other=put(s,'trick.nullification','p2')
    aoe=put(s,'trick.savage_assault'); independent=put(s,'trick.ex_nihilo')
    room=room_for(s)
    s.engine.start_action(PhaseAction('same-play-phase','p1',Phase.PLAY))
    room.pump(); send(room,'use:'+aoe)
    r=s.engine.pending_request
    d=decision_from_wire({'request_id':r.request_id,'value':{'pass':True,'scope':'root_trick'}},'p1')
    room.submit('p1',d)
    root=s.nullification_window_id()
    assert s.state.metadata['nullification_passes'][root]==['p1']
    restored=restore_room(snapshot_room(room))
    assert restored.session.state.metadata['nullification_passes']==s.state.metadata['nullification_passes']
    assert restored.request_deadline==room.request_deadline
    # Continue on the restored authoritative stack; bind its human connection.
    room=restored; s=room.session
    for seat in room.seats.values():seat.connected=True
    send(room,other)
    for _ in range(150):
        r=s.engine.pending_request
        assert r is not None
        if r.request_type is RequestType.CHOOSE_OPTION and 'end_play_phase' in r.choices: break
        assert not (r.player_id=='p1' and r.required_definition_id=='trick.nullification')
        send(room,r.timeout_value())
    else: raise AssertionError('root trick did not finish')
    assert s.state.turn_number==1 and s.state.current_player_id=='p1'
    assert not s.state.metadata['nullification_passes']
    assert not s.declined_nullification_windows
    send(room,'use:'+independent)
    r=s.engine.pending_request
    assert s.state.turn_number==1
    assert r.player_id=='p1' and counter in r.eligible_card_ids

@pytest.mark.parametrize('definition',['trick.savage_assault','trick.archery_attack'])
def test_authoritative_fanout_excludes_dead_and_immune(definition):
    s=game(); s.state.players['p3'].status=PlayerStatus.DEAD
    put(s,'equipment.armor.vine','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.engine.start_action(UseCardAction('targets','p1',put(s,definition)))
    e=next(e for e in s.events.events if isinstance(e,TrickTargetsDeclaredEvent))
    assert e.target_ids==('p4','p5')
    room=room_for(s); cue=room._public_event(e)
    assert cue['target_ids']==['p4','p5']
    context=room._combat_context()
    assert context['target_ids']==['p4','p5']
    assert context['current_target_id']=='p4'

def test_ai_counter_value_parity_and_no_hidden_information():
    s=game(); ai=AIDecisionProvider('human'); counter=put(s,'trick.nullification')
    s.engine.start_action(UseCardAction('test','p1',put(s,'trick.ex_nihilo')))
    r=s.engine.pending_request
    context={'definition_id':'trick.ex_nihilo','current_target_id':'p1','cancelled':False}
    assert ai.decide(s.state,r,response_context=context).value is PASS_RESPONSE
    context['cancelled']=True
    assert ai.decide(s.state,r,response_context=context).value==counter
    before=ai.decide(s.state,r,response_context=context).value
    for pid in s.state.players:
        if pid=='p1': continue
        for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,pid)):
            s.state.cards[cid]=replace(s.state.cards[cid],definition_id='basic.peach')
    assert ai.decide(s.state,r,response_context=context).value==before

def test_all_genuine_request_types_wait_once_and_forced_pass_does_not(monkeypatch):
    from sanguosha.engine.requests import PendingRequest
    clock=[1000.]; monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:clock[0])
    for kind,fields in [(RequestType.YES_NO,{}),(RequestType.RESPOND_WITH_CARD,{'eligible_card_ids':('virtual:test',),'allow_pass':True}),
                        (RequestType.CHOOSE_PLAYER,{'allowed_player_ids':('p2',)}),
                        (RequestType.CHOOSE_PLAYERS,{'allowed_player_ids':('p2','p3'),'max_count':2}),
                        (RequestType.CHOOSE_CARD,{'eligible_card_ids':('test',)}),
                        (RequestType.CHOOSE_CARDS,{'eligible_card_ids':('test',)}),
                        (RequestType.CHOOSE_OPTION,{'choices':('virtual:test','end_play_phase')})]:
        s=game(); room=room_for(s); room.ai_presentation=True; room.seats['p1'].controller=Controller.AI
        r=PendingRequest('gateway-'+kind.value,'p1',kind,'','test','frame',**fields)
        s.engine.pending_request=r
        room.pump(); deadline=room.ai_deadline
        assert deadline>clock[0]
        room.pump(); assert room.ai_deadline==deadline
        assert sum(getattr(e,'event_type','')=='ai_thinking' for e in s.events.events)==1

def test_scope_command_wrong_response_rejected_without_preference():
    s=game(); room=room_for(s)
    s.engine.start_action(UseCardAction('slash','p1',put(s,'basic.slash'),('p2',)))
    r=s.engine.pending_request
    with pytest.raises(RoomError): room.submit(r.player_id,Decision(r.request_id,r.player_id,'ui.pass_root_trick'))
    assert not s.state.metadata.get('nullification_passes')
