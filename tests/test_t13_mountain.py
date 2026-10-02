"""Targeted classic Mountain rule tests."""

from dataclasses import replace
import pytest

from sanguosha.engine.mountain import (QiaobianAction, TuntianAction, ZaoxianAction,
                                       JixiUse, FangquanSkipAction, FangquanEndAction, RuoyuAction,
                                       field_zone)
from sanguosha.engine.turn_order import next_scheduled_player, queue_extra_turn
from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.military_basics import MilitaryStrike
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import EquipmentSlot, Phase, Suit
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.usage import PlayUsageState
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


def test_tuntian_nonheart_judgment_enters_authoritative_field():
    session = GameSession.new_game(military=True, five_generals=True, seed=3)
    session.state.players['p1'].character_id = 'mountain_deng_ai'
    draw = ZoneRef(ZoneType.DRAW_PILE)
    top = session.state.cards_in(draw)[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE)
    session.engine.start_action(TuntianAction('tuntian-judge', 'p1'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert top in session.state.cards_in(field_zone('p1'))
    restored = restore_session(snapshot_session(session))
    assert top in restored.state.cards_in(field_zone('p1'))


def test_tuntian_off_turn_card_loss_queues_reaction():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_deng_ai'
    state.current_player_id = 'p2'
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    moves = session.engine.reaction_provider.__self__
    moves.move(state, CardMove('tuntian-loss', (card,), ZoneRef(ZoneType.HAND, 'p1'),
                               ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, 'p2'))
    reaction = moves.next_reaction(state)
    assert isinstance(reaction, TuntianAction)
    assert reaction.player_id == 'p1'


def test_move_reaction_queue_survives_reconnect():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_deng_ai'
    state.players['p1'].granted_skills['lianying'] = 'test'
    state.current_player_id = 'p2'
    hand = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    moves = session.engine.reaction_provider.__self__
    moves.move(state, CardMove('loss-with-two-reactions', hand,
                               ZoneRef(ZoneType.HAND, 'p1'), ZoneRef(ZoneType.DISCARD_PILE),
                               CardMoveReason.DISCARD, 'p2'))
    assert len(moves.reactions) == 2
    restored = restore_session(snapshot_session(session))
    reactions = restored.engine.reaction_provider.__self__.reactions
    assert len(reactions) == 2
    assert isinstance(reactions[1], TuntianAction)


def test_zaoxian_awakens_once_and_grants_jixi():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_deng_ai'
    moves = session.engine.reaction_provider.__self__
    field_cards = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:3]
    moves.move(state, CardMove('setup-field', field_cards, ZoneRef(ZoneType.DRAW_PILE),
                               field_zone('p1'), CardMoveReason.SYSTEM))
    original_max = player.max_hp
    session.engine.start_action(ZaoxianAction('zaoxian', 'p1'))
    assert player.max_hp == original_max - 1
    assert player.marks['awakened_zaoxian'] == 1
    assert player.granted_skills['jixi'] == 'zaoxian'
    assert session.skills.has(state, 'p1', 'jixi')
    session.engine.start_action(ZaoxianAction('zaoxian-again', 'p1'))
    assert player.max_hp == original_max - 1
    restored = restore_session(snapshot_session(session))
    assert restored.skills.has(restored.state, 'p1', 'jixi')
    assert len(restored.state.cards_in(field_zone('p1'))) == 3


def test_tuntian_field_reduces_outgoing_distance():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_deng_ai'
    distance = DistanceSystem(session.definitions)
    before = distance.distance_between(state, 'p1', 'p3')
    card = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.engine.reaction_provider.__self__.move(state, CardMove(
        'setup-one-field', (card,), ZoneRef(ZoneType.DRAW_PILE), field_zone('p1'),
        CardMoveReason.SYSTEM))
    assert distance.distance_between(state, 'p1', 'p3') == max(1, before - 1)
    assert distance.distance_between(state, 'p3', 'p1') == before


def test_jixi_uses_existing_snatch_and_consumes_field_card():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_deng_ai'
    player.granted_skills['jixi'] = 'zaoxian'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    field_card = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.engine.reaction_provider.__self__.move(state, CardMove(
        'setup-jixi-field', (field_card,), ZoneRef(ZoneType.DRAW_PILE),
        field_zone('p1'), CardMoveReason.SYSTEM))
    session.engine.start_action(JixiUse('jixi-use', 'p1', field_card))
    for _ in range(20):
        request = session.engine.pending_request
        if request is None:
            break
        if request.request_id == 'jixi-use:target':
            choice = 'p2'
        elif request.eligible_card_ids and request.player_id == 'p1':
            choice = request.eligible_card_ids[0]
        else:
            choice = request.timeout_value()
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert session.engine.pending_request is None
    assert field_card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert field_card not in state.cards_in(field_zone('p1'))


def test_xiangle_prevents_slash_when_attacker_declines_basic_cost():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p2'].character_id = 'mountain_liushan'
    slash = put(session, 'basic.slash', 'p1')
    hp = state.players['p2'].hp
    session.engine.start_action(MilitaryStrike('xiangle-slash', 'p1', 'p2', slash,
                                               'basic.dodge'))
    request = session.engine.pending_request
    assert 'decline' in request.choices
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'decline'))
    assert state.players['p2'].hp == hp


