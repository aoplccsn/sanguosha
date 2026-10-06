"""Shared final-judgment disposition and public semantic evidence."""
from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.judgment import JudgmentAction,JudgmentPattern
from sanguosha.engine.events import CardMovedEvent
from sanguosha.model.enums import Suit,Color,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType


def game():
 s=setup('xun_you')
 for p in s.state.players.values():p.character_id='caocao'
 return s


def test_successful_field_judgment_never_enters_discard_or_luoying_window():
 from sanguosha.engine.mountain import TuntianAction,field_zone
 s=game();s.state.players['p2'].granted_skills['tuntian']='audit';s.state.players['p3'].granted_skills['luoying']='audit'
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=Suit.CLUB)
 s.engine.start_action(TuntianAction('audit-field-final','p2'));answer(s,True)
 assert s.engine.pending_request is None
 assert top in s.state.cards_in(field_zone('p2'))
 assert not any(isinstance(e,CardMovedEvent) and top in e.card_ids and e.to_zone.zone_type is ZoneType.DISCARD_PILE for e in s.events.events)
 s.state.__post_init__()


def test_public_final_judgment_uses_judged_players_effective_suit_color():
 from sanguosha.multiplayer.room import MultiplayerRoom
 s=game();s.state.players['p2'].granted_skills.update(hongyan='audit',tiandu='audit')
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=Suit.SPADE,rank=7)
 s.engine.start_action(JudgmentAction('audit-public-suit','p2',JudgmentPattern(suit=Suit.HEART)))
 room=MultiplayerRoom();room.session=s
 reveal=next(e for e in s.events.events if getattr(e,'event_type','')=='judgment_card_revealed')
 public=room._public_event(reveal)
 assert public['cards'][0]['suit']=='\u2665' and public['effective_color']=='red'
 s=restore(s);answer(s,True);room.session=s
 final=next(e for e in s.events.events if getattr(e,'event_type','')=='after_judgment')
 assert room._public_event(final)['matched'] is True
 assert room._public_event(final)['effective_suit']=='heart'
 assert s.state.cards[top].suit is Suit.SPADE

@pytest.mark.parametrize('definition,suit,outcome',[('delayed.indulgence',Suit.SPADE,'skip_play'),('delayed.supply_shortage',Suit.HEART,'skip_draw'),('delayed.lightning',Suit.HEART,'transfer')])
def test_delayed_public_result_names_specific_rule_consequence(definition,suit,outcome):
 from sanguosha.engine.military_tricks import ResolveDelayed
 from sanguosha.multiplayer.room import MultiplayerRoom
 s=game();cid=put(s,definition,'p1',ZoneType.JUDGMENT)
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=suit)
 s.engine.start_action(ResolveDelayed('audit-delayed-result','p1',cid));finish(s)
 result=next(e for e in s.events.events if getattr(e,'event_type','')=='delayed_result')
 assert result.metadata['outcome']==outcome and result.metadata['definition_id']==definition
 room=MultiplayerRoom();room.session=s;public=room._public_event(result)
 assert public['kind']=='DelayedResultEvent' and public['message']


@pytest.mark.parametrize('condition',['dead','moved'])
def test_delayed_removed_or_dead_target_cannot_start_counter_or_judgment(condition):
 from sanguosha.engine.military_tricks import ResolveDelayed
 from sanguosha.engine.card_moves import CardMove,CardMoveReason
 from sanguosha.model.enums import PlayerStatus
 s=game();cid=put(s,'delayed.indulgence','p1',ZoneType.JUDGMENT)
 if condition=='dead':s.state.players['p1'].status=PlayerStatus.DEAD
 else:s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-away',(cid,),ZoneRef(ZoneType.JUDGMENT,'p1'),ZoneRef(ZoneType.HAND,'p2'),CardMoveReason.SYSTEM))
 before=len(s.events.events)
 s.engine.start_action(ResolveDelayed('audit-stale-delayed','p1',cid))
 assert s.engine.pending_request is None
 assert not any(getattr(e,'event_type','')=='before_judgment' for e in s.events.events[before:])


def test_reconnect_retains_revealed_judgment_before_first_retrial():
 from sanguosha.multiplayer.room import MultiplayerRoom
 from sanguosha.projection import project_for_human
 s=game();s.state.players['p2'].granted_skills['guicai']='audit'
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
 s.engine.start_action(JudgmentAction('audit-reveal-restore','p1',JudgmentPattern()))
 s=restore(s);room=MultiplayerRoom();room.session=s
 wire=room._named_projection(project_for_human(s.state,s.definitions,'p3',{}),'p3')
 assert any(e['kind']=='JudgmentRevealedEvent' for e in wire['public_card_history'])
 assert top in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


