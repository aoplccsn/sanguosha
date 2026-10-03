"""Durable acceptance, independent ACK and alarm continuation regression."""

import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import patch

from test_t9_2_cloudflare_game_room import worker_module
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.room_snapshot import restore_room


def test_ack_precedes_resolution_and_survives_hibernation(worker_module, monkeypatch):
    async def scenario():
        messages = []
        storage_data = {}
        timeline = []
        class Storage:
            async def get(self, key):
                return storage_data.get(key)
            async def put(self, key, value):
                storage_data[key] = value
                timeline.append(('persist', key))
            async def setAlarm(self, value):
                timeline.append(('alarm', value))
            async def deleteAll(self):
                storage_data.clear()
        class Socket:
            def send(self, value):
                message = json.loads(value)
                messages.append(message)
                timeline.append(('send', message['type']))
        ws = Socket()
        room = MultiplayerRoom(seed=4)
        pid, _ = room.join('host', lambda _: None)
        room.start(pid)
        request = room.draft_requests[pid]
        choice = request.choices[0]
        deadline = time.time() + 0.1
        room.draft_deadlines[pid] = deadline
        do = object.__new__(worker_module.GameRoomDurableObject)
        do.ctx = SimpleNamespace(storage=Storage(), getWebSockets=lambda: [])
        do.env = SimpleNamespace()
        do.room, do.room_code = room, 'ABC234'
        do.sockets, do.rate = {}, {}
        do._active_decision_id = None
        monkeypatch.setattr(worker_module, '_attachment', lambda _: {'player_id': pid, 'session_id': 'test'})
        message = {'type': 'SUBMIT_DECISION', 'version': 2,
                   'decision': {'request_id': request.request_id, 'value': choice}}
        await do.webSocketMessage(ws, json.dumps(message))
        ack = next(message for message in messages if message['type'] == 'DECISION_ACCEPTED')
        assert ack['request_id'] == request.request_id
        assert room.session is None, 'no draft completion/engine work before ACK event ends'
        assert pid not in room.draft_requests
        assert timeline.index(('persist', worker_module.SNAPSHOT_KEY)) < timeline.index(('send', 'DECISION_ACCEPTED'))
        stored = restore_room(storage_data[worker_module.SNAPSHOT_KEY].encode())
        assert stored.accepted_request_id == request.request_id
        assert stored.pregame.generals[pid] == choice
        # Browser delays ACK/projection; deadline passes and DO resumes from storage.
        do.room = None
        with patch('sanguosha.multiplayer.room.time.time', return_value=deadline + 2):
            await do.alarm()
        assert do.room.pregame.generals[pid] == choice
        assert do.room.session is not None
        assert do.room.accepted_request_id is None
        restored = restore_room(storage_data[worker_module.SNAPSHOT_KEY].encode())
        assert restored.pregame.generals[pid] == choice
    asyncio.run(scenario())


def test_restored_public_room_uses_60_seconds_for_future_requests(worker_module):
    from sanguosha.room_snapshot import snapshot_room
    async def scenario():
        room = MultiplayerRoom(timeout_seconds=30)
        pid, _ = room.join('host', lambda _: None)
        room.start(pid)
        deadlines = dict(room.draft_deadlines)
        snapshot = snapshot_room(room)
        class Storage:
            async def get(self, key):
                return snapshot if key == worker_module.SNAPSHOT_KEY else 'ABC234'
        do = object.__new__(worker_module.GameRoomDurableObject)
        do.room, do.room_code = None, ''
        do.ctx = SimpleNamespace(storage=Storage(), getWebSockets=lambda: [])
        assert await do._load()
        assert do.room.timeout_seconds == 60
        assert do.room.draft_deadlines == deadlines
    asyncio.run(scenario())
