"""Public HP/dying/terminal semantics, independent of a particular skill."""
from dataclasses import dataclass
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.dying import DyingAction
from sanguosha.engine.hp import LoseMaxHpAction
from sanguosha.engine.recovery import RecoverAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.events import HpRecoveredEvent,DamageDealtEvent
from sanguosha.model.enums import PlayerStatus,Identity
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef,ZoneType


def game():
 s=setup('xun_you')
 for p in s.state.players.values():p.character_id='sunquan'
 return s

@pytest.mark.parametrize('inactive',[False,True])
def test_rescue_order_starts_at_active_turn_seat_and_inactive_current_moves_last(inactive):
 s=game();s.state.current_player_id='p3';s.state.players['p2'].hp=0
 if inactive:s.state.current_phase=None
 s.engine.start_action(DyingAction('audit-dying-order','p2',None))
 assert s.engine.pending_request.player_id==('p4' if inactive else 'p3')


def test_same_rescuer_can_supply_multiple_peaches_before_next_seat():
 s=game();s.state.current_player_id='p3';s.state.players['p2'].hp=-1
 cards=tuple(put(s,'basic.peach','p3') for _ in range(2))
 s.engine.start_action(DyingAction('audit-dying-loop','p2',None))
 assert s.engine.pending_request.player_id=='p3'
 s=restore(s);answer(s,cards[0]);s=restore(s)
 assert s.engine.pending_request.player_id=='p3'
 answer(s,cards[1]);finish(s)
 assert s.state.players['p2'].hp==1

@pytest.mark.parametrize('condition',['full','dead'])
def test_recover_full_or_dead_target_is_noop_without_recovery_event(condition):
 s=game()
 if condition=='dead':s.state.players['p2'].status=PlayerStatus.DEAD
 before=s.state.players['p2'].hp;events=len(s.events.events)
 s.engine.start_action(RecoverAction('audit-no-recovery','p1','p2',1))
 assert s.state.players['p2'].hp==before
 assert not any(isinstance(e,HpRecoveredEvent) for e in s.events.events[events:])


def test_zero_max_hp_dies_without_ordinary_peach_rescue():
 s=game();s.state.players['p2'].max_hp=s.state.players['p2'].hp=1
 s.engine.start_action(LoseMaxHpAction('audit-zero-max','p2',1))
 assert s.engine.pending_request is None
 assert not s.state.players['p2'].is_alive


def test_damage_dead_source_is_normalized_to_no_source():
 s=game();s.state.players['p3'].status=PlayerStatus.DEAD
 s.engine.start_action(MilitaryDamageAction('audit-dead-source','p3','p2',1));finish(s)
 e=next(e for e in s.events.events if isinstance(e,DamageDealtEvent) and e.event_id=='audit-dead-source:dealt')
 assert e.source_id is None


def test_finished_game_rejects_new_top_level_response_request():
 from sanguosha.engine.response import RespondWithCardAction
 from sanguosha.engine.errors import InvalidEngineState
 s=game();s.state.status=GameStatus.FINISHED
 with pytest.raises(InvalidEngineState):s.engine.start_action(RespondWithCardAction('audit-after-game','p1','basic.dodge','source'))
 assert s.engine.pending_request is None


def test_parent_cannot_offer_ordinary_request_after_child_ends_game():
 from sanguosha.engine.actions import Action,StepResult
 from sanguosha.engine.death import DeathAction
 from sanguosha.engine.requests import PendingRequest,RequestType
 @dataclass(frozen=True,slots=True)
 class AfterDeath(Action):pass
 class Handler:
  def step(self,state,frame):
   if frame.step_index==0:
    frame.step_index=1;return StepResult.push(DeathAction('audit-last-enemy','p2',None))
   return StepResult.ask(PendingRequest('audit-forbidden-after-game','p1',RequestType.YES_NO,'ordinary',frame.action.action_id,frame.frame_id))
 s=game()
 for p in s.state.players.values():p.identity=Identity.LOYALIST
 s.state.players['p1'].identity=Identity.LORD;s.state.players['p2'].identity=Identity.REBEL
 s.engine.registry.register(AfterDeath,Handler())
 s.engine.start_action(AfterDeath('audit-parent-terminal'))
 assert s.state.status is GameStatus.FINISHED
 assert s.engine.pending_request is None and s.engine.stack.is_empty()

