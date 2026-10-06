"""Effects and phase transitions not covered by the seven acceptance chains."""
from dataclasses import replace
import pytest
from test_t6_military_basics import game,put
from test_t6_trick_chains import run
from test_t6_equipment_chains import gear,choose
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_tricks import ResolveDelayed
from sanguosha.engine.judgment import JudgmentAction,JudgmentPattern
from sanguosha.engine.turns import TurnAction
from sanguosha.engine.dying import DyingAction
from sanguosha.engine.requests import RequestType,PASS_RESPONSE
from sanguosha.engine.events import PhaseSkippedEvent
from sanguosha.engine.card_moves import CardMove,CardMoveService,CardMoveReason
from sanguosha.model.enums import Phase,Suit,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType

@pytest.mark.parametrize('definition',['trick.dismantlement','trick.snatch'])
def test_remove_real_opponent_card_to_correct_zone(definition):
    s=game(); card=put(s,definition); chosen=put(s,'basic.wine','p2')
    s.engine.start_action(UseCardAction('trick','p1',card,('p2',)))
    run(s,lambda r:chosen if r.request_type is RequestType.CHOOSE_CARD else PASS_RESPONSE)
    dest=ZoneRef(ZoneType.DISCARD_PILE) if definition=='trick.dismantlement' else ZoneRef(ZoneType.HAND,'p1')
    assert chosen in s.state.cards_in(dest)
    assert chosen not in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))

def test_ex_nihilo_draws_two_real_cards():
    s=game(); card=put(s,'trick.ex_nihilo'); n=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(UseCardAction('draw','p1',card)); run(s)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==n+1

def test_god_salvation_heals_each_living_player_once():
    s=game()
    for p in s.state.players.values(): p.hp=2
    card=put(s,'trick.god_salvation'); s.engine.start_action(UseCardAction('heal','p1',card)); run(s)
    assert all(p.hp==3 for p in s.state.players.values())

@pytest.mark.parametrize('supplies,suit,skipped',[
    ('delayed.indulgence',Suit.SPADE,Phase.PLAY),
    ('delayed.supply_shortage',Suit.HEART,Phase.DRAW)])
def test_delayed_judgment_skips_actual_phase(supplies,suit,skipped):
    s=game(); card=put(s,supplies,'p1',ZoneType.JUDGMENT)
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]; s.state.cards[top]=replace(s.state.cards[top],suit=suit)
    s.engine.start_action(TurnAction('turn','p1',phases=(Phase.JUDGMENT,skipped,Phase.FINISH)))
    run(s)
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert any(isinstance(e,PhaseSkippedEvent) and e.phase is skipped for e in s.events.events)
    assert not s.state.players['p1'].marks.get('skip_'+skipped.value)

def test_lightning_hit_deals_three_thunder_and_discards_delayed_card():
    s=game(); card=put(s,'delayed.lightning','p2',ZoneType.JUDGMENT)
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]; s.state.cards[top]=replace(s.state.cards[top],suit=Suit.SPADE,rank=5)
    s.engine.start_action(ResolveDelayed('hit','p2',card)); run(s)
    assert s.state.players['p2'].hp==1
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

@pytest.mark.parametrize('respond',[False,True])
def test_borrowed_sword_second_target_response_or_weapon_transfer(respond):
    s=game(); weapon=gear(s,'weapon.kylin_bow','p2'); slash=put(s,'basic.thunder_slash','p2')
    card=put(s,'trick.borrowed_sword'); s.engine.start_action(UseCardAction('borrow','p1',card,('p2',)))
    def response(r):
        if r.request_type is RequestType.CHOOSE_PLAYER:return 'p3'
        if respond and r.required_definition_id=='basic.slash' and slash in r.eligible_card_ids:return slash
        return PASS_RESPONSE
    run(s,response)
    assert s.state.players['p3'].hp==(3 if respond else 4)
    assert weapon in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.WEAPON) if respond else ZoneRef(ZoneType.HAND,'p1'))

@pytest.mark.parametrize('count',[0,1,2,3])
def test_counter_chain_parity_changes_real_duel_effect(count):
    s=game(); counters=[put(s,'trick.nullification','p'+str(i+1)) for i in range(count)]
    card=put(s,'trick.duel'); s.engine.start_action(UseCardAction('duel','p1',card,('p2',)))
    run(s,lambda r:next((cid for cid in counters if cid in r.eligible_card_ids),PASS_RESPONSE))
    assert s.state.players['p2'].hp==(4 if count%2 else 3)

def test_wine_only_saves_its_dying_owner():
    s=game(); wine=put(s,'basic.wine','p2'); s.state.players['p2'].hp=0
    s.engine.start_action(DyingAction('dying','p2','p1'))
    assert s.engine.pending_request.player_id == 'p1'
    from sanguosha.engine.requests import Decision
    r = s.engine.pending_request
    s.engine.submit_decision(Decision(r.request_id, r.player_id, PASS_RESPONSE))
    assert s.engine.pending_request.player_id == 'p2'
    assert wine in s.engine.pending_request.eligible_card_ids
    run(s,lambda r:wine if wine in r.eligible_card_ids else PASS_RESPONSE)
    assert s.state.players['p2'].hp==1 and s.state.players['p2'].is_alive
    assert 'wine' not in s.state.players['p2'].marks

def test_judgment_recycles_real_discard_pile():
    s=game(); draw=ZoneRef(ZoneType.DRAW_PILE); discard=ZoneRef(ZoneType.DISCARD_PILE)
    CardMoveService(s.events).move(s.state,CardMove('empty-draw',s.state.cards_in(draw),draw,discard,CardMoveReason.SYSTEM))
    s.engine.start_action(JudgmentAction('judgment','p1',JudgmentPattern()))
    assert s.engine.last_result is True
    assert len(s.state.cards)==160 and not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))

def test_wine_expires_even_when_finish_phase_is_skipped():
    s=game();s.state.players['p1'].marks['wine']=1
    s.engine.start_action(TurnAction('turn','p1',phases=(Phase.FINISH,),skipped_phases=frozenset({Phase.FINISH})))
    assert 'wine' not in s.state.players['p1'].marks
