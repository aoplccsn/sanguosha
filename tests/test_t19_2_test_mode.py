from fastapi.testclient import TestClient

from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.multiplayer.protocol import PROTOCOL_VERSION
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig


def message(kind, **fields):
    return {'type': kind, 'version': PROTOCOL_VERSION, **fields}


def until(socket, kind):
    for _ in range(20):
        item = socket.receive_json()
        if item['type'] == kind:
            return item
    raise AssertionError(f'missing {kind}')


def test_test_room_requires_server_auth_and_normal_draft_rejects_forgery():
    app = create_app(WebConfig(test_access_code='fixture-only-code'))
    with TestClient(app) as client:
        assert client.post('/api/test-mode/authorize', json={'code': 'wrong'}).status_code == 403
        with client.websocket_connect('/ws') as socket:
            socket.send_json(message('HELLO'))
            until(socket, 'WELCOME')
            socket.send_json(message('CREATE_ROOM', name='访客', test_room=True))
            assert until(socket, 'ERROR')['message'] == 'test authorization required'

        with client.websocket_connect('/ws') as socket:
            socket.send_json(message('HELLO'))
            until(socket, 'WELCOME')
            socket.send_json(message('CREATE_ROOM', name='普通', single_player=True))
            code = until(socket, 'ROOM_CREATED')['room_code']
            until(socket, 'WELCOME')
            draft = until(socket, 'DRAFT_REQUEST')['request']
            assert len(draft['choices']) == 10
            forged = next(str(c.id) for c in PLAYABLE_GENERAL_POOL if str(c.id) not in draft['choices'])
            socket.send_json(message('SUBMIT_DECISION', decision={
                'request_id': draft['request_id'], 'value': forged}))
            assert until(socket, 'ERROR')['message'].startswith('illegal choice')
            assert not app.state.room_manager.rooms[code].game.pregame.generals

        authorized = client.post('/api/test-mode/authorize', json={'code': 'fixture-only-code'})
        assert authorized.status_code == 200
        assert 'HttpOnly' in authorized.headers['set-cookie']
        cookie = client.cookies.get('sanguosha_test')
        with client.websocket_connect('/ws', headers={'cookie': f'sanguosha_test={cookie}'}) as socket:
            socket.send_json(message('HELLO'))
            until(socket, 'WELCOME')
            socket.send_json(message('CREATE_ROOM', name='服主', single_player=True,
                                     mode_id='military-eight', test_room=True))
            code = until(socket, 'ROOM_CREATED')['room_code']
            welcome = until(socket, 'WELCOME')
            draft = until(socket, 'DRAFT_REQUEST')
            assert draft['test_room'] is True
            assert set(draft['request']['choices']) == {str(c.id) for c in PLAYABLE_GENERAL_POOL}
            assert len(draft['request']['choices']) == 108
            assert len(app.state.room_manager.rooms[code].game.seats) == 8
            socket.send_json(message('SUBMIT_DECISION', decision={
                'request_id': draft['request']['request_id'], 'value': 'mobile_god_lusu'}))
            until(socket, 'DECISION_RESULT')
            assert app.state.room_manager.rooms[code].game.pregame.generals[welcome['seat_id']] == 'mobile_god_lusu'
