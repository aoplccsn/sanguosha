"""Local-only 103-candidate acceptance. Production roster gates stay unchanged."""
import sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.multiplayer.room import RoomPhase
from sanguosha.session import GameSession
from sanguosha.pregame import Pregame,SetupStage
from sanguosha.engine.skills import SkillRegistry
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import Decision,PendingRequest,RequestType
from sanguosha.engine.card_moves import CardMove,CardMoveReason
from sanguosha.model.enums import Phase,Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef,ZoneType
from test_t6_military_basics import put
from test_t17b_tier1 import answer
from dataclasses import replace
app=create_app(WebConfig(ai_presentation=False))

@app.get('/audit/catalog')
def catalog():
    registry=SkillRegistry();manifest=json.loads((ROOT/'web/dist/assets/manifest.json').read_text(encoding='utf-8'))
    return [dict(id=c.id,name=c.name,kingdom=c.kingdom.value,max_hp=c.max_hp,pack=c.metadata.get('pack',''),
        implemented=c.metadata.get('implemented',True),playable=c.metadata.get('playable',True),portrait_mode=c.metadata.get('portrait_mode','static'),
        portrait='/assets/'+manifest['general.'+c.id],skills=[dict(id=sid,name=registry.skills[sid].name,description=registry.skills[sid].description,type=registry.skills[sid].skill_type.value) for sid in c.skill_ids]) for c in registry.characters.values()]

@app.post('/audit/new/{case}')
async def fixture(case:str,general:str='yj2012_xun_you'):
    managed=app.state.room_manager.create(seed=3,mode_id='military-eight');room=managed.game;room.timeout_seconds=900
    records=[]
    for i in range(8):
        pid,token=room.join('验收'+str(i+1),lambda _:None)
        records.append(dict(roomCode=managed.code,reconnectToken=token,playerName='验收'+str(i+1),seatId=pid))
    registry=SkillRegistry();setup=Pregame.create(3,'military-eight')
    if case=='zongxuan':general='yj2013_yu_fan'
    if case=='poxi':general='thunder_god_ganning'
    if case=='duorui':general='thunder_god_zhangliao'
    others=[c for c in ('caocao','liubei','sunquan','lvbu','guanyu','simayi','zhangliao','zhaoyun') if c!=general]
    setup.generals=dict(zip(room.seats,[general,*others[:7]]));setup.stage=SetupStage.COMPLETE
    s=GameSession.new_game(seed=3,military=True,setup=setup);room.session=s;room.phase=RoomPhase.IN_GAME
    s.state.current_player_id='p1';s.state.current_phase=Phase.PLAY;s.state.turn_number=1;s.state.play_usage=PlayUsageState('p1',1)
    moves=s.engine.reaction_provider.__self__
    for pid in s.state.seat_order:
        ids=s.state.cards_in(ZoneRef(ZoneType.HAND,pid))
        if ids:moves.move(s.state,CardMove('fixture-empty:'+pid,ids,ZoneRef(ZoneType.HAND,pid),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    s.state.metadata['reaction_event_cursor']=len(s.events.events);moves.reactions.clear()
    if case=='zongxuan':
        cards=(put(s,'basic.slash'),put(s,'basic.dodge'),put(s,'basic.peach'))
        moves.move(s.state,CardMove('fixture-cost',cards,ZoneRef(ZoneType.HAND,'p1'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,'p1'))
        s.engine.start_action(moves.next_reaction(s.state))
    elif case=='poxi':
        from sanguosha.engine.remaining_gods import RemainingGodAction
        for pid,suit,d in (('p1',Suit.SPADE,'basic.slash'),('p1',Suit.HEART,'basic.peach'),('p2',Suit.CLUB,'basic.dodge'),('p2',Suit.DIAMOND,'basic.wine')):
            cid=put(s,d,pid);s.state.cards[cid]=replace(s.state.cards[cid],suit=suit)
        s.engine.start_action(RemainingGodAction('fixture-poxi','p1','poxi'));answer(s,'p2')
    elif case=='duorui':
        from sanguosha.engine.military_basics import MilitaryDamageAction
        s.engine.start_action(MilitaryDamageAction('fixture-duorui','p1','p2',1));answer(s,True)
    elif case=='draft':
        room.pregame=Pregame.create(3,'military-eight');room.phase=RoomPhase.DRAFT;room.session=None
        choices=tuple([general,*[c.id for c in registry.characters.values() if c.id!=general][:9]])
        room.draft_requests['p1']=PendingRequest('audit-draft','p1',RequestType.CHOOSE_OPTION,'选择武将并确认','draft','draft',choices=choices)
        room.draft_deadlines['p1']=time.time()+900
        room.pregame.generals={pid:c for pid,c in setup.generals.items() if pid!='p1'}
    else:
        put(s,'basic.dodge');s.engine.start_action(PhaseAction('fixture-play','p1',Phase.PLAY))
    room.pump()
    return records

# Keep local audit routes before the SPA catch-all.
app.router.routes[:]=[r for r in app.router.routes if getattr(r,'path','').startswith('/audit/')]+[r for r in app.router.routes if not getattr(r,'path','').startswith('/audit/')]

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8018,log_level='warning')
