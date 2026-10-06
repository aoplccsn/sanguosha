from test_t19_lusu import setup
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.mobile_gods import MobileGodAction, inject_qizheng, cancel_dinghan_target
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.projection import project_for_human


def test_tianzuo_eight_exact_prints_and_dinghan():
    s = setup(); s.state.players['p2'].character_id = 'mobile_god_xunyu'
    inject_qizheng(s.state, 'p2', s.rng)
    cards = [c for c in s.state.cards.values() if c.instance_id.startswith('tianzuo-p2-')]
    assert len(cards) == 8
    assert sorted(c.rank for c in cards) == list(range(2,10))
    assert cancel_dinghan_target(s.state,'p2','trick.qizhengxiangsheng',s.skills)
    assert cancel_dinghan_target(s.state,'p2','trick.duel',s.skills)
    assert not cancel_dinghan_target(s.state,'p2','trick.duel',s.skills)


def test_qizheng_secret_reconnect_wrong_response_damage():
    s = setup(); put(s,'basic.dodge','p2'); hp = s.state.players['p2'].hp
    s.engine.start_action(MobileGodAction('qizheng','p1','qizheng','p2')); answer(s,'qi')
    request = s.engine.pending_request
    s = restore_session(snapshot_session(s)); assert s.engine.pending_request == request
    projection = project_for_human(s.state,s.definitions,'p2',s.character_names)
    assert 'secret' not in str(projection)
    answer(s,'dodge'); answer(s,s.engine.pending_request.eligible_card_ids[0])
    assert s.state.players['p2'].hp == hp - 1


def test_qizheng_correct_slash_and_zheng_take():
    s = setup(); put(s,'basic.slash','p2'); hp = s.state.players['p2'].hp
    s.engine.start_action(MobileGodAction('qi','p1','qizheng','p2')); answer(s,'qi'); answer(s,'slash')
    answer(s,s.engine.pending_request.eligible_card_ids[0]); assert s.state.players['p2'].hp == hp
    s.engine.start_action(MobileGodAction('zheng','p1','qizheng','p2')); answer(s,'zheng'); answer(s,'pass')
    card = s.engine.pending_request.eligible_card_ids[0]; answer(s,card)
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
