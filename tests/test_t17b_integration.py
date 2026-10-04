"""Partial T17B acceptance: Tier 1/2 only; the production gate stays closed."""
from dataclasses import replace
import pytest
from sanguosha.session import GameSession
from sanguosha.model.state import GameStatus
from sanguosha.model.enums import EquipmentSlot, Identity, Phase
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.events import PhaseEndedEvent
from sanguosha.engine.requests import Decision
from sanguosha.engine.turnover import TurnoverAction
from sanguosha.engine.yj2011 import XuanfengAction, event_reactions
from sanguosha.snapshot import snapshot_session,restore_session
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.room_snapshot import snapshot_room,restore_room
from test_t17b_tier1 import game,answer
from test_t6_military_basics import put

IMPLEMENTED_DEV=('yj2011_yu_jin','yj2011_xu_sheng','yj2011_zhang_chunhua','yj2011_xu_shu','yj2011_ling_tong')


@pytest.mark.parametrize('mode',['military-five','military-eight'])
@pytest.mark.parametrize('seed',range(5))
def test_current_five_development_generals_full_game_with_mid_skill_restore(mode,seed):
    s=GameSession.new_game(seed=100+seed,military=True,five_generals=True,mode_id=mode)
    order=IMPLEMENTED_DEV[seed:]+IMPLEMENTED_DEV[:seed]
    for pid,gid in zip(s.state.seat_order,order):
        c=s.skills.characters[gid]; p=s.state.players[pid]; p.character_id=gid
        p.max_hp=c.max_hp+int(p.identity is Identity.LORD); p.hp=p.max_hp; s.character_names[pid]=c.name
    s.human_id='ai-only'; restored=False
    for _ in range(30000):
        if s.state.status is GameStatus.FINISHED: break
        if s.engine.pending_request and not restored and any(x in s.engine.pending_request.prompt
                                                            for x in ('伤逝','破军','旋风','举荐')):
            s=restore_session(snapshot_session(s)); restored=True
        assert s.step_auto()
    else: pytest.fail('AI match exceeded limit')
    assert restored and s.state.victory is not None and s.engine.pending_request is None


@pytest.mark.parametrize('mode',['military-five','military-eight'])
def test_xuanfeng_multiplayer_opaque_choice_mid_request_restore_and_timeout(mode):
    room=MultiplayerRoom(mode_id=mode)
    room.session=GameSession.new_game(military=True,five_generals=True,mode_id=mode)
    s=room.session; s.state.players['p1'].character_id='yj2011_ling_tong'
    for pid,p in s.state.players.items():
        if pid!='p1': p.character_id='sunquan'
    card=put(s,'basic.peach','p2')
    s.engine.start_action(XuanfengAction('xuanfeng','p1'))
    answer(s,True); answer(s,'p2')
    request=s.engine.pending_request; payload=room._request_payload(request)
    assert card not in str(payload)
    assert all(cid.startswith('hidden-hand:') for cid in payload['eligible_card_ids'])
    room=restore_room(snapshot_room(room)); s=room.session
    assert s.engine.pending_request==request
    assert room._request_payload(request)==payload
    decision=room._resolve_hidden_choice(request,Decision(request.request_id,'p1','hidden-hand:1'))
    s.engine.submit_decision(decision)
    r=s.engine.pending_request; assert r.timeout_value() is False
    s.engine.submit_decision(Decision(r.request_id,'p1',r.timeout_value()))
    assert s.engine.stack.is_empty()


@pytest.mark.parametrize('count',[0,1,2,3])
def test_xuanfeng_discard_phase_exact_batch_threshold(count):
    s=game(); s.state.players['p1'].character_id='yj2011_ling_tong'
    hand=s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    moves=s.engine.reaction_provider.__self__
    if count:
        moves.move(s.state,CardMove('discard',hand[:count],ZoneRef(ZoneType.HAND,'p1'),
            ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,'p1','phase'))
    reactions=event_reactions(s.state,PhaseEndedEvent('phase:end','p1',Phase.DISCARD),s.skills,s.events)
    assert bool(reactions)==(count>=2)
    if reactions: assert isinstance(reactions[0],XuanfengAction)


def test_xuanfeng_ai_choice_invariant_under_hidden_card_changes():
    s=game(); s.state.players['p1'].character_id='yj2011_ling_tong'
    s.engine.start_action(XuanfengAction('xuanfeng','p1')); answer(s,True); answer(s,'p2')
    request=s.engine.pending_request
    first=s.ai.decide(s.state,request)
    for cid in request.eligible_card_ids:
        s.state.cards[cid]=replace(s.state.cards[cid],definition_id='basic.peach',rank=13)
    assert s.ai.decide(s.state,request)==first


def test_development_general_pool_never_enters_old_huashen():
    from sanguosha.engine.mountain import draw_transformations
    s=game(); draw_transformations(s.state,'p1',200,s.skills,s.rng)
    assert not any(g.startswith('yj2011') for g in s.state.players['p1'].transformation_pool)


def test_pyside_all_development_generals_have_readable_fallback_portraits():
    from sanguosha.content.characters.yj2011 import YJ2011_DEV_GENERALS
    from sanguosha.ui.resources import RESOURCES
    s=game()
    for general in YJ2011_DEV_GENERALS:
        portrait=RESOURCES.general_portrait(str(general.id),general.name)
        assert not portrait.isNull() and portrait.width()>0 and portrait.height()>0
        for sid in general.skill_ids:
            skill=s.skills.skills[sid]
            assert skill.name and len(skill.description)>12