@pytest.mark.parametrize('buff',['anjian','luoyi'])
def test_source_damage_modifier_is_frozen_before_tianxiang_transfer(buff):
 from dataclasses import replace
 from sanguosha.model.enums import Suit
 s=game();s.state.current_player_id='p1'
 s.state.players['p3'].granted_skills['tianxiang']='audit'
 if buff=='anjian':s.state.players['p1'].granted_skills['anjian']='audit'
 else:s.state.players['p1'].marks['luoyi']=1
 card=put(s,'basic.slash');cost=put(s,'basic.dodge','p3');s.state.cards[cost]=replace(s.state.cards[cost],suit=Suit.HEART)
 s.engine.start_action(MilitaryDamageAction('audit-source-transfer','p1','p3',1,card_id=card,card_kind='slash'))
 s=restore(s);answer(s,True);s=restore(s);answer(s,cost);s=restore(s);answer(s,'p2');finish(s)
 assert s.state.players['p3'].hp==4 and s.state.players['p2'].hp==2

def test_transferred_damage_packet_does_not_repeat_source_luoyi_bonus():
 s=game();s.state.players['p1'].marks['luoyi']=1
 cid=put(s,'basic.slash')
 s.engine.start_action(MilitaryDamageAction('audit-transferred-ready','p1','p2',2,card_id=cid,card_kind='slash',redirected=True));finish(s)
 assert s.state.players['p2'].hp==2


@pytest.mark.parametrize('mode',['active','inactive','dead','suppressed'])
def test_wansha_only_living_effective_active_turn_owner_restricts_peach(mode):
 s=game();s.state.current_player_id='p3';s.state.players['p2'].hp=0
 s.state.players['p3'].granted_skills['wansha']='audit'
 if mode=='inactive':s.state.current_phase=None
 if mode=='dead':s.state.players['p3'].status=PlayerStatus.DEAD
 if mode=='suppressed':s.state.players['p3'].disabled_skills.add('wansha')
 s.engine.start_action(DyingAction('audit-wansha-'+mode,'p2',None))
 seen=[]
 while s.engine.pending_request:
  seen.append(s.engine.pending_request.player_id);s=restore(s);answer(s,s.engine.pending_request.timeout_value())
 assert seen==({'active':['p3','p2'],'inactive':['p4','p5','p1','p2','p3'],'dead':['p4','p5','p1','p2'],'suppressed':['p3','p4','p5','p1','p2']}[mode])


def test_rescuer_pass_advances_after_partial_recovery_and_self_wine_is_local():
 s=game();s.state.current_player_id='p3';s.state.players['p2'].hp=-1
 peach=put(s,'basic.peach','p3');other_wine=put(s,'basic.wine','p3');self_wine=put(s,'basic.wine','p2')
 s.engine.start_action(DyingAction('audit-peach-wine','p2',None))
 assert other_wine not in s.engine.pending_request.eligible_card_ids
 answer(s,peach);answer(s,s.engine.pending_request.timeout_value())
 assert s.engine.pending_request.player_id=='p4'
 while s.engine.pending_request.player_id!='p2':answer(s,s.engine.pending_request.timeout_value())
 assert s.engine.pending_request.player_id=='p2' and self_wine in s.engine.pending_request.eligible_card_ids
 s=restore(s);answer(s,self_wine)
 assert s.state.players['p2'].hp==1 and s.engine.pending_request is None


