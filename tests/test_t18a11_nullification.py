"""Independent classic nullification parity and Kanpo material boundaries."""
from dataclasses import replace
import pytest
from test_t17c_first_batch import setup, restore
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.military_tricks import NullificationWindow
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.model.enums import Suit, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType


@pytest.mark.parametrize('count', range(5))
def test_counter_chain_parity_survives_every_response_restore(count):
    s = setup('xun_you')
    cards = tuple(put(s, 'trick.nullification', s.state.seat_order[i % 5]) for i in range(count))
    s.engine.start_action(NullificationWindow('audit-counter', 'p4'))
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        answer(s, next((card for card in cards if card in r.eligible_card_ids), PASS_RESPONSE))
    assert s.engine.last_result is bool(count % 2)
    assert set(cards) <= set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


@pytest.mark.parametrize('definition', ['trick.savage_assault', 'trick.archery_attack'])
def test_one_aoe_target_counter_does_not_cancel_later_targets(definition):
    s = setup('xun_you')
    counter = put(s, 'trick.nullification')
    card = put(s, definition)
    before = {pid: p.hp for pid, p in s.state.players.items()}
    s.engine.start_action(UseCardAction('audit-scope', 'p1', card))
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        value = counter if r.subject_player_id == 'p2' and counter in r.eligible_card_ids else r.timeout_value()
        answer(s, value)
    assert s.state.players['p2'].hp == before['p2']
    assert all(s.state.players[pid].hp == before[pid] - 1 for pid in ('p3', 'p4', 'p5'))


@pytest.mark.parametrize('condition,eligible', [
    ('spade', True), ('club', True), ('heart', False), ('diamond', False),
    ('equipment', False), ('hongyan', False), ('suppressed', False), ('color-ban', False),
])
def test_kanpo_uses_only_allowed_effectively_black_hand(condition, eligible):
    s = setup('xun_you')
    s.state.players['p1'].character_id = 'fire_wolong'
    if condition == 'equipment':
        card = put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    else:
        card = put(s, 'basic.slash')
    suit = {'club': Suit.CLUB, 'heart': Suit.HEART, 'diamond': Suit.DIAMOND}.get(condition, Suit.SPADE)
    s.state.cards[card] = replace(s.state.cards[card], suit=suit)
    if condition == 'hongyan':
        s.state.players['p1'].granted_skills['hongyan'] = 'audit-grant'
    if condition == 'suppressed':
        s.state.players['p1'].disabled_skills.add('kanpo')
    if condition == 'color-ban':
        s.state.metadata['qianxi_limits'] = {'p2': {'target': 'p1', 'color': 'black', 'turn': s.state.turn_number}}
    s.engine.start_action(RespondWithCardAction('audit-kanpo', 'p1', 'trick.nullification', 'incoming'))
    s = restore(s)
    option = 'virtual:kanpo:' + card
    assert (option in s.engine.pending_request.eligible_card_ids) is eligible
    answer(s, option if eligible else PASS_RESPONSE)
    if eligible:
        assert s.engine.last_result.definition_id == 'trick.nullification'
        assert s.engine.last_result.material_ids == (card,)
        assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    else:
        assert s.engine.last_result is None


def test_kanpo_stale_response_rechecks_skill_before_paying_material():
    s = setup('xun_you')
    s.state.players['p1'].granted_skills['kanpo'] = 'audit-grant'
    card = put(s, 'basic.slash')
    s.state.cards[card] = replace(s.state.cards[card], suit=Suit.SPADE)
    s.engine.start_action(RespondWithCardAction('audit-stale-kanpo', 'p1', 'trick.nullification', 'incoming'))
    s.state.players['p1'].disabled_skills.add('kanpo')
    s = restore(s)
    with pytest.raises(InvalidCardUse):
        answer(s, 'virtual:kanpo:' + card)
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
