"""T20 mode contracts at the authoritative room/engine boundaries."""
import json
import pytest
from sanguosha.game_modes import DUEL_1V1, TEAM_2V2
from sanguosha.session import GameSession
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase, Controller
from sanguosha.engine.requests import Decision, PendingRequest, RequestType, PASS_RESPONSE
from sanguosha.engine.death import DeathAction
from sanguosha.engine.identity import IdentitySystem
from sanguosha.engine.turn_order import next_scheduled_player, next_alive_player
from sanguosha.engine.distance import DistanceSystem
from sanguosha.model.enums import Identity
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.projection import project_for_human
from sanguosha.room_snapshot import snapshot_room, restore_room
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.general_draft import OVERPOWERED_SLOT_RATE, OVERPOWERED_WEIGHTS

MODES = (DUEL_1V1, TEAM_2V2)

@pytest.mark.parametrize('mode', MODES)
def test_public_sides_no_lord_standard_hands_distance_and_start(mode):
    s=GameSession.new_game(seed=20,military=True,five_generals=True,mode_id=mode.mode_id)
    assert len(s.state.players)==mode.seat_count
    assert not any(p.identity is Identity.LORD for p in s.state.players.values())
    assert s.state.players['p1'].max_hp==4
    assert all(len(s.state.cards_in(ZoneRef(ZoneType.HAND,pid)))==4 for pid in mode.seats)
    assert DistanceSystem().base_distance(s.state,'p1','p2')==1
    first=next_scheduled_player(s.state)
    assert first in mode.seats
    if mode is TEAM_2V2:
        assert first=='p1'
        assert [next_alive_player(s.state,p) for p in mode.seats]==['p2','p3','p4','p1']
    assert not s.skills.has(s.state,'p1','hujia')
    assert not s.skills.has(s.state,'p2','jijiang')
    restored=restore_session(snapshot_session(s))
    assert next_scheduled_player(restored.state)==first
    assert restored.state.metadata['teams']==s.state.metadata['teams']

@pytest.mark.parametrize('mode,count',[(DUEL_1V1,1),(DUEL_1V1,2),(TEAM_2V2,1),(TEAM_2V2,2),(TEAM_2V2,3),(TEAM_2V2,4)])
def test_room_draft_autofill_and_takeover_reclaim(mode,count):
    room=MultiplayerRoom(seed=2,mode_id=mode.mode_id,test_room=True)
    room.auto_step_budget=1;room.suspend_on_budget=True
    joined=[]
    for i in range(count):
        pid,token=room.join('human'+str(i),lambda _:None);joined.append((pid,token))
        if i:room.ready(pid,True)
    assert [pid for pid,_ in joined]==list(mode.seats[:count])
    if count>1:assert mode.team_for(joined[0][0])!=mode.team_for(joined[1][0])
    room.start(joined[0][0])
    assert sum(s.controller is Controller.AI for s in room.seats.values())==mode.seat_count-count
    assert len(room.draft_requests['p1'].choices)==108
    for pid,_ in joined:
        request=room.draft_requests[pid]
        choice=next(c for c in request.choices if c not in room.pregame.generals.values())
        room.submit(pid,Decision(request.request_id,pid,choice))
    assert room.phase in (RoomPhase.IN_GAME,RoomPhase.FINISHED)
    assert len(set(room.pregame.generals.values()))==mode.seat_count
    before=dict(room.session.state.metadata['teams'])
    generals=dict(room.pregame.generals)
    first=room.session.state.metadata['first_player_id']
    pid,token=joined[-1]
    room.disconnect(pid);room.seats[pid].disconnected_at-=room.reconnect_grace_seconds+1
    room.poll()
    assert room.seats[pid].ai_controlled
    restored=restore_room(snapshot_room(room));messages=[]
    assert restored.join('back',messages.append,token=token)==(pid,token)
    assert restored.seats[pid].controller is Controller.HUMAN
    assert restored.session.state.metadata['teams']==before
    assert restored.pregame.generals==generals
    assert restored.session.state.metadata['first_player_id']==first
    assert len(restored.seats)==mode.seat_count

@pytest.mark.parametrize('mode',MODES)
def test_death_terminal_clears_request_and_stack(mode):
    s=GameSession.new_game(military=True,mode_id=mode.mode_id)
    s.engine.start_action(DeathAction('death1','p1','p2'))
    if mode is TEAM_2V2:
        assert s.state.status is GameStatus.ACTIVE
        assert IdentitySystem().evaluate(s.state) is None
        assert next_alive_player(s.state,'p1')=='p2'
        s.engine.start_action(DeathAction('death2','p3','p2'))
    assert s.state.status is GameStatus.FINISHED
    assert s.state.victory.winner_ids==tuple(p for p in mode.seats if mode.team_for(p)=='B')
    assert s.engine.pending_request is None and s.engine.stack.is_empty()
    assert not s.step_auto()