def test_lose_hp_is_not_damage_and_recovery_is_capped():
 from sanguosha.engine.hp import LoseHpAction
 s=game();s.state.players['p2'].granted_skills['renjie']='audit'
 s.engine.start_action(LoseHpAction('audit-loss','p2',2))
 assert not any(isinstance(e,DamageDealtEvent) for e in s.events.events)
 assert not s.state.players['p2'].marks.get('ren')
 s.engine.start_action(RecoverAction('audit-cap','p1','p2',8))
 e=next(e for e in s.events.events if isinstance(e,HpRecoveredEvent))
 assert s.state.players['p2'].hp==4 and e.amount==2


def test_death_skill_requests_finish_before_terminal_and_clean_public_cards():
 from sanguosha.engine.death import DeathAction
 from sanguosha.engine.card_moves import CardMove,CardMoveReason
 s=game();s.state.players['p1'].granted_skills['zhuiyi']='audit'
 s.state.players['p1'].identity=Identity.LORD
 s.state.players['p3'].hp=2
 moves=s.engine.reaction_provider.__self__
 cards=[]
 for index,ref in enumerate((ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.SPECIAL,special_key='amazing-grace'))):
  cid=put(s,'basic.slash','p4');cards.append(cid)
  moves.move(s.state,CardMove('audit-public-'+str(index),(cid,),ZoneRef(ZoneType.HAND,'p4'),ref,CardMoveReason.SYSTEM))
 s.engine.start_action(DeathAction('audit-lord-zhuiyi','p1','p2'))
 assert not s.state.players['p1'].is_alive and s.state.status is not GameStatus.FINISHED
 s=restore(s);answer(s,True);s=restore(s);answer(s,'p3')
 assert s.state.players['p3'].hp==3 and s.state.status is GameStatus.FINISHED
 assert s.engine.pending_request is None and s.engine.stack.is_empty()
 assert all(cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for cid in cards)
 s=restore(s);assert s.state.status is GameStatus.FINISHED and s.engine.pending_request is None


def test_chain_waits_for_first_dying_and_keeps_source_bonus_single():
 from sanguosha.model.enums import DamageNature
 s=game();s.state.players['p1'].marks['luoyi']=1
 s.state.players['p2'].hp=1
 for pid in ('p2','p3','p4'):s.state.players[pid].chained=True
 cid=put(s,'basic.fire_slash')
 s.engine.start_action(MilitaryDamageAction('audit-chain','p1','p2',1,DamageNature.FIRE,card_id=cid,card_kind='slash'))
 assert s.engine.pending_request and s.state.players['p3'].hp==4
 s=restore(s);finish(s)
 assert not s.state.players['p2'].is_alive
 assert s.state.players['p3'].hp==2 and s.state.players['p4'].hp==2
 assert all(not s.state.players[pid].chained for pid in ('p2','p3','p4'))

@pytest.mark.parametrize('allowed',[False,True])
def test_anjian_only_when_source_outside_victim_attack_range(allowed):
 s=game();s.state.players['p1'].granted_skills['anjian']='audit'
 target='p3' if allowed else 'p2';cid=put(s,'basic.slash')
 s.engine.start_action(MilitaryDamageAction('audit-anjian-range','p1',target,1,card_id=cid,card_kind='slash'));finish(s)
 assert s.state.players[target].hp==(2 if allowed else 3)


@pytest.mark.parametrize('rescuer,expected',[('sunquan',2),('caocao',1)])
def test_jiuyuan_requires_wu_rescuer_not_matching_lord_faction(rescuer,expected):
 s=game();s.state.current_player_id='p3'
 s.state.players['p2'].identity=Identity.LORD;s.state.players['p2'].character_id='caocao'
 s.state.players['p2'].granted_skills['jiuyuan']='audit';s.state.players['p2'].hp=0
 s.state.players['p3'].character_id=rescuer;cid=put(s,'basic.peach','p3')
 s.engine.start_action(DyingAction('audit-jiuyuan','p2',None));answer(s,cid)
 assert s.state.players['p2'].hp==expected


