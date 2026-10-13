"""Offline cross-client authority, hidden choices and full identity game smoke."""
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
from sanguosha.content.characters.boundary import BOUNDARY_GENERAL_POOL
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.session import GameSession
from sanguosha.pregame import Pregame,SetupStage
from sanguosha.model.state import GameStatus
from sanguosha.model.enums import Phase
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.engine.phases import PhaseAction,END_PLAY_PHASE
from sanguosha.engine.requests import Decision
from sanguosha.engine.boundary_combat import BoundaryCombatAction,POJUN_PREFIX
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.room_snapshot import snapshot_room,restore_room
from sanguosha.projection import project_for_human
from sanguosha.snapshot import snapshot_session,restore_session
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from test_t22_combat import answer,drain
from test_t19_2_test_mode import message,until

IDS=tuple(c.id for c in BOUNDARY_GENERAL_POOL)
ROOT=Path(__file__).resolve().parents[1]

def prepared(mode,selected,seed=2222):
    setup=Pregame.create(seed,mode)
    setup.generals={q:selected[i%len(selected)] for i,q in enumerate(setup.identities)}
    setup.stage=SetupStage.COMPLETE
    return GameSession.new_game(military=True,setup=setup)

@pytest.mark.parametrize('mode',['military-five','military-eight'])
@pytest.mark.parametrize('offset',[0,5])
def test_full_identity_games_finish_with_all_boundary_generals_and_reconnect(mode,offset):
    selected=IDS[offset:]+IDS[:offset]
    s=prepared(mode,selected,2222+offset)
    s.human_id='ai-only'
    restored=False
    for steps in range(30000):
        if s.state.status is GameStatus.FINISHED:break
        if s.engine.pending_request is not None and steps>=17 and not restored:
            for pid in s.state.seat_order:
                project_for_human(s.state,s.definitions,pid,s.character_names)
            s=restore_session(snapshot_session(s));restored=True
        s.ai.observe_public_events(s.state,s.events.events)
        assert s.step_auto()
        if steps%100==0:s.state.__post_init__()
    else:pytest.fail('full identity game exceeded finite decision bound')
    assert restored and s.state.victory is not None and s.engine.pending_request is None
    s.state.__post_init__()

@pytest.mark.parametrize('mode',['military-five','military-eight'])
def test_multiplayer_pojun_hidden_multiselect_and_mid_request_reconnect(mode):
    room=MultiplayerRoom(mode_id=mode)
    s=prepared(mode,('boundary_xu_sheng','sunquan'))
    room.session=s
    s.state.current_player_id='p1';s.state.current_phase=Phase.PLAY;s.state.turn_number=1
    cards=s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))[:2]
    s.engine.start_action(BoundaryCombatAction('mp-pojun','p1','jie_pojun','p2'))
    answer(s,True)
    request=s.engine.pending_request
    payload=room._request_payload(request)
    assert not any(cid in json.dumps(payload) for cid in cards)
    assert all(cid.startswith('hidden-hand:') for cid in payload['eligible_card_ids'])
    room=restore_room(snapshot_room(room));s=room.session
    assert room._request_payload(s.engine.pending_request)==payload
    value=tuple(payload['eligible_card_ids'][:2])
    decoded=room._resolve_hidden_choice(s.engine.pending_request,Decision(request.request_id,'p1',value))
    s.engine.submit_decision(decoded);drain(s)
    view=project_for_human(s.state,s.definitions,'p1',s.character_names)
    piles=next(p for p in view.players if p.player_id=='p2').special_piles
    pile=next(value for key,value in piles.items() if key.startswith(POJUN_PREFIX))
    assert len(pile)==2 and all(c.definition_id=='' and c.card_id.startswith('hidden:') for c in pile)
    assert not any(cid in json.dumps(payload) for cid in cards)
    s.state.__post_init__()

@pytest.mark.parametrize('general',BOUNDARY_GENERAL_POOL,ids=lambda c:c.id)
def test_pyside_descriptions_portraits_and_play_phase_use_the_authoritative_request(general):
    from sanguosha.ui.main_window import MainWindow
    from sanguosha.ui.resources import RESOURCES
    s=prepared('military-five',(general.id,'sunquan'))
    s.human_id='p1';s.state.current_player_id='p1';s.state.turn_number=1
    s.engine.start_action(PhaseAction('qt-play','p1',Phase.PLAY))
    w=MainWindow();w.session=s;w._render()
    assert s.engine.pending_request is not None
    assert '出牌' in w.decision.prompt_label.text()
    assert END_PLAY_PHASE in s.engine.pending_request.choices
    assert not RESOURCES.general_portrait(general.id,general.name).isNull()
    assert all(s.skills.skills[sid].name and s.skills.skills[sid].description for sid in general.skill_ids)
    w._submit_value(END_PLAY_PHASE)
    s.state.__post_init__();w.close()

@pytest.mark.parametrize('mode',['military-five','military-eight'])
def test_web_catalog_and_protected_test_draft_offer_and_select_every_boundary_general(mode):
    app=create_app(WebConfig(test_access_code='t22-local-fixture'))
    with TestClient(app) as client:
        catalog={item['id']:item for item in client.get('/api/catalog/generals').json()}
        manifest=json.loads((ROOT/'assets/manifest.json').read_text(encoding='utf-8'))
        for g in BOUNDARY_GENERAL_POOL:
            item=catalog[g.id]
            assert item['name']==g.name and item['max_hp']==g.max_hp and item['playable']
            assert all(s['name'] and s['description'] for s in item['skills'])
            assert (ROOT/'assets'/manifest['general.'+g.id]).is_file()
        assert client.post('/api/test-mode/authorize',json={'code':'t22-local-fixture'}).status_code==200
        cookie=client.cookies.get('sanguosha_test')
        # Two real socket drafts exercise the first and last additions in both modes.
        for gid in (IDS[0],IDS[-1]):
            with client.websocket_connect('/ws',headers={'cookie':f'sanguosha_test={cookie}'}) as socket:
                socket.send_json(message('HELLO'));until(socket,'WELCOME')
                socket.send_json(message('CREATE_ROOM',name='T22',single_player=True,mode_id=mode,test_room=True))
                code=until(socket,'ROOM_CREATED')['room_code'];welcome=until(socket,'WELCOME')
                draft=until(socket,'DRAFT_REQUEST')['request']
                assert set(IDS)<=set(draft['choices'])
                assert len(draft['choices'])==len(PLAYABLE_GENERAL_POOL)
                socket.send_json(message('SUBMIT_DECISION',decision={'request_id':draft['request_id'],'value':gid}))
                until(socket,'DECISION_RESULT')
                assert app.state.room_manager.rooms[code].game.pregame.generals[welcome['seat_id']]==gid


def test_pyside_jianying_response_button_submits_authoritative_material():
    from PySide6.QtWidgets import QPushButton
    from sanguosha.ui.main_window import MainWindow
    from sanguosha.engine.response import RespondWithCardAction
    from test_t22_advanced import game, colored
    s=game('ju_shou');s.human_id='p1'
    material=colored(s,'basic.dodge')
    s.state.players['p1'].hp=0
    s.engine.start_action(RespondWithCardAction('qt-save','p1','basic.peach','dying',subject_player_id='p1'))
    w=MainWindow();w.session=s;w._render()
    buttons=[b for b in w.decision.findChildren(QPushButton) if b.text().startswith('渐营 · ')]
    assert len(buttons)==1 and buttons[0].isEnabled() and '闪' in buttons[0].text()
    buttons[0].click()
    assert material in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert s.state.play_usage.count('skill.jie_jianying')==1
    s.state.__post_init__();w.close()
