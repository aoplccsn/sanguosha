"""T18A.6 public waiting, reconnect and lightweight AI regressions."""
from dataclasses import replace
import json
import pytest
from sanguosha.decisions.ai import AIDecisionProvider
from sanguosha.engine.requests import PendingRequest, RequestType, PASS_RESPONSE
from sanguosha.model.enums import EquipmentSlot, Identity
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.multiplayer.room import MultiplayerRoom, Controller, RoomPhase
from test_t6_military_basics import game, put
from test_t8_network_chains import configure


def request(kind, **kwargs):
    return PendingRequest('polish', 'p1', kind, '', 'action', 'frame', **kwargs)


def test_action_order_and_equipment_upgrade():
    s = game(); ai = AIDecisionProvider('human'); state = s.state
    slash = put(s, 'basic.slash'); draw = put(s, 'trick.ex_nihilo')
    armor = put(s, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    remove = put(s, 'trick.dismantlement')
    state.players['p1'].identity = Identity.REBEL
    state.players['p2'].identity = Identity.LORD; state.revealed_identities.add('p2')
    r = request(RequestType.CHOOSE_OPTION, choices=(f'use:{slash}', f'use:{draw}', f'use:{remove}', 'end_play_phase'))
    assert ai.decide(state, r).value == f'use:{draw}'
    r = replace(r, choices=(f'use:{slash}', f'use:{remove}', 'end_play_phase'))
    assert ai.decide(state, r).value == f'use:{remove}'
    state.players['p2'].hp = 1
    assert ai.decide(state, r).value == f'use:{slash}'
    put(s, 'equipment.weapon.kylin_bow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    worse = put(s, 'equipment.weapon.double_sword')
    assert ai._action_priority(state, 'p1', 'equipment.weapon.double_sword', ['p2']) < 0
    r = replace(r, choices=(f'use:{worse}', 'end_play_phase'))
    assert ai.decide(state, r).value == 'end_play_phase'


def test_low_hp_resources_and_visible_target_score():
    s = game(); ai = AIDecisionProvider('human'); state = s.state
    state.players['p1'].hp = 2
    assert ai._card_value(state, 'p1', 'basic.peach') > ai._card_value(state, 'p1', 'basic.slash')
    assert ai._card_value(state, 'p1', 'basic.dodge') > ai._card_value(state, 'p1', 'basic.slash')
    state.players['p2'].hp = 1; state.players['p3'].hp = 4
    assert ai._target_score(state, 'p1', 'p2') > ai._target_score(state, 'p1', 'p3')
    # Changing an opponent's hidden card definitions cannot change public scoring.
    before = ai._target_score(state, 'p1', 'p2')
    for cid in state.cards_in(ZoneRef(ZoneType.HAND, 'p2')):
        state.cards[cid] = replace(state.cards[cid], definition_id='basic.peach')
    assert ai._target_score(state, 'p1', 'p2') == before


def test_response_resource_tradeoff_never_at_low_hp():
    s = game(); ai = AIDecisionProvider('human'); state = s.state
    state.players['p1'].character_id = 'guojia'; state.players['p1'].hp = 4
    # Retain one scarce Dodge when full-health Yiji gains resources from damage.
    for cid in list(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))):
        state.cards[cid] = replace(state.cards[cid], definition_id='basic.slash')
    dodge = put(s, 'basic.dodge')
    r = request(RequestType.RESPOND_WITH_CARD, eligible_card_ids=(dodge,), required_definition_id='basic.dodge', allow_pass=True)
    assert ai.decide(state, r).value is PASS_RESPONSE
    state.players['p1'].hp = 1
    assert ai.decide(state, r).value == dodge