def test_xiangle_consumes_basic_cost_then_slash_continues():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p2'].character_id = 'mountain_liushan'
    slash = put(session, 'basic.slash', 'p1')
    cost = put(session, 'basic.peach', 'p1')
    session.engine.start_action(MilitaryStrike('xiangle-paid', 'p1', 'p2', slash,
                                               'basic.dodge'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', cost))
    assert cost in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert session.engine.stack.is_empty()


def test_fangquan_skip_cost_and_extra_turn_survive_reconnect():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_liushan'
    hand = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    session.engine.start_action(FangquanSkipAction('fangquan-skip', 'p1'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert state.players['p1'].marks['skip_play'] == 1
    assert state.players['p1'].marks['fangquan_pending'] == 1
    session.engine.start_action(FangquanEndAction('fangquan-end', 'p1'))
    for choice in (True, hand[0], 'p3'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert hand[0] in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert state.extra_turn_queue == ['p3']
    restored = restore_session(snapshot_session(session))
    assert next_scheduled_player(restored.state) == 'p3'
    assert restored.state.extra_turn_queue == []


def test_extra_turn_queue_skips_dead_recipient_and_preserves_order():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.current_player_id = 'p1'
    queue_extra_turn(state, 'p2')
    queue_extra_turn(state, 'p3')
    from sanguosha.model.enums import PlayerStatus
    state.players['p2'].status = PlayerStatus.DEAD
    assert next_scheduled_player(state) == 'p3'
    state.current_player_id = 'p3'
    assert next_scheduled_player(state) == 'p3'


def test_nested_extra_turns_resume_after_original_player():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.current_player_id = 'p1'
    queue_extra_turn(state, 'p3')
    assert next_scheduled_player(state) == 'p3'
    state.current_player_id = 'p3'
    queue_extra_turn(state, 'p4')
    assert next_scheduled_player(state) == 'p4'
    state.current_player_id = 'p4'
    assert next_scheduled_player(state) == 'p2'


def test_ruoyu_lord_awakes_once_and_reuses_jijiang():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    lord_id = next(pid for pid, player in state.players.items()
                   if player.identity.value == 'lord')
    lord = state.players[lord_id]
    lord.character_id = 'mountain_liushan'
    lord.hp = 1
    original_max = lord.max_hp
    session.engine.start_action(RuoyuAction('ruoyu-awake', lord_id))
    assert lord.max_hp == original_max + 1
    assert lord.hp == 2
    assert lord.marks['awakened_ruoyu'] == 1
    assert session.skills.has(state, lord_id, 'jijiang')
    session.engine.start_action(RuoyuAction('ruoyu-again', lord_id))
    assert lord.max_hp == original_max + 1
    restored = restore_session(snapshot_session(session))
    assert restored.skills.has(restored.state, lord_id, 'jijiang')
