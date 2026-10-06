from dataclasses import replace
import pytest
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL, ALL_SKILL_CATALOGUE
from sanguosha.engine.events import CardMovedEvent, Event
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_tricks import TargetTrick
from sanguosha.multiplayer.room import Controller, RoomError
from sanguosha.model.enums import Suit, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.snapshot import snapshot_session, restore_session
from test_t6_military_basics import game, put
from test_t18a7_flow import room_for, send

def test_108_descriptions_are_complete_and_original():
    assert len(PLAYABLE_GENERAL_POOL)==108
    registry={s.id:s for s in ALL_SKILL_CATALOGUE}
    for general in PLAYABLE_GENERAL_POOL:
        for sid in general.skill_ids:
            s=registry[sid]
            assert s.name and len(s.description)>=10,(general.id,sid)
            assert not any(word in s.description.lower() for word in ('todo','placeholder','规则摘要','待补','generic'))

@pytest.mark.parametrize('zone',[ZoneType.HAND,ZoneType.EQUIPMENT,ZoneType.JUDGMENT])
def test_discard_becomes_public_only_after_move(zone):
    s=game();room=room_for(s);cid=put(s,'equipment.weapon.crossbow' if zone is ZoneType.EQUIPMENT else 'basic.slash','p2')
    ref=ZoneRef(zone,'p2',EquipmentSlot.WEAPON if zone is ZoneType.EQUIPMENT else None)
    if zone is not ZoneType.HAND:
        CardMoveService(s.events).move(s.state,CardMove('move-before',(cid,),ZoneRef(ZoneType.HAND,'p2'),ref,CardMoveReason.SYSTEM))
    event=CardMovedEvent('public-discard',(cid,),ref,ZoneRef(ZoneType.DISCARD_PILE),'discard','p1','dismantle')
    assert room._public_event(event)['cards'][0]['name']
    assert room._public_event(event)['player_id']=='p2'
    hidden=replace(event,to_zone=ZoneRef(ZoneType.HAND,'p1'))
    assert room._public_event(hidden) is None

@pytest.mark.parametrize('matching',[True,False])
def test_fire_attack_reveal_snapshot_and_result(matching):
    s=game();room=room_for(s);cid=put(s,'basic.peach','p2');cost=put(s,'basic.slash')
    s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.HEART)
    s.state.cards[cost]=replace(s.state.cards[cost],suit=Suit.HEART if matching else Suit.CLUB)
    # Fixture no other matching cards.
    for c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')):
        if c!=cost:s.state.cards[c]=replace(s.state.cards[c],suit=Suit.CLUB)
    fire=put(s,'trick.fire_attack')
    s.engine.start_action(TargetTrick('fire-case','p1','p2',fire,'trick.fire_attack'))
    r=s.engine.pending_request;s.engine.submit_decision(Decision(r.request_id,r.player_id,cid))
    assert any(e.event_type=='card_revealed' for e in s.events.events if isinstance(e,Event))
    restored=restore_session(snapshot_session(s));room.session=restored
    view=room._named_projection(__import__('sanguosha.projection',fromlist=['project_for_human']).project_for_human(restored.state,restored.definitions,'p3',restored.character_names),'p3')
    assert view['public_reveal']['cards'][0]['name']=='桃'
    r=restored.engine.pending_request
    if matching: assert cost in r.eligible_card_ids
    restored.engine.submit_decision(Decision(r.request_id,r.player_id,cost if matching else PASS_RESPONSE))
    assert restored.engine.stack.is_empty()
    if not matching: assert any(isinstance(e,Event) and e.event_type=='fire_attack_result' for e in restored.events.events)