@pytest.mark.parametrize('mode', ['military-five', 'military-eight'])
def test_public_waiting_two_humans_reconnect_and_clear(mode, monkeypatch):
    clock = [1000.0]; monkeypatch.setattr('sanguosha.multiplayer.room.time.time', lambda: clock[0])
    room = MultiplayerRoom(mode_id=mode); messages = {pid: [] for pid in ('p1', 'p2')}
    for pid in messages:
        seat = room.seats[pid]; seat.controller = Controller.HUMAN; seat.connected = True; seat.send = messages[pid].append
    from sanguosha.pregame import Pregame, SetupStage
    from sanguosha.session import GameSession
    setup = Pregame.create(3, mode)
    from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
    setup.generals = dict(zip(setup.identities, [g.id for g in PLAYABLE_GENERAL_POOL]))
    setup.stage = SetupStage.COMPLETE
    room.session = GameSession.new_game(military=True, setup=setup); room.phase = RoomPhase.IN_GAME
    action, facts = configure('slash_dodge', room.session)
    room.session.engine.start_action(action)
    pending = room.session.engine.pending_request
    while pending.request_type is RequestType.YES_NO:
        from sanguosha.engine.requests import Decision
        room.session.engine.submit_decision(Decision(pending.request_id, pending.player_id, False))
        pending = room.session.engine.pending_request
    room.network_decisions.dispatch(pending)
    wait = next(m for m in reversed(messages['p1']) if m['type'] == 'PROJECTION_UPDATE')['projection']['waiting']
    assert wait['player_id'] == 'p2' and wait['responding'] and not wait['thinking']
    assert set(wait) == {'key', 'player_id', 'responding', 'thinking', 'remaining_ms', 'total_ms', 'required_definition_id', 'response_to', 'deadline'}
    assert 'eligible_card_ids' not in json.dumps(wait)
    deadline = room.request_deadline; clock[0] += 7.5
    room._send_current('p1')
    restored = messages['p1'][-1]['projection']['waiting']
    assert restored['key'] == wait['key']
    assert restored['total_ms'] == wait['total_ms'] == 60000
    assert restored['remaining_ms'] == wait['remaining_ms'] - 7500
    assert room.request_deadline == deadline
    room.session.engine.pending_request = None
    room._sync()
    assert messages['p1'][-1]['projection']['waiting'] is None


def test_thinking_profile_range_and_complexity():
    s = game(); ai = AIDecisionProvider('human')
    simple = request(RequestType.RESPOND_WITH_CARD, eligible_card_ids=('dodge',))
    complex = request(RequestType.CHOOSE_PLAYERS, allowed_player_ids=('p2', 'p3'), max_count=2)
    assert 1000 <= ai.thinking_profile(s.state, simple)[1] <= 2200
    assert 2600 <= ai.thinking_profile(s.state, complex)[1] <= 3000


def test_speed_changes_only_ai_wait_not_human_deadline(monkeypatch):
    clock = [1000.0]; monkeypatch.setattr('sanguosha.multiplayer.room.time.time', lambda: clock[0])
    room = MultiplayerRoom(); room.host_id = 'p1'; room.ai_deadline = 1004; room.request_deadline = 1060
    room.set_presentation_speed('p1', 'fast')
    assert room.ai_deadline == 1002.2 and room.request_deadline == 1060
    room.set_presentation_speed('p1', 'slow')
    assert room.ai_deadline == pytest.approx(1005.6) and room.request_deadline == 1060


def test_skill_cue_preserves_public_target_without_long_description():
    from sanguosha.engine.events import Event
    room = MultiplayerRoom()
    cue = room._public_event(Event('mingce', 'skill_mingce', 'p2', ('p3',)))
    assert cue['kind'] == 'SkillEvent' and cue['skill_name'] == '明策'
    assert cue['source_id'] == 'p2' and cue['target_ids'] == ['p3']


def test_real_ai_mingce_targets_ally_then_public_enemy():
    from sanguosha.engine.yj2011_tier3 import YJSkillAction
    from sanguosha.engine.requests import Decision
    from test_t17b_tier3 import game as tier3_game, active
    s = tier3_game(); active(s, 'chen_gong'); ai = AIDecisionProvider('human')
    s.state.players['p2'].identity = Identity.REBEL
    s.state.players['p1'].identity = Identity.REBEL
    s.state.players['p3'].identity = Identity.LORD
    s.state.revealed_identities.add('p3')
    put(s, 'basic.slash')
    s.engine.start_action(YJSkillAction('audit-mingce', 'p1', 'mingce'))
    room = MultiplayerRoom(); room.session = s
    selected = []
    for _ in range(20):
        r = s.engine.pending_request
        if r is None: break
        d = ai.decide(s.state, r); r.validate(d.value)
        if r.request_type is RequestType.CHOOSE_PLAYER: selected.append(d.value)
        since = len(s.events.events)
        s.engine.submit_decision(d)
        room._present_decision(r, d, since)
    assert selected[0] != 'p3' and selected[1] == 'p3'
    room = MultiplayerRoom(); room.session = s
    cues = [room._public_event(e) for e in s.events.events]
    assert any(cue and cue['kind'] == 'SkillEvent' and cue['skill_name'] == '明策' for cue in cues)
    assert s.engine.pending_request is None
