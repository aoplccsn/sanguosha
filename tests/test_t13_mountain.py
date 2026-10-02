"""Targeted classic Mountain rule tests."""

import pytest

from sanguosha.engine.mountain import QiaobianAction
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import EquipmentSlot, Phase
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from test_t6_military_basics import put


@pytest.mark.parametrize('phase', (Phase.JUDGMENT, Phase.DRAW, Phase.PLAY, Phase.DISCARD))
def test_qiaobian_discards_hand_card_and_marks_only_legal_phase(phase):
    session = GameSession.new_game(military=True, five_generals=True)
    player = session.state.players['p1']
    player.character_id = 'mountain_zhang_he'
    hand = tuple(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    assert hand
    session.engine.start_action(QiaobianAction('qiaobian-' + phase.value, 'p1', phase))
    request = session.engine.pending_request
    assert request.player_id == 'p1'
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    request = session.engine.pending_request
    assert request.eligible_card_ids == hand
    session.engine.submit_decision(Decision(request.request_id, 'p1', hand[0]))
    if phase is Phase.DRAW:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', 'done'))
    assert hand[0] in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert player.marks['skip_' + phase.value] == 1
    restored = restore_session(snapshot_session(session))
    assert restored.state.players['p1'].marks['skip_' + phase.value] == 1


def test_qiaobian_draw_replacement_takes_from_two_distinct_players():
    session = GameSession.new_game(military=True, five_generals=True, seed=3)
    session.state.players['p1'].character_id = 'mountain_zhang_he'
    original = {pid: set(session.state.cards_in(ZoneRef(ZoneType.HAND, pid)))
                for pid in ('p1', 'p2', 'p3')}
    session.engine.start_action(QiaobianAction('qiaobian-take', 'p1', Phase.DRAW))
    for choice in (True, next(iter(original['p1'])), 'p2', 'p3'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert session.engine.pending_request is None
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == len(original['p2']) - 1
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))) == len(original['p3']) - 1
    gained = set(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) - original['p1']
    assert len(gained) == 2
    assert gained <= original['p2'] | original['p3']


def test_qiaobian_decline_has_no_cost_or_skip():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'mountain_zhang_he'
    hand = tuple(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(QiaobianAction('qiaobian-decline', 'p1', Phase.DRAW))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', False))
    assert tuple(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == hand
    assert 'skip_draw' not in session.state.players['p1'].marks


def test_qiaobian_rejects_unskippable_phase():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'mountain_zhang_he'
    session.engine.start_action(QiaobianAction('qiaobian-invalid', 'p1', Phase.PREPARATION))
    assert session.engine.pending_request is None
    assert 'skip_preparation' not in session.state.players['p1'].marks


def test_qiaobian_moves_equipment_to_open_matching_slot():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'mountain_zhang_he'
    card = put(session, 'equipment.weapon.serpent_spear', 'p2',
               ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    cost = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.engine.start_action(QiaobianAction('qiaobian-board', 'p1', Phase.PLAY))
    for choice in (True, cost, card, 'p3'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert card not in session.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p2', EquipmentSlot.WEAPON))
    assert card in session.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p3', EquipmentSlot.WEAPON))
    assert session.state.players['p1'].marks['skip_play'] == 1
