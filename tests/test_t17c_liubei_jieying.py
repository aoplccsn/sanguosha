import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put,resolve
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.fire import FireHandLimit
from sanguosha.engine.wind import WindHandLimit
from sanguosha.engine.chaining import set_chained
from sanguosha.model.enums import Phase,DamageNature,PlayerStatus


def game():
    s=setup('cao_zhang');s.state.players['p1'].character_id='shadow_god_liubei'
    for q in s.state.seat_order:empty(s,q)
    s.state.players['p1'].chained=True
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return s


def test_jieying_finish_mandatory_other_unchained_target_restore():
    s=game();s.state.players['p3'].chained=True
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH));s=restore(s)
    r=s.engine.pending_request
    assert '结营' in r.prompt and 'p1' not in r.allowed_player_ids and 'p3' not in r.allowed_player_ids
    answer(s,'p2');assert s.state.players['p2'].chained and s.engine.pending_request is None


def test_jieying_chain_hand_bonus_global_and_source_suppression_or_death():
    s=game();s.state.players['p2'].chained=True
    limit=FireHandLimit(WindHandLimit(),s.skills)
    assert limit(s.state,'p1')==s.state.players['p1'].hp+2
    assert limit(s.state,'p2')==s.state.players['p2'].hp+2
    assert limit(s.state,'p3')==s.state.players['p3'].hp
    s.state.players['p1'].disabled_skills.add('jieying_liubei')
    assert limit(s.state,'p2')==s.state.players['p2'].hp
    assert set_chained(s.state,'p1',False,s.skills)
    s.state.players['p1'].disabled_skills.clear();s.state.players['p1'].status=PlayerStatus.DEAD
    assert limit(s.state,'p2')==s.state.players['p2'].hp


def test_jieying_blocks_iron_chain_unlink():
    s=game();c=put(s,'trick.iron_chain','p2');s.state.current_player_id='p2'
    from sanguosha.model.usage import PlayUsageState
    s.state.play_usage=PlayUsageState('p2',4)
    s.engine.start_action(UseCardAction('iron','p2',c,('p1',)))
    resolve(s)
    assert s.state.players['p1'].chained


@pytest.mark.parametrize('god_first',[True,False])
def test_jieying_elemental_damage_keeps_god_linked_and_propagates_once(god_first):
    s=game();s.state.players['p2'].chained=True
    first='p1' if god_first else 'p2'
    initial={q:s.state.players[q].hp for q in ('p1','p2')}
    s.engine.start_action(MilitaryDamageAction('fire','p3',first,1,DamageNature.FIRE))
    resolve(s)
    assert all(s.state.players[q].hp==initial[q]-1 for q in initial)
    assert s.state.players['p1'].chained and not s.state.players['p2'].chained


def test_jieying_finish_no_unchained_targets_has_no_prompt():
    s=game()
    for p in s.state.players.values():p.chained=True
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH))
    assert s.engine.pending_request is None
