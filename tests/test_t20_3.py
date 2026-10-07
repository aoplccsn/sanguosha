"""T20.3 real three-survivor chain projection, combined payload and equipment cost."""
import pytest
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import Decision
from sanguosha.engine.events import CardMovedEvent
from sanguosha.model.enums import Identity, Phase, EquipmentSlot, PlayerStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from test_t6_military_basics import put
from sanguosha.multiplayer.protocol import serialize_request
from sanguosha.session import GameSession


def scene():
    s=GameSession.new_game(military=True,five_generals=True)
    s.state.current_player_id='p1'
    s.state.revealed_identities={'p2','p4','p5'}
    for pid,identity in zip(('p1','p2','p3'),(Identity.LOYALIST,Identity.LORD,Identity.REBEL)):
        s.state.players[pid].identity=identity
        s.state.players[pid].character_id='sunquan' if pid=='p1' else 'caocao'
    for pid in ('p4','p5'):
        s.state.players[pid].status=PlayerStatus.DEAD
    cid=put(s,'trick.iron_chain')
    s.engine.start_action(PhaseAction('t203-play','p1',Phase.PLAY))
    return s,cid


@pytest.mark.parametrize('targets',[('p2',),('p1','p3'),()])
def test_three_survivors_loyalist_chain_targets_and_recast(targets):
    s,cid=scene();req=s.engine.pending_request
    option='use:'+cid
    spec=serialize_request(req,60000)['play_card_targets'][option]
    assert set(spec['targets'])=={'p1','p2','p3'}
    assert (spec['min'],spec['max'])==(0,2)
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.submit_decision(Decision(req.request_id,'p1',{'option':option,'targets':targets}))
    while s.engine.pending_request and s.engine.pending_request.request_type.value!='choose_option':
        req=s.engine.pending_request
        s.engine.submit_decision(Decision(req.request_id,req.player_id,req.timeout_value()))
    assert {pid for pid,p in s.state.players.items() if p.chained}==set(targets)
    assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before-(1 if targets else 0)
    if not targets:
        assert any(isinstance(e,CardMovedEvent) and cid in e.card_ids and e.reason=='recast' for e in s.events.events)


def test_zhiheng_hand_and_equipment_payload():
    s,cid=scene()
    # End this play request and start a clean phase with equipment present.
    s.engine.submit_decision(Decision(s.engine.pending_request.request_id,'p1','end_play_phase'))
    eq=put(s,'equipment.weapon.crossbow',zone=ZoneType.EQUIPMENT,slot=EquipmentSlot.WEAPON)
    s.engine.start_action(PhaseAction('t203-cost','p1',Phase.PLAY))
    req=s.engine.pending_request
    option=next(o for o in req.choices if o=='skill:zhiheng')
    s.engine.submit_decision(Decision(req.request_id,'p1',option))
    req=s.engine.pending_request
    assert eq in req.eligible_card_ids and cid in req.eligible_card_ids
    s.engine.submit_decision(Decision(req.request_id,'p1',(eq,cid)))
    assert eq in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