@pytest.mark.parametrize('definition,allowed',[('trick.savage_assault',True),('trick.archery_attack',True),('trick.amazing_grace',True),('trick.god_salvation',True),('trick.dismantlement',False),('trick.fire_attack',False),('trick.duel',False)])
def test_root_skip_scope(definition,allowed):
    s=game();room=room_for(s);put(s,'trick.nullification');put(s,'basic.slash','p2')
    c=put(s,definition);targets=() if allowed else ('p2',)
    s.engine.start_action(UseCardAction('scope-'+definition,'p1',c,targets));room.pump()
    r=s.engine.pending_request
    assert room._request_payload(r)['allow_root_trick_pass'] is allowed
    if not allowed:
        with pytest.raises(RoomError):room.submit(r.player_id,Decision(r.request_id,r.player_id,'ui.pass_root_trick'))

def test_short_disconnect_and_token_takeover(monkeypatch):
    s=game();room=room_for(s);seat=room.seats['p2'];seat.token='stable-token'
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:100)
    room.disconnect('p2');room.poll();assert seat.controller is Controller.HUMAN
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:116)
    monkeypatch.setattr(room,'pump',lambda **kwargs:None)
    room.poll();assert seat.controller is Controller.AI and seat.ai_controlled
    assert seat.token=='stable-token'
    room.join('return',lambda _:None,token='stable-token')
    assert seat.controller is Controller.HUMAN and not seat.ai_controlled and seat.connected
    assert s.state.players['p2'] is room.session.state.players['p2']


def test_public_discard_reaches_every_viewer_and_reconnect_history():
    s=game();room=room_for(s);received={pid:[] for pid in room.seats}
    for pid,seat in room.seats.items():seat.send=received[pid].append
    cid=put(s,'basic.peach','p2');room._seen_events=len(s.events.events)
    s.events.record(CardMovedEvent('all-viewers-discard',(cid,),ZoneRef(ZoneType.HAND,'p2'),ZoneRef(ZoneType.DISCARD_PILE),'discard','p1','dismantle'))
    room._sync()
    for messages in received.values():
        events=[m['event'] for m in messages if m['type']=='PUBLIC_EVENT' and m['event']['kind']=='DiscardEvent']
        assert len(events)==1 and events[0]['cards'][0]['name']=='桃'
        assert events[0]['cards'][0]['card_id']=='public-card'
    from sanguosha.projection import project_for_human
    for pid in room.seats:
        view=room._named_projection(project_for_human(s.state,s.definitions,pid,s.character_names),pid)
        assert view['public_card_history'][-1]['cards'][0]['name']=='桃'


def test_grace_takeover_really_resolves_pending_then_token_returns(monkeypatch):
    from sanguosha.engine.phases import PhaseAction
    from sanguosha.model.enums import Phase
    s=game();room=room_for(s);seat=room.seats['p2'];seat.token='return-token'
    original_player=s.state.players['p2'];original_player.marks['takeover-proof']=7
    from sanguosha.model.usage import PlayUsageState
    s.state.current_player_id='p2';s.state.play_usage=PlayUsageState('p2',1)
    s.engine.start_action(PhaseAction('takeover-play','p2',Phase.PLAY));room.pump()
    old=s.engine.pending_request.request_id
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:100)
    room.disconnect('p2');room.poll();assert s.engine.pending_request.request_id==old
    monkeypatch.setattr('sanguosha.multiplayer.room.time.time',lambda:116)
    room.poll()
    assert seat.ai_controlled and seat.controller is Controller.AI
    assert s.engine.pending_request is None or s.engine.pending_request.request_id!=old
    room.join('returning',lambda _:None,token='return-token')
    assert not seat.ai_controlled and seat.controller is Controller.HUMAN
    assert s.state.players['p2'] is original_player and original_player.marks['takeover-proof']==7


def test_tcp_server_close_releases_connected_clients():
    import asyncio
    from sanguosha.multiplayer.transport import GameClient,GameServer
    async def scenario():
        server=GameServer(host='127.0.0.1',port=0)
        await server.start();client=GameClient('127.0.0.1',server.port)
        try:
            await client.connect('shutdown-test')
            await asyncio.wait_for(server.close(),2)
            while await asyncio.wait_for(client.reader.readline(),2):pass
        finally:
            await client.close();await server.close()
    asyncio.run(scenario())
