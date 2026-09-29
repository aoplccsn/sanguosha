"""Skills remain legal across existing judgment, equipment, and response systems."""

from dataclasses import replace

import pytest

from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.events import CardRespondedEvent, VirtualResponseEvent
from sanguosha.engine.military_tricks import ResolveDelayed
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.skills import LijianAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.model.enums import EquipmentSlot, Phase, Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from test_t6_military_basics import put
from test_t6_equipment_chains import clear_hand


def play_state(session):
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)


@pytest.mark.parametrize('defender,prefix,materials', [
    ('zhaoyun', 'longdan', ('basic.slash', 'basic.slash')),
    ('zhenji', 'qingguo', ('basic.peach', 'basic.peach')),
])
def test_wushuang_requires_two_real_virtual_dodge_responses(defender, prefix, materials):
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p1'].character_id = 'lvbu'
    session.state.players['p2'].character_id = defender
    slash = put(session, 'basic.slash', 'p1')
    costs = [put(session, definition, 'p2') for definition in materials]
    if prefix == 'qingguo':
        for cost in costs:
            session.state.cards[cost] = replace(session.state.cards[cost], suit=Suit.SPADE)
    before = session.state.players['p2'].hp
    session.engine.start_action(UseCardAction('wushuang-virtual', 'p1', slash, ('p2',)))
    used = []
    while session.engine.pending_request:
        request = session.engine.pending_request
        if request.request_type is RequestType.RESPOND_WITH_CARD and request.player_id == 'p2':
            choice = next(f'virtual:{prefix}:{cid}' for cid in costs
                          if f'virtual:{prefix}:{cid}' in request.eligible_card_ids and cid not in used)
            used.append(choice.split(':', 2)[2])
        else:
            choice = PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else request.timeout_value()
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert session.state.players['p2'].hp == before
    assert used == costs
    responses = [event for event in session.events.events if isinstance(event, CardRespondedEvent)
                 and event.card_id in costs]
    assert [event.response_number for event in responses] == [1, 2]
    assert [event.response_total for event in responses] == [2, 2]
    assert not session.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_wushuang_numbers_two_physical_dodges_for_vfx():
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p1'].character_id = 'lvbu'
    slash = put(session, 'basic.slash', 'p1')
    dodges = [put(session, 'basic.dodge', 'p2') for _ in range(2)]
    session.engine.start_action(UseCardAction('wushuang-physical', 'p1', slash, ('p2',)))
    while session.engine.pending_request:
        request = session.engine.pending_request
        choice = next((cid for cid in dodges if cid in request.eligible_card_ids), PASS_RESPONSE)
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    responses = [event for event in session.events.events if isinstance(event, CardRespondedEvent)
                 and event.card_id in dodges]
    assert [(event.response_number, event.response_total) for event in responses] == [(1, 2), (2, 2)]


def test_tieqi_red_judgment_prevents_eight_trigrams_dodge():
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p1'].character_id = 'machao'
    slash = put(session, 'basic.slash', 'p1')
    put(session, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.HEART)
    before = session.state.players['p2'].hp
    session.engine.start_action(UseCardAction('tieqi-armor', 'p1', slash, ('p2',)))
    while session.engine.pending_request:
        request = session.engine.pending_request
        choice = True if request.request_type is RequestType.YES_NO else request.timeout_value()
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert session.state.players['p2'].hp == before - 1
    assert not any(isinstance(event, VirtualResponseEvent) and event.player_id == 'p2'
                   for event in session.events.events)


def test_tiandu_collects_eight_trigrams_judgment_before_virtual_dodge():
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p2'].character_id = 'guojia'
    slash = put(session, 'basic.slash', 'p1')
    put(session, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.HEART)
    before = session.state.players['p2'].hp
    session.engine.start_action(UseCardAction('tiandu-armor', 'p1', slash, ('p2',)))
    while session.engine.pending_request:
        request = session.engine.pending_request
        choice = True if request.request_type is RequestType.YES_NO else request.timeout_value()
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert top in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert session.state.players['p2'].hp == before
    assert any(isinstance(event, VirtualResponseEvent) and event.player_id == 'p2'
               for event in session.events.events)


def test_guicai_replaces_lethal_lightning_judgment():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'simayi'
    lightning = put(session, 'delayed.lightning', 'p1', ZoneType.JUDGMENT)
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE, rank=5)
    replacement = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    session.state.cards[replacement] = replace(session.state.cards[replacement], suit=Suit.HEART)
    before = session.state.players['p1'].hp
    session.engine.start_action(ResolveDelayed('guicai-lightning', 'p1', lightning))
    while session.engine.pending_request:
        request = session.engine.pending_request
        choice = (True if request.request_type is RequestType.YES_NO and '鬼才' in request.prompt else
                  replacement if request.request_type is RequestType.CHOOSE_CARD else
                  PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else request.timeout_value())
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert session.state.players['p1'].hp == before
    assert lightning in session.state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p2'))
    assert top in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_guanxing_can_move_safe_card_above_lightning_judgment():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'zhugeliang'
    session.state.current_player_id = 'p1'
    lightning = put(session, 'delayed.lightning', 'p1', ZoneType.JUDGMENT)
    draw = ZoneRef(ZoneType.DRAW_PILE)
    original = session.state.cards_in(draw)
    session.state.cards[original[0]] = replace(session.state.cards[original[0]], suit=Suit.SPADE, rank=5)
    session.state.cards[original[1]] = replace(session.state.cards[original[1]], suit=Suit.HEART)
    before = session.state.players['p1'].hp
    session.engine.start_action(PhaseAction('guanxing-lightning', 'p1', Phase.PREPARATION))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    for cid in (original[1], original[0], original[2], original[3], original[4]):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', f'top:{cid}'))
    assert session.state.cards_in(draw)[0] == original[1]
    session.engine.start_action(ResolveDelayed('guanxing-lightning-resolve', 'p1', lightning))
    while session.engine.pending_request:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD
                                                else request.timeout_value()))
    assert session.state.players['p1'].hp == before
    assert lightning in session.state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p2'))


