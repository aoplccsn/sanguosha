"""Human request handling, equipment copy and distance regressions."""
from sanguosha.content.cards.classic_military import WEAPONS, ARMORS, HORSES
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_tricks import NullificationWindow
from sanguosha.engine.phases import PhaseAction, END_PLAY_PHASE
from sanguosha.engine.requests import Decision, PASS_RESPONSE, PendingRequest, RequestType
from sanguosha.model.enums import EquipmentSlot, Phase, PlayerStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.projection import project_for_human, CardView
from sanguosha.ui.card_widget import CardWidget
from sanguosha.ui.main_window import MainWindow, HUMAN_DECISION_TIMEOUT_MS
from test_t6_military_basics import game, put
from test_t6_distance import make_state


def request(kind, **kwargs):
    return PendingRequest('timeout', 'p1', kind, 'test', 'action', 'frame', **kwargs)


def test_timeout_fallbacks_are_valid_for_every_existing_shape():
    examples = (
        request(RequestType.RESPOND_WITH_CARD, allow_pass=True),
        request(RequestType.YES_NO),
        request(RequestType.CHOOSE_OPTION, choices=('use:x', 'end_play_phase')),
        request(RequestType.CHOOSE_PLAYER, allowed_player_ids=('p2', 'p3')),
        request(RequestType.CHOOSE_PLAYERS, allowed_player_ids=('p2', 'p3'), min_count=1, max_count=2),
        request(RequestType.CHOOSE_CARD, eligible_card_ids=('a', 'b')),
        request(RequestType.CHOOSE_CARDS, eligible_card_ids=('a', 'b', 'c'), min_count=2, max_count=2),
    )
    for item in examples:
        item.validate(item.timeout_value())
    assert examples[0].timeout_value() is PASS_RESPONSE
    assert examples[2].timeout_value() == END_PLAY_PHASE
    assert examples[3].timeout_value() == 'p2'
    assert examples[6].timeout_value() == ('a', 'b')


def test_empty_nullification_is_passed_without_human_prompt():
    session = game()
    session.engine.start_action(NullificationWindow('empty-window', 'p2'))
    window = MainWindow()
    window.session = session
    window._render()
    assert not (session.engine.pending_request and session.engine.pending_request.player_id == 'p1')
    assert all(button.text() != '本次均不响应' for button in window.decision.buttons)
    window.close()


def test_nullification_decline_is_scoped_to_one_window():
    session = game()
    first = put(session, 'trick.nullification', 'p1')
    second = put(session, 'trick.nullification', 'p2')
    session.engine.start_action(NullificationWindow('first-window', 'p3'))
    assert first in session.engine.pending_request.eligible_card_ids
    window = MainWindow()
    window.session = session
    window._render()
    assert any(button.text() == '本次均不响应' for button in window.decision.buttons)
    window._submit_value('ui.decline_nullification')
    assert 'first-window' in session.declined_nullification_windows
    while session.engine.pending_request:
        pending = session.engine.pending_request
        choice = second if second in pending.eligible_card_ids else PASS_RESPONSE
        session.engine.submit_decision(Decision(pending.request_id, pending.player_id, choice))
        session.pass_unavailable_nullification()
    session.clear_finished_nullification_windows()
    assert not session.declined_nullification_windows
    session.engine.start_action(NullificationWindow('next-window', 'p3'))
    assert first in session.engine.pending_request.eligible_card_ids
    assert not session.pass_unavailable_nullification()
    window.close()


def test_timeout_end_play_goes_through_pending_decision():
    session = game()
    session.engine.start_action(PhaseAction('timed-play', 'p1', Phase.PLAY))
    pending = session.engine.pending_request
    assert pending.timeout_value() == END_PLAY_PHASE
    session.submit_human(Decision(pending.request_id, pending.player_id, pending.timeout_value()))
    assert session.engine.pending_request is None


def test_player_highlights_timer_and_close():
    session = game()
    put(session, 'trick.nullification', 'p1')
    session.engine.start_action(NullificationWindow('visible-window', 'p3'))
    window = MainWindow()
    window.session = session
    window._render()
    active = window.table.panels['p1']
    assert active.view.active and active.turn_glow >= 0
    assert active.decision_progress == 1
    assert window._decision_timer.isActive()
    window._decision_remaining_ms = 100
    window._decision_countdown()
    assert session.engine.pending_request is None or session.engine.pending_request.player_id != 'p1'
    window.close()
    assert not window._decision_timer.isActive()


def test_responder_highlight_independent_of_turn():
    session = game()
    put(session, 'trick.nullification', 'p2')
    session.engine.start_action(NullificationWindow('responder-window', 'p3'))
    window = MainWindow()
    window.session = session
    window._render()
    assert window.table.panels['p1'].view.active
    assert window.table.panels['p2'].pending_responder
    window.close()


