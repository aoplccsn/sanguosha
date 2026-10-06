from test_t19_lusu import setup
from test_t17b_tier1 import answer
from sanguosha.engine.mobile_gods import MobileGodAction
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.snapshot import snapshot_session, restore_session


def guojia():
    s = setup(); p = s.state.players['p1']; p.character_id = 'mobile_god_guojia'; p.hp = 2; p.max_hp = 3
    return s


def test_huishi_retains_judgment_then_gives_penalty():
    s = guojia(); before = len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(MobileGodAction('huishi','p1','huishi'))
    assert '慧识' in s.engine.pending_request.prompt
    assert s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    s = restore_session(snapshot_session(s)); answer(s,False); answer(s,True); answer(s,'p1')
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))) == before + 1
    assert s.state.players['p1'].max_hp == 2
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_tianyi_permanent_zuoxing_then_virtual_trick():
    s = guojia(); p = s.state.players['p1']
    for player in s.state.players.values(): player.marks['ever_damaged'] = 1
    s.engine.start_action(MobileGodAction('awaken','p1','tianyi_guojia')); answer(s,'p1')
    assert p.max_hp == 5 and p.hp == 3
    assert s.skills.has(s.state,'p1','zuoxing')
    before = len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(MobileGodAction('zuoxing','p1','zuoxing')); answer(s,'trick.ex_nihilo')
    # Existing ordinary trick counter windows remain authoritative.
    from sanguosha.engine.requests import PASS_RESPONSE
    for _ in range(20):
        if s.engine.pending_request is None: break
        answer(s,PASS_RESPONSE)
    assert p.max_hp == 4
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))) == before + 2


def test_huishi_guojia_awakening_override_and_cost():
    s = guojia(); p = s.state.players['p1']; p.max_hp = 6
    s.state.players['p2'].character_id = 'mountain_god_simayi'
    s.engine.start_action(MobileGodAction('limited','p1','huishi_guojia')); answer(s,'p2')
    assert s.engine.pending_request.choices == ('baoyin',)
    answer(s,'baoyin')
    assert s.state.players['p2'].marks['ignore_awakening:baoyin'] == 1
    assert p.max_hp == 4 and p.marks['huishi_guojia_used'] == 1