def test_team_relation_targeting_rescue_and_private_hands():
    s=GameSession.new_game(military=True,five_generals=True,mode_id=TEAM_2V2.mode_id)
    assert [s.ai.relation(s.state,'p1',p) for p in TEAM_2V2.seats]==['SELF','ENEMY','ALLY','ENEMY']
    attack=PendingRequest('attack','p1',RequestType.CHOOSE_PLAYER,'杀：选择目标','a','f',allowed_player_ids=('p3','p2','p4'))
    assert s.ai.decide(s.state,attack).value in ('p2','p4')
    peach=next(cid for cid,c in s.state.cards.items() if c.definition_id=='basic.peach')
    rescue=PendingRequest('save','p1',RequestType.RESPOND_WITH_CARD,'濒死求桃','a','f',required_definition_id='basic.peach',eligible_card_ids=(peach,),allow_pass=True,subject_player_id='p3')
    assert s.ai.decide(s.state,rescue).value==peach
    from dataclasses import replace
    assert s.ai.decide(s.state,replace(rescue,subject_player_id='p2')).value is PASS_RESPONSE
    view=project_for_human(s.state,s.definitions,'p1',s.character_names)
    assert [p.team_id for p in view.players]==['A','B','A','B']
    assert [p.identity_label for p in view.players]==['A队','B队','A队','B队']
    assert not any(p.revealed_hand for p in view.players)
    wire=json.dumps([{'card_id':c.card_id} for c in view.hand])
    for pid in ('p2','p3','p4'):
        assert all(cid not in wire for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,pid)))
    # Team membership never follows the reordered turn seats or kingdom.
    s.state.seat_order=('p1','p3','p2','p4')
    assert s.ai.relation(s.state,'p1','p3')=='ALLY'
    assert s.ai.relation(s.state,'p1','p2')=='ENEMY'

@pytest.mark.parametrize('mode',MODES)
def test_draft_keeps_five_percent_slot_and_deterministic_candidates(mode):
    assert OVERPOWERED_SLOT_RATE==.05
    a=Pregame.create(91,mode.mode_id);b=Pregame.create(91,mode.mode_id)
    assert a.candidates==b.candidates and len(set(a.candidates))==10
    assert len(set(a.candidates)&OVERPOWERED_WEIGHTS.keys())<=1
    assert a.lord_id is None

@pytest.mark.parametrize('mode',MODES)
def test_cards_still_allow_friendly_targets(mode):
    s=GameSession.new_game(military=True,five_generals=True,mode_id=mode.mode_id)
    from sanguosha.engine.military_tricks import MilitaryTrickRule
    candidates=MilitaryTrickRule('trick.iron_chain',DistanceSystem(),s.skills).target_candidates(s.state,'p1')
    assert set(candidates)==set(mode.seats)

@pytest.mark.parametrize('mode', MODES)
def test_tamo_reorders_every_nonlord_without_switching_teams(mode):
    setup=Pregame.create(20,mode.mode_id)
    setup.generals=dict(zip(mode.seats,('mobile_god_lusu','caocao','sunquan','guanyu')))
    setup.stage=SetupStage.COMPLETE
    s=GameSession.new_game(military=True,setup=setup)
    teams=dict(s.state.metadata['teams'])
    from sanguosha.engine.mobile_gods import MobileGodAction
    s.engine.start_action(MobileGodAction('tamo','p1','tamo'))
    request=s.engine.pending_request
    assert request.request_type is RequestType.YES_NO
    s.engine.submit_decision(Decision(request.request_id,'p1',True))
    request=s.engine.pending_request
    assert set(request.allowed_player_ids)==set(mode.seats)
    order=tuple(reversed(mode.seats))
    s.engine.submit_decision(Decision(request.request_id,'p1',order))
    assert s.state.seat_order==order
    assert s.state.metadata['teams']==teams
    assert s.ai.relation(s.state,'p1','p2')=='ENEMY'
    if mode is TEAM_2V2:assert s.ai.relation(s.state,'p1','p3')=='ALLY'


def test_team_counter_and_aoe_score_protect_vulnerable_ally():
    s=GameSession.new_game(military=True,five_generals=True,mode_id=TEAM_2V2.mode_id)
    s.state.players['p3'].hp=1
    assert s.ai._action_priority(s.state,'p1','trick.archery_attack',('p2','p4'))<0
    cid=next(cid for cid,c in s.state.cards.items() if c.definition_id=='trick.nullification')
    request=PendingRequest('counter','p1',RequestType.RESPOND_WITH_CARD,'无懈可击','a','f',
        required_definition_id='trick.nullification',eligible_card_ids=(cid,),allow_pass=True,subject_player_id='p3')
    context=dict(current_target_id='p3',definition_id='trick.archery_attack',cancelled=False)
    assert s.ai.decide(s.state,request,response_context=context).value==cid
    context['cancelled']=True
    assert s.ai.decide(s.state,request,response_context=context).value is PASS_RESPONSE
