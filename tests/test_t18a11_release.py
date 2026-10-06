"""Rule regressions found by the T18A.11 audit, independent of prior assertions."""
import pytest
from test_t6_military_basics import game, put, resolve
from sanguosha.engine.death import DeathAction
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.model.enums import EquipmentSlot, Identity
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.snapshot import snapshot_session, restore_session

@pytest.mark.parametrize("reconnect", [False, True])
def test_lord_loyalist_penalty_preserves_judgment_and_special_piles(reconnect):
    s = game()
    s.state.players['p1'].identity = Identity.LORD
    s.state.players['p2'].identity = Identity.LOYALIST
    weapon = put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    delayed = put(s, 'trick.indulgence', 'p1', ZoneType.JUDGMENT)
    special = put(s, 'basic.slash')
    pile = ZoneRef(ZoneType.SPECIAL, 'p1', special_key='audit-private')
    CardMoveService(s.events).move(s.state, CardMove('pile', (special,), ZoneRef(ZoneType.HAND, 'p1'), pile, CardMoveReason.SYSTEM))
    if reconnect:
        s = restore_session(snapshot_session(s))
    s.engine.start_action(DeathAction('penalty', 'p2', 'p1'))
    resolve(s)
    assert not s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert weapon in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert delayed in s.state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p1'))
    assert special in s.state.cards_in(pile)
    s.state.__post_init__()

@pytest.mark.parametrize("reconnect", [False, True])
def test_cuike_killing_lord_does_not_offer_burst_after_victory(reconnect):
    from test_t17c_god_luxun import luxun
    from sanguosha.engine.remaining_gods import RemainingGodAction
    from sanguosha.engine.requests import Decision, PASS_RESPONSE
    from sanguosha.model.state import GameStatus
    s=luxun()
    s.state.players['p1'].identity=Identity.REBEL
    s.state.players['p2'].identity=Identity.LORD
    s.state.players['p2'].hp=1
    s.state.players['p1'].marks['junlve']=7
    s.engine.start_action(RemainingGodAction('kill-lord','p1','cuike'))
    for value in (True,'p2'):
        r=s.engine.pending_request
        s.engine.submit_decision(Decision(r.request_id,r.player_id,value))
    if reconnect:s=restore_session(snapshot_session(s))
    while s.engine.pending_request and s.state.status is not GameStatus.FINISHED:
        r=s.engine.pending_request
        s.engine.submit_decision(Decision(r.request_id,r.player_id,PASS_RESPONSE))
    assert s.state.status is GameStatus.FINISHED
    assert s.engine.pending_request is None
    assert s.engine.stack.is_empty()

def test_jingce_never_starts_a_new_phase_end_request_after_lord_death():
    from test_t17c_god_luxun import luxun
    from sanguosha.engine.events import TurnStartedEvent
    from sanguosha.engine.phases import PhaseAction
    from sanguosha.engine.requests import Decision, PASS_RESPONSE
    from sanguosha.model.enums import Phase
    from sanguosha.model.state import GameStatus
    s=luxun();s.state.players['p1'].character_id='yj2013_guo_huai'
    s.state.players['p1'].hp=1;s.state.players['p1'].identity=Identity.REBEL
    s.state.players['p2'].identity=Identity.LORD;s.state.players['p2'].hp=1
    slash=put(s,'basic.slash')
    s.events.record(TurnStartedEvent('current-audit-turn','p1',4))
    s.engine.start_action(PhaseAction('terminal-play','p1',Phase.PLAY))
    r=s.engine.pending_request
    s.engine.submit_decision(Decision(r.request_id,r.player_id,{'option':'use:'+slash,'targets':('p2',)}))
    for _ in range(30):
        if s.state.status is GameStatus.FINISHED:break
        r=s.engine.pending_request
        assert r is not None
        s.engine.submit_decision(Decision(r.request_id,r.player_id,PASS_RESPONSE))
    assert s.state.status is GameStatus.FINISHED
    assert s.engine.pending_request is None and s.engine.stack.is_empty()
