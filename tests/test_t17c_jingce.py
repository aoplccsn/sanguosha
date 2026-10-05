"""Jingce counts use events across the current turn, not responses/materials."""
import pytest
from test_t17c_first_batch import setup, restore
from test_t17b_tier1 import answer
from sanguosha.engine.events import CardUsedEvent, CardRespondedEvent, TurnStartedEvent
from sanguosha.engine.phases import PhaseAction, END_PLAY_PHASE
from sanguosha.engine.yj2013 import cards_used_this_turn
from sanguosha.model.enums import Phase
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.decisions.ai import AIDecisionProvider

@pytest.mark.parametrize('count,hp,wanted', [(0,3,False),(2,3,False),(3,3,True),(4,3,True),(2,2,True)])
def test_jingce_end_play_threshold_and_restore(count,hp,wanted):
    s=setup('cao_zhang'); s.state.players['p1'].character_id='yj2013_guo_huai'
    s.state.players['p1'].hp=hp
    s.events.record(TurnStartedEvent('current','p1',4))
    for i in range(count):
        s.events.record(CardUsedEvent('used:'+str(i),'p1','representative',(), 'basic.slash'))
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(PhaseAction('play','p1',Phase.PLAY))
    answer(s,END_PLAY_PHASE)
    if wanted:
        assert '精策' in s.engine.pending_request.prompt
        s=restore(s)
        d=AIDecisionProvider(human_id=None).decide(s.state,s.engine.pending_request)
        assert d.value is True
        answer(s,True)
    assert s.engine.pending_request is None
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before+(2 if wanted else 0)

def test_count_stops_at_current_turn_and_excludes_other_players():
    events=[CardUsedEvent('old','p1','x',()),TurnStartedEvent('start','p1',4),
            CardUsedEvent('enemy','p2','y',()),CardUsedEvent('virtual','p1','z',(),'trick.duel')]
    assert cards_used_this_turn(events,'p1')==1

def test_decline_and_no_duplicate_after_restore():
    s=setup('cao_zhang'); s.state.players['p1'].character_id='yj2013_guo_huai'
    s.state.players['p1'].hp=1
    s.events.record(TurnStartedEvent('current','p1',4))
    s.events.record(CardUsedEvent('used','p1','x',(),'basic.slash'))
    s.engine.start_action(PhaseAction('play','p1',Phase.PLAY)); answer(s,END_PLAY_PHASE)
    s=restore(s); answer(s,False)
    assert s.engine.pending_request is None