def test_every_equipment_has_rule_backed_display_details():
    session = game()
    for key, _, expected in WEAPONS:
        definition = session.definitions.get(f'equipment.weapon.{key}')
        assert definition.attack_range == expected
        assert definition.metadata['effect_summary']
    for key, _ in ARMORS:
        assert session.definitions.get(f'equipment.armor.{key}').metadata['effect_summary']
    for key, _, _ in HORSES:
        assert session.definitions.get(f'equipment.horse.{key}').metadata['effect_summary']
    for definition_id, phrase in (
        ('equipment.weapon.kylin_bow', '攻击范围：5'),
        ('equipment.armor.eight_trigrams', '判定'),
        ('equipment.horse.chitu', '-1'),
        ('equipment.horse.jueying', '+1'),
    ):
        card = put(session, definition_id)
        view = project_for_human(session.state, session.definitions, session.human_id, session.character_names)
        card_view = next(c for c in view.hand if c.card_id == card)
        assert phrase in card_view.details
        assert phrase in CardWidget(card_view).toolTip()
    assert CardWidget(CardView('missing', '未知', '♠', 'A')).toolTip()


def test_horses_are_directional_and_removed_modifiers_disappear():
    state, distance = make_state(offensive=True, defensive=True, weapon_range=2)
    p1, p2, p3, *_ = state.seat_order
    assert distance.base_distance(state, p1, p3) == 2
    assert distance.distance_between(state, p1, p3) == 2
    assert distance.distance_between(state, p3, p1) == 2
    state.zones[ZoneRef(ZoneType.EQUIPMENT, p1, EquipmentSlot.OFFENSIVE_HORSE)].card_ids.clear()
    assert distance.distance_between(state, p1, p3) == 3
    state.zones[ZoneRef(ZoneType.EQUIPMENT, p3, EquipmentSlot.DEFENSIVE_HORSE)].card_ids.clear()
    assert distance.distance_between(state, p1, p3) == 2
    assert distance.attack_range(state, p1) == 2
    state.zones[ZoneRef(ZoneType.EQUIPMENT, p1, EquipmentSlot.WEAPON)].card_ids.clear()
    assert distance.attack_range(state, p1) == 1


def test_dead_seats_and_horse_directionality():
    state, distance = make_state(offensive=True, defensive=True)
    p1, p2, p3, p4, p5 = state.seat_order
    assert distance.distance_between(state, p3, p1) == 2
    assert distance.distance_between(state, p2, p3) == 2
    state.players[p2].status = PlayerStatus.DEAD
    assert distance.base_distance(state, p1, p3) == 1
    assert distance.distance_between(state, p1, p3) == 1
    state.players[p4].status = PlayerStatus.DEAD
    assert distance.base_distance(state, p3, p5) == 1


def test_snatch_and_supply_shortage_use_distance_after_horse_change():
    session = game()
    snatch = put(session, 'trick.snatch')
    supply = put(session, 'delayed.supply_shortage')
    # p3 is two seats away until p1 equips an offensive horse.
    for card in (snatch, supply):
        action = UseCardAction('preview', 'p1', card)
        rule = session.engine.registry.handler_for(action).validator.rule_for(session.state, card)
        assert 'p3' not in rule.target_candidates(session.state, 'p1')
    horse = put(session, 'equipment.horse.chitu', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.OFFENSIVE_HORSE)
    for card in (snatch, supply):
        rule = session.engine.registry.handler_for(UseCardAction('preview', 'p1', card)).validator.rule_for(session.state, card)
        assert 'p3' in rule.target_candidates(session.state, 'p1')
    session.state.zones[ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.OFFENSIVE_HORSE)].card_ids.clear()
    for card in (snatch, supply):
        rule = session.engine.registry.handler_for(UseCardAction('preview', 'p1', card)).validator.rule_for(session.state, card)
        assert 'p3' not in rule.target_candidates(session.state, 'p1')


def test_gui_target_highlight_tracks_immediate_distance_change():
    session = game()
    card = put(session, 'basic.slash')
    session.engine.start_action(PhaseAction('play-distance', 'p1', Phase.PLAY))
    window = MainWindow()
    window.session = session
    window._render()
    window._card_clicked(card)
    assert 'p3' not in window.interaction.legal_targets
    window._submit_value('ui.cancel')
    put(session, 'equipment.horse.chitu', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.OFFENSIVE_HORSE)
    window._card_clicked(card)
    assert 'p3' in window.interaction.legal_targets
    window.close()
