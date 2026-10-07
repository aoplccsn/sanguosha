"""Loopback-only T20.3 browser fixture, using the production room and engine."""
from dataclasses import replace
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.multiplayer.room import RoomPhase
from sanguosha.session import GameSession
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.card_moves import CardMoveService, CardMove, CardMoveReason
from sanguosha.model.enums import Identity, PlayerStatus, Phase, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType

app=create_app(WebConfig(ai_presentation=False,test_access_code='fixture-only-code',room_creations_per_minute=100))

@app.post('/api/t203/scene/{code}')
async def scenario(code:str):
    room=app.state.room_manager.get(code).game
    s=GameSession.new_game(military=True,five_generals=True)
    s.state.current_player_id='p1';s.state.revealed_identities={'p2','p4','p5'}
    for pid,identity in zip(('p1','p2','p3'),(Identity.LOYALIST,Identity.LORD,Identity.REBEL)):
        s.state.players[pid].identity=identity
        s.state.players[pid].character_id='sunquan' if pid=='p1' else 'caocao'
    for pid in ('p4','p5'):s.state.players[pid].status=PlayerStatus.DEAD
    def put(definition,zone=ZoneType.HAND,slot=None):
        cid=next(iter(s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))))
        s.state.cards[cid]=replace(s.state.cards[cid],definition_id=definition)
        CardMoveService(s.events).move(s.state,CardMove('fixture:'+cid,(cid,),ZoneRef(ZoneType.DRAW_PILE),ZoneRef(zone,'p1',slot),CardMoveReason.SYSTEM))
        return cid
    chain=put('trick.iron_chain');equipment=put('equipment.weapon.crossbow',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    for _ in range(22):put('basic.dodge')
    s.engine.start_action(PhaseAction('t203-play','p1',Phase.PLAY))
    room.session=s;room.phase=RoomPhase.IN_GAME;room._last_request_id=None;room._seen_events=len(s.events.events)
    room.presentation_deadline=None;room.ai_deadline=None;room.turn_visible_until=None
    room.pump()
    return {'chain':chain,'equipment':equipment}

@app.post('/api/t203/state/{code}')
async def result(code:str):
    s=app.state.room_manager.get(code).game.session
    return {'chained':[str(pid) for pid,p in s.state.players.items() if p.chained],
        'discard':list(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))),
        'hand':list(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))}
