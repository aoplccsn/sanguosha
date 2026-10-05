import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_qice import clear_hand
from test_t17b_tier1 import answer,finish
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.model.enums import Phase
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.engine.card_moves import CardMove,CardMoveReason

def empty(s,pid):
    cards=s.state.cards_in(ZoneRef(ZoneType.HAND,pid))
    if cards:s.engine.reaction_provider.__self__.move(s.state,CardMove('empty:'+pid,cards,ZoneRef(ZoneType.HAND,pid),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM,pid))

@pytest.mark.parametrize('wanted',[True,False])
def test_juece_finish_only_empty_other_targets_and_restore(wanted):
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_li_ru'
    empty(s,'p1');empty(s,'p2');hp=s.state.players['p2'].hp
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH));s=restore(s);answer(s,wanted)
    if wanted:
        assert s.engine.pending_request.allowed_player_ids==('p2',)
        s=restore(s);answer(s,'p2');finish(s)
    assert s.engine.pending_request is None
    assert s.state.players['p2'].hp==hp-int(wanted)

def test_juece_no_empty_target_no_request():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_li_ru'
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH))
    assert s.engine.pending_request is None
