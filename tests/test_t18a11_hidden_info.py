"""Viewer wire payload invariance under concealed state changes."""
from dataclasses import replace
import json
import pytest
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.session import GameSession
from sanguosha.model.enums import Identity, Suit
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.projection import project_for_human
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.engine.events import CardMovedEvent


def payload(room, viewer):
    s = room.session
    return room._named_projection(project_for_human(s.state, s.definitions,
        viewer, s.character_names), viewer)


@pytest.mark.parametrize('mode', ('military-five', 'military-eight'))
@pytest.mark.parametrize('general', PLAYABLE_GENERAL_POOL, ids=lambda c: c.id)
def test_all_roster_wire_payloads_ignore_hidden_faces_ids_order_and_identity(mode, general):
    from sanguosha.pregame import Pregame
    from sanguosha.game_modes import game_mode
    setup = Pregame.create(17, mode)
    # Use the real production setup/initial areas, including gods' private stars.
    from sanguosha.pregame import SetupStage
    setup.generals = dict(zip(game_mode(mode).seats,
        [c.id for c in PLAYABLE_GENERAL_POOL[:game_mode(mode).seat_count]]))
    setup.stage = SetupStage.COMPLETE
    setup.generals['p2'] = general.id
    s = GameSession.new_game(seed=17, military=True, setup=setup)
    s.state.players['p1'].identity = Identity.LORD
    s.state.players['p2'].identity = Identity.REBEL
    s.state.players['p3'].identity = Identity.LOYALIST
    s.state.revealed_identities = {'p1'}
    room = MultiplayerRoom(seed=17, mode_id=mode)
    room.session = s
    before = json.dumps(payload(room, 'p1'), sort_keys=True, ensure_ascii=False)
    hidden_refs = [ref for ref in s.state.zones if
        ref.zone_type is ZoneType.DRAW_PILE or
        (ref.player_id not in (None, 'p1') and ref.zone_type is ZoneType.HAND) or
        (ref.player_id not in (None, 'p1') and ref.zone_type is ZoneType.SPECIAL
            and (ref.special_key == 'star' or ref.special_key.startswith('committed:')))]
    for ref in hidden_refs:
        zone = s.state.zones[ref]
        replacement = []
        for cid in zone.card_ids:
            secret = 'concealed-audit:' + str(cid)
            card = s.state.cards.pop(cid)
            s.state.cards[secret] = replace(card, instance_id=secret,
                definition_id='basic.peach', suit=Suit.DIAMOND, rank=13)
            replacement.append(secret)
        zone.card_ids[:] = reversed(replacement)
    s.state.players['p2'].identity = Identity.LOYALIST
    s.state.players['p3'].identity = Identity.REBEL
    if general.id == 'mountain_zuoci':
        s.state.players['p2'].transformation_pool = ['guanyu', 'ganning', 'yj2013_li_ru']
    after = json.dumps(payload(room, 'p1'), sort_keys=True, ensure_ascii=False)
    assert after == before
    assert 'concealed-audit:' not in after
    s.state.__post_init__()


@pytest.mark.parametrize('source,target,reason', (
    (ZoneRef(ZoneType.DRAW_PILE), ZoneRef(ZoneType.HAND, 'p2'), 'draw'),
    (ZoneRef(ZoneType.HAND, 'p2'), ZoneRef(ZoneType.HAND, 'p1'), 'obtain'),
    (ZoneRef(ZoneType.HAND, 'p2'), ZoneRef(ZoneType.SPECIAL, 'p2', special_key='star'), 'system'),
))
def test_private_card_moves_never_create_public_faces_or_ids(source, target, reason):
    s = GameSession.new_game(military=True, five_generals=True)
    room = MultiplayerRoom(); room.session = s
    cid = next(iter(s.state.cards))
    event = CardMovedEvent('private-transfer:' + cid, (cid,), source, target,
        reason, 'p1', None)
    assert room._public_event(event) is None
