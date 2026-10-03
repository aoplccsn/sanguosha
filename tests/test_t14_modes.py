"""Five- and eight-seat identity mode contracts."""

from collections import Counter

from sanguosha.game_modes import MILITARY_EIGHT, MILITARY_FIVE
from sanguosha.model.enums import Identity
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
from sanguosha.room_snapshot import restore_room, snapshot_room
from sanguosha.engine.requests import Decision
from sanguosha.engine.requests import PendingRequest, RequestType
from sanguosha.projection import project_for_human
from sanguosha.model.zones import ZoneRef, ZoneType


def test_mode_definitions_have_classic_role_distributions():
    assert Counter(MILITARY_FIVE.roles) == {
        Identity.LORD: 1, Identity.LOYALIST: 1,
        Identity.REBEL: 2, Identity.RENEGADE: 1}
    assert Counter(MILITARY_EIGHT.roles) == {
        Identity.LORD: 1, Identity.LOYALIST: 2,
        Identity.REBEL: 4, Identity.RENEGADE: 1}


def test_eight_player_session_and_snapshot_restore():
    session = GameSession.new_game(military=True, five_generals=True,
                                   mode_id='military-eight')
    assert len(session.state.players) == 8
    assert session.state.metadata['mode_id'] == 'military-eight'
    restored = restore_session(snapshot_session(session))
    assert len(restored.state.players) == 8
    assert restored.state.seat_order == session.state.seat_order


def test_eight_player_pregame_distributes_roles_without_duplicates():
    setup = Pregame.create(11, 'military-eight')
    assert set(setup.identities) == set(MILITARY_EIGHT.seats)
    assert Counter(setup.identities.values()) == Counter(MILITARY_EIGHT.roles)


def test_eight_player_room_autofills_ai_and_restores():
    room = MultiplayerRoom(seed=8, mode_id='military-eight', allow_gods=True)
    sent = []
    host, _ = room.join('host', sent.append)
    guest, _ = room.join('guest', sent.append)
    room.ready(guest, True)
    room.start(host)
    assert room.phase is RoomPhase.DRAFT
    assert len(room.seats) == 8
    assert sum(seat.controller.value == 'AI' for seat in room.seats.values()) == 6
    restored = restore_room(snapshot_room(room))
    assert restored.mode.mode_id == 'military-eight'
    assert restored.allow_gods
    assert len(restored.seats) == 8


def test_switching_to_five_preserves_human_seats():
    room = MultiplayerRoom(mode_id='military-eight')
    host, _ = room.join('host', lambda _: None)
    room.join('guest', lambda _: None)
    room.configure(host, mode_id='military-five')
    assert len(room.seats) == 5
    assert room.seats['p2'].name == 'guest'


def test_eight_player_mixed_room_starts_shared_game_with_private_identities():
    room = MultiplayerRoom(seed=17, mode_id='military-eight', allow_gods=True)
    host, _ = room.join('host', lambda _: None)
    guest, _ = room.join('guest', lambda _: None)
    room.ready(guest, True)
    room.start(host)
    for pid in (host, guest):
        request = room.draft_requests[pid]
        room.submit(pid, Decision(request.request_id, pid, request.choices[0]))
    assert room.phase in (RoomPhase.IN_GAME, RoomPhase.FINISHED)
    assert len(room.session.state.players) == 8
    view = project_for_human(room.session.state, room.session.definitions,
                             host, room.session.character_names)
    for player in view.players:
        if player.player_id not in (host, room.pregame.lord_id):
            assert player.identity_label == '未知'


def test_lobby_disconnect_keeps_token_and_kick_releases_seat():
    room = MultiplayerRoom(mode_id='military-eight')
    host, _ = room.join('host', lambda _: None)
    guest, token = room.join('guest', lambda _: None)
    room.disconnect(guest)
    assert room.seats[guest].controller.value == 'HUMAN'
    assert not room.seats[guest].connected
    rejoined, same_token = room.join('guest', lambda _: None, token=token)
    assert rejoined == guest and same_token == token
    room.kick(host, guest)
    assert room.seats[guest].controller.value == 'EMPTY'


def test_mode_switch_refuses_to_drop_an_occupied_human_seat():
    from sanguosha.multiplayer.room import RoomError
    import pytest
    room = MultiplayerRoom(mode_id='military-eight')
    host, _ = room.join('host', lambda _: None)
    for index in range(5):
        room.join(f'guest-{index}', lambda _: None)
    with pytest.raises(RoomError, match='occupied'):
        room.configure(host, mode_id='military-five')
    assert room.mode.mode_id == 'military-eight'


def test_hidden_opponent_hand_uses_opaque_choice_and_restores_after_snapshot():
    room = MultiplayerRoom(mode_id='military-eight')
    room.session = GameSession.new_game(military=True, five_generals=True,
                                        mode_id='military-eight')
    hand = room.session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    request = PendingRequest('private-choice', 'p1', RequestType.CHOOSE_CARD,
                             '选择目标手牌', 'action', 'frame',
                             eligible_card_ids=hand, subject_player_id='p2')
    payload = room._request_payload(request)
    assert payload['eligible_card_ids'] == [f'hidden-hand:{i}' for i in range(1, len(hand) + 1)]
    assert not any(card in str(payload) for card in hand)
    restored = restore_room(snapshot_room(room))
    assert restored._request_payload(request)['eligible_card_ids'] == payload['eligible_card_ids']
    decision = restored._resolve_hidden_choice(request, Decision('private-choice', 'p1', 'hidden-hand:1'))
    assert decision.value == hand[0]