@pytest.mark.parametrize('mode',['decline','disabled','nonlord','other-faction','self','hongyan'])
def test_songwei_full_qualification_and_optional_decline(mode):
 from sanguosha.model.enums import Identity
 s=game();s.state.players['p1'].identity=Identity.LORD;s.state.players['p1'].granted_skills['songwei']='audit'
 if mode=='disabled':s.state.players['p1'].disabled_skills.add('songwei')
 if mode=='nonlord':s.state.players['p1'].identity=Identity.LOYALIST
 if mode=='other-faction':s.state.players['p2'].character_id='sunquan'
 if mode=='hongyan':s.state.players['p2'].granted_skills['hongyan']='audit'
 judged='p1' if mode=='self' else 'p2'
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=Suit.SPADE)
 before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
 s.engine.start_action(JudgmentAction('audit-songwei-'+mode,judged,JudgmentPattern()))
 if mode=='decline':
  assert s.engine.pending_request.player_id=='p2';s=restore(s);answer(s,False)
 else:assert s.engine.pending_request is None
 assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before

@pytest.mark.parametrize('definition,good',[('delayed.indulgence',Suit.HEART),('delayed.supply_shortage',Suit.CLUB)])
def test_delayed_success_does_not_skip_and_final_card_cleans(definition,good):
 from sanguosha.engine.military_tricks import ResolveDelayed
 s=game();cid=put(s,definition,'p1',ZoneType.JUDGMENT)
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=good)
 s.engine.start_action(ResolveDelayed('audit-safe','p1',cid));finish(s)
 assert not s.state.players['p1'].marks.get('skip_play') and not s.state.players['p1'].marks.get('skip_draw')
 assert {cid,top}<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
 assert next(e for e in s.events.events if getattr(e,'event_type','')=='delayed_result').metadata['outcome']=='safe'
 s=restore(s);s.state.__post_init__()

@pytest.mark.parametrize('rank,hit',[(1,False),(2,True),(9,True),(10,False)])
def test_lightning_final_rank_boundaries_and_no_next_target(rank,hit):
 from sanguosha.engine.military_tricks import ResolveDelayed
 s=game();s.state.players['p1'].hp=s.state.players['p1'].max_hp=8
 cid=put(s,'delayed.lightning','p1',ZoneType.JUDGMENT)
 for pid in ('p2','p3','p4','p5'):s.state.players[pid].granted_skills['weimu']='audit'
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=Suit.SPADE,rank=rank)
 s.engine.start_action(ResolveDelayed('audit-lightning-rank','p1',cid));finish(s)
 assert s.state.players['p1'].hp==(5 if hit else 8)
 assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
 s.state.__post_init__()


def test_judgment_phase_resolves_last_placed_delayed_first():
 from sanguosha.engine.phases import PhaseAction
 from sanguosha.model.enums import Phase
 s=game();put(s,'delayed.indulgence','p1',ZoneType.JUDGMENT);put(s,'delayed.supply_shortage','p1',ZoneType.JUDGMENT)
 s.engine.start_action(PhaseAction('audit-order','p1',Phase.JUDGMENT));finish(s)
 results=[e.metadata['definition_id'] for e in s.events.events if getattr(e,'event_type','')=='delayed_result']
 assert results==['delayed.supply_shortage','delayed.indulgence']


def test_final_retrial_public_history_and_destination_survive_tiandu_request():
 from sanguosha.multiplayer.room import MultiplayerRoom
 from sanguosha.projection import project_for_human
 s=game();s.state.players['p1'].granted_skills.update(hongyan='audit',tiandu='audit');s.state.players['p2'].granted_skills['guicai']='audit'
 cid=put(s,'basic.dodge','p2');s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.SPADE,rank=9)
 s.engine.start_action(JudgmentAction('audit-final-restore','p1',JudgmentPattern(suit=Suit.HEART)))
 answer(s,True);s=restore(s);answer(s,cid);s=restore(s)
 assert s.engine.pending_request.request_id.endswith(':tiandu')
 room=MultiplayerRoom();room.session=s;wire=room._named_projection(project_for_human(s.state,s.definitions,'p3',{}),'p3')
 changed=[e for e in wire['public_card_history'] if e['kind']=='JudgmentRevealedEvent'][-1]
 assert changed['effective_suit']=='heart' and changed['cards'][0]['suit']=='\u2665'
 assert cid in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
 answer(s,False);assert s.engine.last_result is True
 s.state.__post_init__()


def test_field_heart_failure_remains_ordinary_discard():
 from sanguosha.engine.mountain import TuntianAction,field_zone
 s=game();s.state.players['p2'].granted_skills['tuntian']='audit'
 cid=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.HEART)
 s.engine.start_action(TuntianAction('audit-field-fail','p2'));s=restore(s);answer(s,True)
 assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) and not s.state.cards_in(field_zone('p2'))


def test_game_finished_rejects_new_delayed_judgment():
 from sanguosha.engine.military_tricks import ResolveDelayed
 from sanguosha.engine.errors import InvalidEngineState
 from sanguosha.model.state import GameStatus
 s=game();cid=put(s,'delayed.lightning','p1',ZoneType.JUDGMENT);s.state.status=GameStatus.FINISHED
 with pytest.raises(InvalidEngineState):s.engine.start_action(ResolveDelayed('audit-terminal','p1',cid))
 assert s.engine.pending_request is None



