"""Local production-dist acceptance fixture; never deployed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tests'))
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.multiplayer.room import RoomPhase
from sanguosha.engine.card_use import UseCardAction
from sanguosha.model.enums import Phase, EquipmentSlot
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType, CardZone
from sanguosha.session import GameSession
from test_t6_military_basics import put
app = create_app(WebConfig(ai_presentation=True))
@app.post('/audit/fixture/{case}')
async def fixture(case: str):
    interrupt=case=='harvest_interrupt'
    if interrupt: case='harvest'
    managed = app.state.room_manager.create(seed=3, mode_id='military-eight')
    room = managed.game
    room.timeout_seconds=300
    sessions = []
    for i in range(8):
        pid, token = room.join(f'真人{i+1}', lambda _: None)
        sessions.append(dict(roomCode=managed.code, reconnectToken=token, playerName=f'真人{i+1}', seatId=pid))
    s = GameSession.new_game(military=True, mode_id='military-eight')
    room.session=s; room.phase=RoomPhase.IN_GAME
    s.state.current_player_id='p1'; s.state.current_phase=Phase.PLAY; s.state.turn_number=1
    s.state.play_usage=PlayUsageState('p1',1)
    ref=ZoneRef(ZoneType.DISCARD_PILE)
    s.state.zones.setdefault(ref,CardZone(ref))
    for i,pid in enumerate(s.state.seat_order):
        hand=s.state.zones[ZoneRef(ZoneType.HAND,pid)].card_ids
        s.state.zones[ZoneRef(ZoneType.DISCARD_PILE)].card_ids.extend(hand); hand.clear()
        general=['zhaoyun','forest_caopi','lvmeng','forest_lusu','sunshangxiang','luxun','wind_zhang_jiao','mountain_god_simayi'][i]
        s.state.players[pid].character_id=general
        from sanguosha.engine.skills import SkillRegistry
        registry=SkillRegistry()
        s.character_names[pid]=registry.characters[general].name
    for d in ['basic.slash','basic.dodge','basic.peach','basic.wine']: put(s,d)
    put(s,'basic.slash','p2'); put(s,'basic.peach','p2')
    put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    definition={'snatch':'trick.snatch','dismantle':'trick.dismantlement','harvest':'trick.amazing_grace','slash':'basic.slash'}[case]
    if case=='harvest':
        from dataclasses import replace
        for cid in s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE)):
            s.state.cards[cid]=replace(s.state.cards[cid],definition_id='trick.nullification' if interrupt else 'basic.slash')
    card=put(s,definition)
    if case=='slash':
        put(s,'basic.dodge','p2')
        from sanguosha.engine.phases import PhaseAction
        s.engine.start_action(PhaseAction('audit-slash-play','p1',Phase.PLAY))
    else:
        s.engine.start_action(UseCardAction('audit-'+case,'p1',card,() if case=='harvest' else ('p2',)))
    room.pump()
    return sessions
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8009,log_level='warning')
