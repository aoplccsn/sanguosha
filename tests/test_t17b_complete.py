"""Preproduction acceptance of all eleven generals in both military modes."""
import pytest
from sanguosha.session import GameSession
from sanguosha.content.characters.yj2011 import YJ2011_DEV_GENERALS
from sanguosha.model.enums import Identity, Phase
from sanguosha.model.state import GameStatus
from sanguosha.model.usage import PlayUsageState
from sanguosha.engine.requests import Decision, RequestType
from sanguosha.engine.yj2011_tier3 import YJSkillAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.model.enums import Suit
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.snapshot import snapshot_session,restore_session
from sanguosha.multiplayer.room import MultiplayerRoom,RoomPhase,Controller
from sanguosha.room_snapshot import snapshot_room,restore_room
from test_t6_military_basics import put

GENERALS=tuple(str(c.id) for c in YJ2011_DEV_GENERALS)


@pytest.mark.parametrize('mode',['military-five','military-eight'])
@pytest.mark.parametrize('seed',range(40))
def test_all_eleven_forced_ai_matches_with_live_skill_restore(mode,seed):
    s=GameSession.new_game(seed=300+seed,military=True,five_generals=True,mode_id=mode)
    order=GENERALS[seed%11:]+GENERALS[:seed%11]
    for pid,gid in zip(s.state.seat_order,order):
        c=s.skills.characters[gid]; p=s.state.players[pid]
        p.character_id=gid; p.max_hp=c.max_hp+int(p.identity is Identity.LORD); p.hp=p.max_hp
        s.character_names[pid]=c.name
    s.human_id='ai-only'; restored=set()
    for _ in range(50000):
        if s.state.status is GameStatus.FINISHED: break
        request=s.engine.pending_request
        if request:
            skill=next((name for name in ('落英','酒诗','恩怨','眩惑','心战','甘露','补益','明策','陷阵','拼点','伤逝','举荐','旋风','破军') if name in request.prompt),None)
            if skill and skill not in restored:
                s=restore_session(snapshot_session(s)); assert s.engine.pending_request==request
                restored.add(skill)
        assert s.step_auto()
    else: pytest.fail('match did not resolve')
    assert s.state.victory is not None and s.engine.pending_request is None
    assert s.engine.stack.is_empty()
    assert not any(k.startswith('yj_xianzhen') or k=='yj_zhichi' for p in s.state.players.values() for k in p.marks)


@pytest.mark.parametrize('mode',['military-five','military-eight'])
@pytest.mark.parametrize('skill',['luoying','jiushi_return','enyuan_damage','ganlu','buyi','mingce','xianzhen'])
def test_two_humans_ai_room_skill_reconnect_and_timeout(mode,skill):
    wire={'p1':[],'p2':[]}; room=MultiplayerRoom(mode_id=mode,seed=19)
    p1,t1=room.join('host',wire['p1'].append); p2,t2=room.join('guest',wire['p2'].append)
    room.ready(p2,True); room.start(p1)
    for pid in (p1,p2):
        r=room.draft_requests[pid]
        choice=next(c for c in r.choices if c not in room.pregame.generals.values())
        room.submit(pid,Decision(r.request_id,pid,choice))
    assert sum(x.controller is Controller.HUMAN for x in room.seats.values())==2
    # Install a deterministic shared-engine skill fixture in the established
    # room; transport, tokens, opaque mapping and deadlines remain real.
    room.session=GameSession.new_game(military=True,five_generals=True,mode_id=mode,seed=19)
    s=room.session
    for p in s.state.players.values(): p.character_id='sunquan'
    general={'luoying':'cao_zhi','jiushi_return':'cao_zhi','enyuan_damage':'fa_zheng','ganlu':'wu_guotai',
             'buyi':'wu_guotai','mingce':'chen_gong','xianzhen':'gao_shun'}[skill]
    s.state.players[p1].character_id='yj2011_'+general
    s.state.current_player_id=p1; s.state.current_phase=Phase.PLAY
    s.state.turn_number=9; s.state.play_usage=PlayUsageState(p1,9)
    cards=()
    if skill=='luoying':
        cid=put(s,'basic.slash',p2)
        from dataclasses import replace
        s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.CLUB)
        from sanguosha.engine.card_moves import CardMoveService,CardMove,CardMoveReason
        CardMoveService(s.events).move(s.state,CardMove('setup-discard',(cid,),ZoneRef(ZoneType.HAND,p2),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,p2))
        cards=(cid,)
    if skill=='mingce': put(s,'basic.slash',p1)
    if skill=='buyi': s.state.players[p2].hp=0; put(s,'trick.duel',p2)
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    s.engine.start_action(YJSkillAction('room-skill',p1,skill,p2 if skill in ('enyuan_damage','buyi') else None,cards))
    seen=[]
    while s.engine.pending_request:
        r=s.engine.pending_request; seen.append(r.prompt)
        payload=room._request_payload(r)
        deadline=room.request_deadline
        room=restore_room(snapshot_room(room)); s=room.session
        assert room.request_deadline==deadline
        room.join('host',wire['p1'].append,token=t1); room.join('guest',wire['p2'].append,token=t2)
        assert s.engine.pending_request==r
        restored_payload=room._request_payload(r)
        assert {k:v for k,v in restored_payload.items() if k!='remaining_ms'}=={k:v for k,v in payload.items() if k!='remaining_ms'}
        # Exercise concrete choices, then time out the final response/offer.
        if r.request_type is RequestType.YES_NO: value=True
        elif r.request_type is RequestType.CHOOSE_OPTION: value='give' if 'give' in r.choices else 'draw' if 'draw' in r.choices else r.choices[0]
        elif r.request_type is RequestType.RESPOND_WITH_CARD: value=r.timeout_value()
        elif r.request_type is RequestType.CHOOSE_CARD: value=payload['eligible_card_ids'][0]
        else: value=r.timeout_value()
        decision=room._resolve_hidden_choice(r,Decision(r.request_id,r.player_id,value))
        s.engine.submit_decision(decision)
    assert s.engine.stack.is_empty() and seen
    if skill=='xianzhen': assert any('拼点' in text for text in seen)


@pytest.mark.parametrize('mode',['military-five','military-eight'])
def test_two_humans_ai_room_real_deadline_timeout(mode):
    room=MultiplayerRoom(mode_id=mode,seed=7)
    p1,t1=room.join('host',lambda _:None); p2,t2=room.join('guest',lambda _:None)
    room.ready(p2,True); room.start(p1)
    for pid in (p1,p2):
        r=room.draft_requests[pid]
        room.submit(pid,Decision(r.request_id,pid,next(c for c in r.choices if c not in room.pregame.generals.values())))
    old=room.session.engine.pending_request
    room.request_deadline=0; room=restore_room(snapshot_room(room))
    room.join('host',lambda _:None,token=t1); room.join('guest',lambda _:None,token=t2)
    room.poll()
    assert room.session.engine.pending_request is None or room.session.engine.pending_request.request_id!=old.request_id