def test_guidao_ai_preferred_material_is_evaluated_for_judged_player():
 s=game();s.state.players['p1'].granted_skills['hongyan']='audit';s.state.players['p2'].granted_skills['guidao']='audit'
 cid=put(s,'basic.slash','p2');s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.SPADE)
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=Suit.CLUB)
 s.engine.start_action(JudgmentAction('audit-guidao-context','p1',JudgmentPattern(suit=Suit.HEART)))
 assert 'better:'+cid in s.engine.pending_request.choices



def test_finish_judgment_skill_runs_before_default_discard_and_luoying():
 from sanguosha.model.enums import Identity
 s=game();s.state.players['p1'].identity=Identity.LORD;s.state.players['p1'].granted_skills['songwei']='audit';s.state.players['p3'].granted_skills['luoying']='audit'
 cid=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.CLUB)
 s.engine.start_action(JudgmentAction('audit-finish-before-clean','p2',JudgmentPattern()))
 assert s.engine.pending_request.player_id=='p2' and s.engine.pending_request.request_id.endswith(':songwei:offer')
 assert cid in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
 s=restore(s);answer(s,False)
 assert s.engine.pending_request.player_id=='p3'
 finish(s);s.state.__post_init__()


@pytest.mark.parametrize('zone', [ZoneType.HAND, ZoneType.EQUIPMENT, ZoneType.JUDGMENT])
@pytest.mark.parametrize('suit', [Suit.SPADE, Suit.HEART, Suit.CLUB, Suit.DIAMOND])
def test_hongyan_owned_face_and_suppression_are_contextual(zone, suit):
 from sanguosha.engine.suits import effective_suit, effective_color
 s=game();s.state.players['p1'].granted_skills['hongyan']='audit'
 cid=put(s,'equipment.weapon.crossbow' if zone is ZoneType.EQUIPMENT else 'basic.slash','p1',zone,EquipmentSlot.WEAPON if zone is ZoneType.EQUIPMENT else None)
 card=replace(s.state.cards[cid],suit=suit,rank=8);s.state.cards[cid]=card
 interpreted=Suit.HEART if suit is Suit.SPADE else suit
 assert effective_suit(s.state,cid) is interpreted
 assert effective_color(s.state,cid) is (Color.RED if interpreted in (Suit.HEART,Suit.DIAMOND) else Color.BLACK)
 assert effective_suit(s.state,cid,'p2') is suit
 assert s.state.cards[cid]==card
 s=restore(s);assert effective_suit(s.state,cid) is interpreted
 s.state.players['p1'].disabled_skills.add('hongyan')
 assert effective_suit(s.state,cid) is suit
 assert s.state.cards[cid].rank==8 and s.state.cards[cid].definition_id==card.definition_id



def test_nonterminal_lightning_death_cleans_delayed_processing_card():
 from sanguosha.engine.military_tricks import ResolveDelayed
 from sanguosha.model.enums import Identity
 from sanguosha.model.state import GameStatus
 s=game();s.state.players['p2'].hp=1;s.state.players['p2'].identity=Identity.LOYALIST
 s.state.players['p1'].identity=Identity.LORD;s.state.players['p3'].identity=Identity.REBEL
 cid=put(s,'delayed.lightning','p2',ZoneType.JUDGMENT)
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=Suit.SPADE,rank=5)
 s.engine.start_action(ResolveDelayed('audit-lightning-death','p2',cid));finish(s)
 assert not s.state.players['p2'].is_alive and s.state.status is not GameStatus.FINISHED
 assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
 assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
 s.state.__post_init__()



def test_lightning_transfer_continues_identically_from_finish_judge_snapshot():
 from sanguosha.engine.military_tricks import ResolveDelayed
 from sanguosha.model.enums import Identity
 from sanguosha.multiplayer.room import MultiplayerRoom
 from sanguosha.projection import project_for_human
 s=game();s.state.players['p1'].identity=Identity.LORD;s.state.players['p1'].granted_skills['songwei']='audit'
 cid=put(s,'delayed.lightning','p2',ZoneType.JUDGMENT)
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0];s.state.cards[top]=replace(s.state.cards[top],suit=Suit.CLUB,rank=5)
 s.engine.start_action(ResolveDelayed('audit-transfer-restore','p2',cid))
 while s.engine.pending_request and ':counter:' in s.engine.pending_request.request_id:
  answer(s,s.engine.pending_request.timeout_value())
 assert s.engine.pending_request.request_id.endswith(':songwei:offer')
 assert cid in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
 restored=restore(s)
 for session in (s,restored):
  answer(session,False)
  assert cid in session.state.cards_in(ZoneRef(ZoneType.JUDGMENT,'p3'))
  room=MultiplayerRoom();room.session=session
  history=room._named_projection(project_for_human(session.state,session.definitions,'p4',{}),'p4')['public_card_history']
  assert history[-1]['kind']=='DelayedResultEvent' and history[-1]['target_id']=='p3'
  session.state.__post_init__()
 assert restored.engine.pending_request is None
