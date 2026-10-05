"""Local-only deterministic real engine fixtures; never imported by production."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.multiplayer.room import RoomPhase, Controller
from sanguosha.engine.requests import RequestType
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.model.enums import Phase, Identity
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType, CardZone
from test_t6_military_basics import game, put
app=create_app(WebConfig(ai_presentation=True))
@app.post('/audit/fixture/{case}')
def fixture(case:str):
    eight=case.endswith('8')
    if eight:case=case[:-1]
    mode='military-eight' if eight else 'military-five'
    managed=app.state.room_manager.create(seed=3,mode_id=mode)
    room=managed.game
    pid,token=room.join('真人刘备',lambda _:None)
    from sanguosha.session import GameSession
    s=GameSession.new_game(military=True,mode_id=mode) if eight else game()
    s.state.current_phase=Phase.PLAY;s.state.turn_number=1
    room.session=s;room.phase=RoomPhase.IN_GAME
    for seat in room.seats.values():
        if seat.player_id!='p1': seat.controller=Controller.AI;seat.name='电脑'+seat.player_id[-1]
    ref=ZoneRef(ZoneType.DISCARD_PILE)
    s.state.zones.setdefault(ref,CardZone(ref))
    for pid in s.state.players:
        hand=s.state.zones[ZoneRef(ZoneType.HAND,pid)].card_ids
        s.state.zones[ZoneRef(ZoneType.DISCARD_PILE)].card_ids.extend(hand);hand.clear()
        s.state.players[pid].character_id='sunquan';s.character_names[pid]='孙权'
    s.state.players['p1'].character_id='liubei';s.state.players['p2'].character_id='caocao'
    s.character_names.update({'p1':'刘备','p2':'曹操','p3':'孙权','p4':'孙权','p5':'孙权'})
    s.state.players['p2'].identity=Identity.LORD;s.state.revealed_identities={'p2'}
    s.state.players['p1'].hp=2
    source='p1' if case in ('B','N','X') else 'p2' if case=='A' else 'p5'
    if source=='p5':
        s.state.players['p5'].character_id='caocao';s.character_names['p5']='曹操'
        s.state.players['p5'].identity=Identity.LORD;s.state.revealed_identities={'p5'}
    s.state.current_player_id=source;s.state.play_usage=PlayUsageState(source,1)
    definition={'X':'basic.dodge','P':'basic.dodge','Q':'equipment.weapon.crossbow','R':'equipment.weapon.crossbow','N':'trick.ex_nihilo','A':'basic.slash','B':'basic.slash','C':'trick.savage_assault','D':'trick.archery_attack','E':'trick.savage_assault','F':'trick.savage_assault'}[case]
    put(s,definition,source)
    if case=='R':
        put(s,'equipment.horse.dilu',source);put(s,'basic.peach',source);s.state.players[source].hp=2
    if case=='X':
        for pid in s.state.players:
            if pid!='p1':s.state.players[pid].face_up=False
    if case=='N':
        put(s,'trick.nullification','p2');s.state.players['p2'].identity=Identity.REBEL
        s.state.players['p1'].identity=Identity.LORD;s.state.revealed_identities={'p1'}
    if case in ('A','B'):put(s,'basic.dodge','p1' if case=='A' else 'p2')
    if case in ('C','D'):
        for pid in ('p1','p2','p3','p4'):put(s,'basic.slash' if case=='C' else 'basic.dodge',pid)
    if case in ('E','F'):
        put(s,'trick.nullification','p1');put(s,'trick.nullification','p3')
        s.state.players['p1'].identity=Identity.LORD;s.state.players['p2'].identity=Identity.REBEL
        s.state.players['p3'].identity=Identity.REBEL;s.state.revealed_identities={'p1'}
        card=next(cid for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,source)) if s.state.cards[cid].definition_id==definition)
        s.engine.start_action(UseCardAction('audit-'+case,source,card))
    elif case in ('P','Q','R'):
        from sanguosha.engine.turns import TurnAction
        s.state.turn_number=0
        s.engine.start_action(TurnAction('measured-turn',source,phases=(Phase.PLAY,Phase.FINISH)))
    else:s.engine.start_action(PhaseAction('audit-'+case,source,Phase.PLAY))
    room.pump()
    return {'roomCode':managed.code,'reconnectToken':token,'playerName':'真人刘备','seatId':'p1'}
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8008,log_level='warning')
