"""Tricks retain target/card/counter cursors across nested decisions."""
from dataclasses import replace
from test_t6_military_basics import game, put
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_tricks import NullificationWindow, ResolveDelayed
from sanguosha.engine.requests import Decision, RequestType, PASS_RESPONSE
from sanguosha.engine.card_moves import CardMoveService, CardMove, CardMoveReason
from sanguosha.model.enums import Suit
from sanguosha.model.zones import ZoneRef, ZoneType

def run(s, chooser=None):
    count=0
    while s.engine.pending_request:
        r=s.engine.pending_request
        if chooser:
            v=chooser(r)
        elif r.request_type is RequestType.RESPOND_WITH_CARD:
            v=PASS_RESPONSE
        elif r.request_type is RequestType.CHOOSE_CARD:
            v=r.eligible_card_ids[0]
        elif r.request_type is RequestType.CHOOSE_PLAYER:
            v=r.allowed_player_ids[0]
        else:
            v=False
        s.engine.submit_decision(Decision(r.request_id,r.player_id,v))
        s.state.__post_init__()
        count+=1
        assert count<300
    assert s.engine.stack.is_empty()
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))

def test_three_nullifications_leave_original_effect_cancelled():
    s=game()
    ids=[put(s,'trick.nullification',pid) for pid in ('p1','p2','p3')]
    s.engine.start_action(NullificationWindow('counter','p4'))
    def choose(r):
        return next((cid for cid in ids if cid in r.eligible_card_ids),PASS_RESPONSE)
    run(s,choose)
    assert s.engine.last_result is True
    assert all(cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for cid in ids)

def test_duel_alternates_multiple_slash_responses_then_damage():
    s=game()
    card=put(s,'trick.duel')
    slash1=put(s,'basic.fire_slash','p2')
    slash2=put(s,'basic.thunder_slash','p1')
    s.engine.start_action(UseCardAction('duel','p1',card,('p2',)))
    selected=[]
    def choose(r):
        if r.required_definition_id=='basic.slash':
            selected.append(r.player_id)
            return next((cid for cid in (slash1,slash2) if cid in r.eligible_card_ids),PASS_RESPONSE)
        return PASS_RESPONSE
    run(s,choose)
    assert selected==['p2','p1','p2']
    assert s.state.players['p2'].hp==3

def test_savage_assault_resumes_after_dying_to_later_targets():
    s=game()
    s.state.players['p2'].hp=1
    peach=put(s,'basic.peach')
    card=put(s,'trick.savage_assault')
    s.engine.start_action(UseCardAction('aoe','p1',card))
    def choose(r):
        return peach if r.required_definition_id=='basic.peach' and peach in r.eligible_card_ids else PASS_RESPONSE
    run(s,choose)
    assert s.state.players['p2'].is_alive and s.state.players['p2'].hp>0
    assert all(s.state.players[pid].hp==3 for pid in ('p3','p4','p5'))

def test_amazing_grace_five_real_cards_selected_from_shared_pool():
    s=game()
    card=put(s,'trick.amazing_grace')
    before={pid:len(s.state.cards_in(ZoneRef(ZoneType.HAND,pid))) for pid in s.state.seat_order}
    s.engine.start_action(UseCardAction('grace','p1',card))
    chosen=[]
    def choose(r):
        if r.request_type is RequestType.CHOOSE_CARD:
            chosen.append((r.player_id,r.eligible_card_ids[0]))
            return r.eligible_card_ids[0]
        return PASS_RESPONSE
    run(s,choose)
    assert len(chosen)==len(set(cid for _,cid in chosen))==5
    for pid,cid in chosen:
        assert cid in s.state.cards_in(ZoneRef(ZoneType.HAND,pid))
    assert not any(zone.card_ids for ref,zone in s.state.zones.items() if ref.zone_type is ZoneType.SPECIAL)

def test_lightning_miss_moves_same_physical_instance_to_next_player():
    s=game()
    card=put(s,'delayed.lightning','p1',ZoneType.JUDGMENT)
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top]=replace(s.state.cards[top],suit=Suit.HEART)
    s.engine.start_action(ResolveDelayed('lightning','p1',card))
    run(s)
    assert card in s.state.cards_in(ZoneRef(ZoneType.JUDGMENT,'p2'))
    assert card not in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

def test_fire_attack_reveal_then_matching_suit_discard():
    s=game()
    card=put(s,'trick.fire_attack')
    cost=put(s,'basic.dodge')
    shown=put(s,'basic.dodge','p2')
    s.state.cards[cost]=replace(s.state.cards[cost],suit=Suit.HEART)
    s.state.cards[shown]=replace(s.state.cards[shown],suit=Suit.HEART)
    s.engine.start_action(UseCardAction('fire','p1',card,('p2',)))
    def choose(r):
        if r.request_type is RequestType.CHOOSE_CARD:
            return shown
        if r.required_definition_id is None:
            return cost
        return PASS_RESPONSE
    run(s,choose)
    assert s.state.players['p2'].hp==3
    assert cost in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

def test_iron_chain_recast_draws_one_without_counter_window():
    s=game()
    card=put(s,'trick.iron_chain')
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(UseCardAction('chain','p1',card))
    r=s.engine.pending_request
    assert r.request_type is RequestType.CHOOSE_PLAYERS and r.min_count==0
    s.engine.submit_decision(Decision(r.request_id,r.player_id,()))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