def test_guose_indulgence_can_be_nullified_at_delayed_resolution():
    from sanguosha.engine.skills import GuoseUse
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p1'].character_id = 'daqiao'
    material = put(session, 'basic.peach', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.DIAMOND)
    counter = put(session, 'trick.nullification', 'p2')
    session.engine.start_action(GuoseUse('guose-counter', 'p1', material))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    assert material in session.state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p2'))
    session.engine.start_action(ResolveDelayed('guose-nullified', 'p2', material))
    while session.engine.pending_request:
        request = session.engine.pending_request
        choice = counter if counter in request.eligible_card_ids else PASS_RESPONSE
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert not session.state.players['p2'].marks.get('skip_play')
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert material not in session.state.metadata['virtual_delayed_cards']


def test_liuli_redirects_one_halberd_target_without_copying_slash():
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p2'].character_id = 'daqiao'
    put(session, 'equipment.weapon.halberd', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    put(session, 'equipment.weapon.kylin_bow', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    clear_hand(session, 'p1')
    slash = put(session, 'basic.slash', 'p1')
    cost = put(session, 'basic.peach', 'p2')
    before = {pid: session.state.players[pid].hp for pid in ('p2', 'p3', 'p4', 'p5')}
    session.engine.start_action(UseCardAction('liuli-halberd', 'p1', slash, ('p2', 'p3', 'p4')))
    while session.engine.pending_request:
        request = session.engine.pending_request
        choice = (True if request.request_type is RequestType.YES_NO and '流离' in request.prompt else
                  cost if request.request_type is RequestType.CHOOSE_CARD else
                  'p5' if request.request_type is RequestType.CHOOSE_PLAYER else
                  PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else request.timeout_value())
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert session.state.players['p2'].hp == before['p2']
    assert session.state.players['p5'].hp == before['p5'] - 1
    assert slash in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert sum(slash in zone.card_ids for zone in session.state.zones.values()) == 1
    session.state.__post_init__()


def test_xiaoji_draws_after_weapon_replacement():
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p1'].character_id = 'sunshangxiang'
    old = put(session, 'equipment.weapon.double_sword', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    new = put(session, 'equipment.weapon.kylin_bow', 'p1')
    before = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(UseCardAction('xiaoji-replace', 'p1', new))
    while session.engine.pending_request:
        request = session.engine.pending_request
        assert request.request_type is RequestType.YES_NO and '枭姬' in request.prompt
        session.engine.submit_decision(Decision(request.request_id, request.player_id, True))
    assert old in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert new in session.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON))
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before - 1 + 2


def test_jijiu_uses_red_card_during_other_players_dying_resolution():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.current_player_id = 'p1'
    session.state.players['p1'].hp = 1
    session.state.players['p2'].character_id = 'huatuo'
    material = put(session, 'basic.slash', 'p2')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.HEART)
    session.engine.start_action(MilitaryDamageAction('jijiu-dying', 'p3', 'p1', 1))
    used = False
    while session.engine.pending_request:
        request = session.engine.pending_request
        virtual = f'virtual:jijiu:{material}'
        choice = virtual if virtual in request.eligible_card_ids else (
            PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else request.timeout_value())
        used |= choice == virtual
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert used
    assert session.state.players['p1'].hp == 1
    assert session.state.players['p1'].is_alive
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_lijian_duel_obeys_lu_bu_wushuang_double_slash():
    session = GameSession.new_game(military=True, five_generals=True)
    play_state(session)
    session.state.players['p1'].character_id = 'diaochan'
    session.state.players['p2'].character_id = 'lvbu'
    session.state.players['p3'].character_id = 'caocao'
    cost = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    slashes = [put(session, 'basic.slash', 'p3') for _ in range(2)]
    before_lubu = session.state.players['p2'].hp
    before_target = session.state.players['p3'].hp
    session.engine.start_action(LijianAction('lijian-wushuang', 'p1'))
    used = []
    while session.engine.pending_request:
        request = session.engine.pending_request
        if request.request_type is RequestType.CHOOSE_CARD:
            choice = cost
        elif request.request_type is RequestType.CHOOSE_PLAYERS:
            choice = ('p2', 'p3')
        elif request.request_type is RequestType.RESPOND_WITH_CARD:
            choice = next((cid for cid in slashes if cid in request.eligible_card_ids and cid not in used), PASS_RESPONSE)
            if choice is not PASS_RESPONSE:
                used.append(choice)
        else:
            choice = request.timeout_value()
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert used == slashes
    assert session.state.players['p3'].hp == before_target
    assert session.state.players['p2'].hp == before_lubu - 1
    assert session.engine.stack.is_empty()