@pytest.mark.parametrize('mode',['disabled','chain','transfer','duel','normal'])
def test_anjian_negative_and_normal_slash_boundaries(mode):
 s=game();s.state.players['p1'].granted_skills['anjian']='audit'
 if mode=='disabled':s.state.players['p1'].disabled_skills.add('anjian')
 kind='duel' if mode=='duel' else 'slash';cid=put(s,'trick.duel' if mode=='duel' else 'basic.slash')
 s.engine.start_action(MilitaryDamageAction('audit-anjian-'+mode,'p1','p3',1,card_id=cid,card_kind=kind,propagated=mode=='chain',redirected=mode=='transfer'));finish(s)
 assert s.state.players['p3'].hp==(2 if mode=='normal' else 3)

@pytest.mark.parametrize('mode',['nonlord','disabled','self'])
def test_jiuyuan_lord_skill_does_not_buff_other_recovery(mode):
 s=game();s.state.current_player_id='p3';s.state.players['p2'].hp=0
 s.state.players['p2'].identity=Identity.LORD if mode!='nonlord' else Identity.LOYALIST
 if mode=='disabled':s.state.players['p2'].disabled_skills.add('jiuyuan')
 if mode=='self':s.state.current_player_id='p2'
 rescuer='p2' if mode=='self' else 'p3';cid=put(s,'basic.peach',rescuer)
 s.engine.start_action(DyingAction('audit-jiuyuan-'+mode,'p2',None));s=restore(s);answer(s,cid)
 assert s.state.players['p2'].hp==1


def test_wuhun_dead_owner_tie_request_resolves_nested_death_before_terminal():
 from dataclasses import replace
 from sanguosha.engine.death import DeathAction
 s=game();s.state.players['p1'].identity=Identity.LORD
 s.state.players['p1'].granted_skills['wuhun']='audit'
 for pid in ('p2','p3'):s.state.players[pid].marks['nightmare']=2
 top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
 s.state.cards[top]=replace(s.state.cards[top],definition_id='basic.slash')
 s.engine.start_action(DeathAction('audit-wuhun-terminal','p1',None))
 assert s.engine.pending_request.player_id=='p1' and not s.state.players['p1'].is_alive
 assert s.state.status is not GameStatus.FINISHED
 s=restore(s);answer(s,'p2');finish(s)
 assert not s.state.players['p2'].is_alive and s.state.status is GameStatus.FINISHED
 assert s.engine.pending_request is None and s.engine.stack.is_empty()
 assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_terminal_chain_never_damages_later_chained_seats():
 from sanguosha.model.enums import DamageNature
 s=game();s.state.players['p1'].identity=Identity.LOYALIST;s.state.players['p2'].identity=Identity.LORD;s.state.players['p2'].hp=1
 for pid in ('p2','p3'):s.state.players[pid].chained=True
 s.engine.start_action(MilitaryDamageAction('audit-terminal-chain','p1','p2',1,DamageNature.FIRE));s=restore(s);finish(s)
 assert s.state.status is GameStatus.FINISHED and s.state.players['p3'].hp==4
 assert s.engine.pending_request is None and s.engine.stack.is_empty()


@pytest.mark.parametrize('mode',['no-source','disabled','no-beneficiary'])
def test_zhuiyi_death_only_source_and_eligibility_boundaries(mode):
 from sanguosha.engine.death import DeathAction
 s=game();s.state.players['p1'].granted_skills['zhuiyi']='audit'
 if mode=='disabled':s.state.players['p1'].disabled_skills.add('zhuiyi')
 if mode=='no-beneficiary':
  for pid in ('p3','p4','p5'):s.state.players[pid].status=PlayerStatus.DEAD
 s.engine.start_action(DeathAction('audit-zhuiyi-'+mode,'p1',None if mode=='no-source' else 'p2'))
 if mode=='no-source':
  s=restore(s);answer(s,True)
  assert set(s.engine.pending_request.allowed_player_ids)=={'p2','p3','p4','p5'}
  s=restore(s);answer(s,'p2')
 else:assert s.engine.pending_request is None
 assert not s.state.players['p1'].is_alive
