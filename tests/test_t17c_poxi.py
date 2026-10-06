from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.remaining_gods import RemainingGodAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.errors import InvalidDecision
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.enums import Suit,Phase
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.projection import project_for_human
from sanguosha.multiplayer.room import MultiplayerRoom


def ganning(n):
    s=setup('cao_zhang');s.state.players['p1'].character_id='thunder_god_ganning'
    s.state.players['p1'].hp=3;s.state.players['p1'].max_hp=6
    for q in s.state.seat_order:empty(s,q)
    cards=[]
    for i,suit in enumerate((Suit.SPADE,Suit.HEART,Suit.CLUB,Suit.DIAMOND)):
        cid=put(s,'basic.slash','p1' if i<n else 'p2')
        s.state.cards[cid]=replace(s.state.cards[cid],suit=suit);cards.append(cid)
    if n==4:put(s,'basic.dodge','p2')
    return s,tuple(cards)


@pytest.mark.parametrize('n',[0,1,2,3,4])
def test_poxi_four_suits_each_own_card_count_result_restore(n):
    s,cards=ganning(n);s.engine.start_action(RemainingGodAction('poxi','p1','poxi'));s=restore(s)
    answer(s,'p2');s=restore(s);answer(s,cards)
    assert s.engine.pending_request is None
    assert set(cards)<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert not s.state.metadata.get('poxi_reveal')
    assert s.state.play_usage.count('skill.poxi')==1
    assert s.state.players['p1'].max_hp==(5 if n==0 else 6)
    assert s.state.players['p1'].hp==(4 if n==3 else 3)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==(4 if n==4 else 0)
    assert bool(s.state.players['p1'].marks.get('poxi_end_play'))==(n==1)


def test_poxi_authorized_viewer_only_and_wire_uses_visible_faces():
    s,cards=ganning(2);s.engine.start_action(RemainingGodAction('poxi','p1','poxi'));answer(s,'p2');s=restore(s)
    owner=project_for_human(s.state,s.definitions,'p1',s.character_names);observer=project_for_human(s.state,s.definitions,'p3',s.character_names)
    assert {c.card_id for c in next(p for p in owner.players if p.player_id=='p2').revealed_hand}==set(cards[2:])
    assert all(not p.revealed_hand for p in observer.players)
    room=MultiplayerRoom();room.session=s;payload=room._request_payload(s.engine.pending_request)
    assert set(payload['eligible_card_ids'])==set(cards)
    assert all('背面' not in label for label in payload['choice_labels'].values())
    answer(s,());assert not s.state.metadata.get('poxi_reveal')
    assert all(not p.revealed_hand for p in project_for_human(s.state,s.definitions,'p1',s.character_names).players)
    assert all(c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1' if i<2 else 'p2')) for i,c in enumerate(cards))


def test_poxi_rejects_partial_and_duplicate_suit_selection():
    s,cards=ganning(2);extra=put(s,'basic.slash','p2');s.state.cards[extra]=replace(s.state.cards[extra],suit=Suit.SPADE)
    s.engine.start_action(RemainingGodAction('poxi','p1','poxi'));answer(s,'p2');r=s.engine.pending_request
    with pytest.raises(InvalidDecision):r.validate(cards[:3])
    with pytest.raises(InvalidDecision):r.validate((cards[0],extra,cards[1],cards[2]))
    assert r.timeout_value()==()


def test_poxi_one_own_card_ends_real_play_and_reduces_hand_limit():
    from sanguosha.engine.fire import FireHandLimit
    from sanguosha.engine.wind import WindHandLimit
    s,cards=ganning(1);s.engine.start_action(PhaseAction('play','p1',Phase.PLAY))
    answer(s,'skill:poxi');answer(s,'p2');answer(s,cards)
    assert s.engine.pending_request is None and s.state.current_phase is None
    assert not s.state.players['p1'].marks.get('poxi_end_play')
    assert FireHandLimit(WindHandLimit(),s.skills)(s.state,'p1')==2


def test_poxi_reveal_does_not_survive_skill_suppression_or_actor_death():
    from sanguosha.model.enums import PlayerStatus
    s,cards=ganning(2);s.engine.start_action(RemainingGodAction('poxi','p1','poxi'));answer(s,'p2')
    s.state.players['p1'].disabled_skills.add('poxi')
    assert all(not p.revealed_hand for p in project_for_human(s.state,s.definitions,'p1',s.character_names).players)
    s.state.players['p1'].disabled_skills.clear();s.state.players['p1'].status=PlayerStatus.DEAD
    assert all(not p.revealed_hand for p in project_for_human(s.state,s.definitions,'p1',s.character_names).players)
