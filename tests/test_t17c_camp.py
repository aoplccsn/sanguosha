from test_t17c_poxi import ganning
from test_t17c_first_batch import restore
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.remaining_gods import RemainingGodAction,camp_bonus,camp_start
from sanguosha.engine.turns import TurnAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.military_basics import MilitarySlashRule
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.fire import FireHandLimit
from sanguosha.engine.wind import WindHandLimit
from sanguosha.engine.yj2012 import YJ2012Action
from sanguosha.model.enums import Phase
from sanguosha.model.zones import ZoneRef,ZoneType


def camp(s,holder='p1'):
    s.state.players[holder].marks['camp']=1
    s.state.metadata['camp_sources']={holder:'p1'}


def test_camp_turn_start_only_if_no_living_holder_and_own_mark_stays():
    s,_=ganning(0);s.engine.start_action(TurnAction('turn','p1',(Phase.DRAW,)))
    assert s.state.players['p1'].marks['camp']==1
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==3
    assert s.engine.pending_request is None
    s.state.players['p1'].marks.pop('camp');camp(s,'p2');camp_start(s.state,'p1',s.skills)
    assert not s.state.players['p1'].marks.get('camp')


def test_camp_finish_transfer_restore_and_all_three_shared_bonuses():
    s,_=ganning(0);camp(s)
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH));s=restore(s);answer(s,True)
    s=restore(s);answer(s,'p2')
    assert not s.state.players['p1'].marks.get('camp') and s.state.players['p2'].marks['camp']==1
    assert camp_bonus(s.state,'p2',s.skills)==1
    rule=MilitarySlashRule(DistanceSystem(s.definitions),s.skills)
    assert rule.usage_limit(s.state,'p2')==2
    assert FireHandLimit(WindHandLimit(),s.skills)(s.state,'p2')==s.state.players['p2'].hp+1


def test_camp_other_turn_end_obtains_entire_current_hand_and_removes_mark():
    s,_=ganning(0);camp(s,'p2');s.state.players['p2'].character_id='sunquan'
    before=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    s.engine.start_action(TurnAction('other','p2',(Phase.DRAW,Phase.PLAY)))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==len(before)+3
    current=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')));s=restore(s);answer(s,'end_play_phase')
    assert not s.state.players['p2'].marks.get('camp')
    assert not s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
    assert current<=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))


def test_camp_does_not_modify_arbitrary_skill_draws():
    from sanguosha.engine.deck import DrawCardsAction
    s,_=ganning(0);camp(s)
    s.engine.start_action(DrawCardsAction('skill-draw','p1',2))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==2


def test_camp_bonus_combines_with_jiangchi_draw_count():
    s,_=ganning(0);camp(s,'p2');s.state.players['p2'].granted_skills['jiangchi']='test'
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    s.engine.start_action(YJ2012Action('jiangchi','p2','jiangchi'));answer(s,'chi')
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==before+2


def test_camp_source_skill_disabled_no_bonuses_and_no_hand_acquisition():
    s,_=ganning(0);camp(s,'p2');s.state.players['p1'].disabled_skills.add('jieying_ganning')
    assert camp_bonus(s.state,'p2',s.skills)==0
    before=s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
    s.engine.start_action(TurnAction('other','p2',(Phase.PREPARATION,)))
    assert s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))==before
    assert s.state.players['p2'].marks.get('camp')==1


def test_camp_source_death_leaves_mark_but_no_bonus():
    from sanguosha.engine.death import DeathAction
    s,_=ganning(0);camp(s,'p2')
    s.engine.start_action(DeathAction('death','p1',None))
    assert s.state.players['p2'].marks.get('camp')==1
    assert camp_bonus(s.state,'p2',s.skills)==0


def test_camp_optional_finish_decline_keeps_self_mark():
    s,_=ganning(0);camp(s)
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH));answer(s,False)
    assert s.state.players['p1'].marks['camp']==1
