"""Local-only real engine fixtures; never included in production routes."""
import sys,time
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.session import GameSession
from sanguosha.multiplayer.room import RoomPhase,Controller
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_tricks import TargetTrick
from sanguosha.engine.requests import Decision
from sanguosha.engine.skills import SkillRegistry
from sanguosha.engine.card_moves import CardMove,CardMoveReason
from sanguosha.model.enums import Phase,Suit,EquipmentSlot
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef,ZoneType,CardZone
from test_t6_military_basics import put
app=create_app(WebConfig(ai_presentation=False,room_creations_per_minute=100))
@app.post('/audit/new/{case}')
def fixture(case:str,mode:str='military-eight',general:str='mountain_zuoci'):
 managed=app.state.room_manager.create(seed=3,mode_id=mode);room=managed.game;room.timeout_seconds=900
 records=[]
 for i in range(room.mode.seat_count):
  pid,token=room.join('验收'+str(i+1),lambda _:None)
  records.append(dict(roomCode=managed.code,reconnectToken=token,playerName='验收'+str(i+1),seatId=pid))
 from sanguosha.pregame import Pregame,SetupStage
 setup=Pregame.create(3,mode);setup.generals=dict(zip(room.seats,[general,'zhaoyun','liubei','sunquan','lvbu','guanyu','simayi','zhangliao']));setup.stage=SetupStage.COMPLETE
 s=GameSession.new_game(military=True,setup=setup);room.session=s;room.phase=RoomPhase.IN_GAME
 s.state.current_player_id='p1';s.state.current_phase=Phase.PLAY;s.state.turn_number=1;s.state.play_usage=PlayUsageState('p1',1)
 s.state.zones.setdefault(ZoneRef(ZoneType.DISCARD_PILE),CardZone(ZoneRef(ZoneType.DISCARD_PILE)))
 registry=SkillRegistry()
 for i,pid in enumerate(s.state.seat_order):
  hand=s.state.cards_in(ZoneRef(ZoneType.HAND,pid))
  s.state.zones[ZoneRef(ZoneType.HAND,pid)].card_ids.clear();s.state.zones[ZoneRef(ZoneType.DISCARD_PILE)].card_ids.extend(hand)
  c=general if i==0 else ['zhaoyun','liubei','sunquan','lvbu','guanyu','simayi','zhangliao'][i-1]
  s.state.players[pid].character_id=c;s.character_names[pid]=registry.characters[c].name
 put(s,'equipment.horse.jueying','p3',ZoneType.EQUIPMENT,EquipmentSlot.DEFENSIVE_HORSE)
 put(s,'equipment.horse.chitu','p4',ZoneType.EQUIPMENT,EquipmentSlot.OFFENSIVE_HORSE)
 s.state.players['p3'].chained=True;s.state.players['p4'].chained=True
 slash=put(s,'basic.slash');s.state.cards[slash]=replace(s.state.cards[slash],suit=Suit.SPADE)
 peach=put(s,'basic.peach');s.state.cards[peach]=replace(s.state.cards[peach],suit=Suit.HEART)
 put(s,'basic.dodge');s.state.players['p1'].hp=2
 target=put(s,'basic.peach','p2');s.state.cards[target]=replace(s.state.cards[target],suit=Suit.HEART)
 put(s,'basic.slash','p2')
 if case=='full':
  for _ in range(9):put(s,'basic.slash')
  for d,slot in [('equipment.weapon.crossbow',EquipmentSlot.WEAPON),('equipment.armor.eight_trigrams',EquipmentSlot.ARMOR),('equipment.horse.chitu',EquipmentSlot.OFFENSIVE_HORSE),('equipment.horse.jueying',EquipmentSlot.DEFENSIVE_HORSE)]:
   put(s,d,'p1',ZoneType.EQUIPMENT,slot)
  put(s,'delayed.indulgence','p1',ZoneType.JUDGMENT)
 if case=='recast':
  s.state.players['p1'].granted_skills['jizhi']='audit'
  cid=put(s,'trick.iron_chain')
  s.engine.start_action(UseCardAction('recast-card','p1',cid))
 elif case=='qixi':
  p=s.state.players['p1'];p.transformation_pool=['ganning'];p.active_transformation='ganning';p.transformation_skill='qixi'
  s.engine.start_action(PhaseAction('qixi-play','p1',Phase.PLAY))
 elif case in ('fire','fire_none'):
  if case=='fire_none':
   for c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')):s.state.cards[c]=replace(s.state.cards[c],suit=Suit.CLUB)
  c=put(s,'trick.fire_attack');s.engine.start_action(UseCardAction('fire-fixture','p1',c,('p2',)))
 elif case in ('dismantle','snatch','savage','archery','counter_single','counter_group','harvest'):
  d={'snatch':'trick.snatch','dismantle':'trick.dismantlement','savage':'trick.savage_assault','archery':'trick.archery_attack','counter_single':'trick.duel','counter_group':'trick.savage_assault','harvest':'trick.amazing_grace'}[case]
  if case.startswith('counter') or case in ('savage','archery'):put(s,'trick.nullification')
  c=put(s,d);s.engine.start_action(UseCardAction('fixture-'+case,'p1',c,('p2',) if case in ('dismantle','snatch','counter_single') else ()))
 else:
  if case=='takeover':room.seats['p2'].ai_controlled=True;room.seats['p2'].controller=Controller.AI
  s.engine.start_action(PhaseAction('layout-play','p1',Phase.PLAY))
 room._seen_events=len(s.events.events)
 room.pump();return records
@app.post('/audit/advance/{code}')
def advance(code:str):
 room=app.state.room_manager.get(code).game;s=room.session;r=s.engine.pending_request
 value=room._ai.decide(s.state,r).value
 room.submit(r.player_id,Decision(r.request_id,r.player_id,value));return {'ok':True}
@app.post('/audit/discard/{code}')
def discard(code:str):
 room=app.state.room_manager.get(code).game;s=room.session;cards=s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))[:3]
 s.engine.reaction_provider.__self__.move(s.state,CardMove('public-three',cards,ZoneRef(ZoneType.HAND,'p1'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,'p1'))
 room._sync();return {'ok':True}
@app.post('/audit/general/{code}/{general}')
def general(code:str,general:str):
 room=app.state.room_manager.get(code).game;s=room.session;s.state.players['p1'].character_id=general;s.character_names['p1']=SkillRegistry().characters[general].name
 room._sync();return {'ok':True}
@app.get('/audit/state/{code}')
def audit_state(code:str):
 from sanguosha.engine.events import TurnStartedEvent
 s=app.state.room_manager.get(code).game.session
 turns=[e.turn_number for e in s.events.events if isinstance(e,TurnStartedEvent)]
 return {'first_turn':turns[0] if turns else None,'generals':[p.character_id for p in s.state.players.values()], 'recasts':sum(getattr(e,'reason',None)=='recast' and getattr(e,'to_zone',None).zone_type is ZoneType.DISCARD_PILE for e in s.events.events), 'used_iron_chains':sum(getattr(e,'virtual_definition_id',None)=='trick.iron_chain' or type(e).__name__=='CardUsedEvent' and e.card_id in s.state.cards and s.state.cards[e.card_id].definition_id=='trick.iron_chain' for e in s.events.events)}
@app.post('/audit/reset')
def reset():
 app.state.room_manager.rooms.clear();return {'ok':True}
app.router.routes[:]=[r for r in app.router.routes if getattr(r,'path','').startswith('/audit/')]+[r for r in app.router.routes if not getattr(r,'path','').startswith('/audit/')]
if __name__=='__main__':
 import uvicorn
 from sanguosha.web.__main__ import web_loop
 uvicorn.run(app,host='127.0.0.1',port=8012,log_level='warning',loop=web_loop())
