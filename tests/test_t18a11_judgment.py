from dataclasses import replace
import pytest
from test_t17c_first_batch import setup, restore
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
from sanguosha.engine.requests import RequestType
from sanguosha.model.enums import Suit, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType

@pytest.mark.parametrize('zone', [ZoneType.HAND, ZoneType.EQUIPMENT])
def test_guidao_exchanges_old_judgment_into_owners_hand(zone):
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'wind_zhang_jiao'
    material = put(s, 'basic.slash' if zone is ZoneType.HAND else 'equipment.weapon.crossbow',
                   'p2', zone, None if zone is ZoneType.HAND else EquipmentSlot.WEAPON)
    s.state.cards[material] = replace(s.state.cards[material], suit=Suit.SPADE)
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.HEART)
    s.engine.start_action(JudgmentAction('audit-exchange', 'p1', JudgmentPattern(suit=Suit.SPADE)))
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        answer(s, True if r.request_type is RequestType.YES_NO else material)
    assert s.engine.last_result is True
    assert top in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert material in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_retrial_offers_every_holder_in_current_turn_seat_order():
    s = setup('xun_you')
    s.state.current_player_id = 'p3'
    for pid, skill in [('p1', 'guicai'), ('p3', 'guidao'), ('p4', 'guicai')]:
        s.state.players[pid].granted_skills[skill] = 'audit-grant'
        card = put(s, 'basic.slash', pid)
        s.state.cards[card] = replace(s.state.cards[card], suit=Suit.SPADE)
    s.engine.start_action(JudgmentAction('audit-order', 'p2', JudgmentPattern(suit=Suit.HEART)))
    offered = []
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        assert r.request_type is RequestType.YES_NO
        offered.append(r.player_id)
        answer(s, False)
    assert offered == ['p3', 'p4', 'p1']


def test_sequential_retrial_uses_last_card_and_tiandu_obtains_only_final_card():
    s = setup('xun_you')
    s.state.players['p1'].granted_skills['tiandu'] = 'audit-grant'
    s.state.players['p2'].granted_skills['guicai'] = 'audit-grant'
    s.state.players['p3'].granted_skills['guidao'] = 'audit-grant'
    first = put(s, 'basic.slash', 'p2')
    last = put(s, 'basic.slash', 'p3')
    s.state.cards[first] = replace(s.state.cards[first], suit=Suit.HEART)
    s.state.cards[last] = replace(s.state.cards[last], suit=Suit.SPADE)
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.engine.start_action(JudgmentAction('audit-retrial-chain', 'p1', JudgmentPattern(suit=Suit.HEART)))
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        answer(s, True if r.request_type is RequestType.YES_NO else first if r.player_id == 'p2' else last)
    assert s.engine.last_result is False
    assert top in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert first in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))
    assert last in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


@pytest.mark.parametrize('cancelled', [False, True])
def test_lightning_transfer_skips_weimu_and_virtual_duplicate(cancelled):
    from sanguosha.engine.military_tricks import ResolveDelayed
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'forest_jia_xu'
    lightning = put(s, 'delayed.lightning', 'p1', ZoneType.JUDGMENT)
    s.state.cards[lightning] = replace(s.state.cards[lightning], suit=Suit.SPADE)
    duplicate = put(s, 'basic.slash', 'p3', ZoneType.JUDGMENT)
    s.state.metadata['virtual_delayed_cards'] = {duplicate: 'delayed.lightning'}
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.HEART)
    counter = put(s, 'trick.nullification') if cancelled else None
    s.engine.start_action(ResolveDelayed('audit-transfer', 'p1', lightning))
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        answer(s, counter if counter in r.eligible_card_ids else r.timeout_value())
    assert lightning in s.state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p4'))
    assert s.state.metadata['virtual_delayed_cards'][duplicate] == 'delayed.lightning'

@pytest.mark.parametrize('skill', ['guicai', 'guidao', 'jilue'])
def test_qianxi_forbidden_hand_material_is_not_a_retrial_candidate(skill):
    from sanguosha.engine.card_moves import CardMove, CardMoveReason
    s = setup('xun_you')
    actor = 'p2'
    s.state.players[actor].granted_skills[skill] = 'audit-grant'
    s.state.players[actor].marks['ren'] = 1
    moves = s.engine.reaction_provider.__self__
    original = s.state.cards_in(ZoneRef(ZoneType.HAND, actor))
    moves.move(s.state, CardMove('audit-clear-retrial', original, ZoneRef(ZoneType.HAND, actor),
                               ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM, actor))
    card = put(s, 'basic.slash', actor)
    s.state.cards[card] = replace(s.state.cards[card], suit=Suit.SPADE)
    s.state.metadata['qianxi_limits'] = {'p1': {'target': actor, 'color': 'black', 'turn': s.state.turn_number}}
    s.engine.start_action(JudgmentAction('audit-limit-retrial', 'p1', JudgmentPattern(suit=Suit.HEART)))
    assert s.engine.pending_request is None
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, actor))
    assert s.state.players[actor].marks['ren'] == 1


def test_multiple_guicai_holders_can_replace_in_one_judgment():
    s = setup('xun_you')
    materials = {}
    for pid, suit in [('p2', Suit.HEART), ('p3', Suit.SPADE)]:
        s.state.players[pid].granted_skills['guicai'] = 'audit-grant'
        card = put(s, 'basic.slash', pid)
        s.state.cards[card] = replace(s.state.cards[card], suit=suit)
        materials[pid] = card
    s.engine.start_action(JudgmentAction('audit-two-guicai', 'p1', JudgmentPattern(suit=Suit.SPADE)))
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        answer(s, True if r.request_type is RequestType.YES_NO else materials[r.player_id])
    assert s.engine.last_result is True
    assert set(materials.values()) <= set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    event_ids = [event.event_id for event in s.events.events]
    assert len(event_ids) == len(set(event_ids))


def test_qianxi_does_not_prohibit_black_equipment_guidao_material():
    s = setup('xun_you')
    s.state.players['p2'].granted_skills['guidao'] = 'audit-grant'
    card = put(s, 'equipment.weapon.crossbow', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    s.state.cards[card] = replace(s.state.cards[card], suit=Suit.SPADE)
    s.state.metadata['qianxi_limits'] = {'p1': {'target': 'p2', 'color': 'black', 'turn': s.state.turn_number}}
    s.engine.start_action(JudgmentAction('audit-equipment-limit', 'p1', JudgmentPattern(suit=Suit.SPADE)))
    answer(s, True)
    assert card in s.engine.pending_request.eligible_card_ids
    s = restore(s)
    answer(s, card)
    assert s.engine.last_result is True

@pytest.mark.parametrize('rank,hit', [(1, False), (2, True), (9, True), (10, False)])
def test_lightning_spade_rank_boundaries_and_wuyan_prevents_delayed_trick_damage(rank, hit):
    from sanguosha.engine.military_tricks import ResolveDelayed
    s = setup('xun_you')
    s.state.players['p1'].granted_skills['wuyan'] = 'audit-grant'
    card = put(s, 'delayed.lightning', 'p1', ZoneType.JUDGMENT)
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.SPADE, rank=rank)
    hp = s.state.players['p1'].hp
    s.engine.start_action(ResolveDelayed('audit-lightning-wuyan', 'p1', card))
    while s.engine.pending_request:
        s = restore(s)
        answer(s, s.engine.pending_request.timeout_value())
    assert s.state.players['p1'].hp == hp
    destination = ZoneRef(ZoneType.DISCARD_PILE) if hit else ZoneRef(ZoneType.JUDGMENT, 'p2')
    assert card in s.state.cards_in(destination)


def test_lightning_remains_on_table_until_damage_reactions_finish():
    from sanguosha.engine.military_tricks import ResolveDelayed
    s = setup('xun_you')
    s.state.players['p1'].granted_skills['jianxiong'] = 'audit-grant'
    card = put(s, 'delayed.lightning', 'p1', ZoneType.JUDGMENT)
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.SPADE, rank=2)
    s.engine.start_action(ResolveDelayed('audit-lightning-table', 'p1', card))
    offered = False
    while s.engine.pending_request:
        s = restore(s)
        r = s.engine.pending_request
        if r.request_id.endswith(':jianxiong'):
            offered = True
            assert card in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
            answer(s, True)
        else:
            answer(s, r.timeout_value())
    assert offered
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_delayed_card_leaves_judgment_before_retrial_request():
    from sanguosha.engine.military_tricks import ResolveDelayed
    s = setup('xun_you')
    s.state.players['p2'].granted_skills['guicai'] = 'audit-grant'
    card = put(s, 'delayed.indulgence', 'p1', ZoneType.JUDGMENT)
    s.engine.start_action(ResolveDelayed('audit-delayed-table', 'p1', card))
    while s.engine.pending_request and ':guicai:' not in s.engine.pending_request.request_id:
        answer(s, s.engine.pending_request.timeout_value())
    assert s.engine.pending_request is not None
    s = restore(s)
    assert card not in s.state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p1'))
    assert card in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_virtual_delayed_definition_survives_processing_and_reconnect():
    from sanguosha.engine.military_tricks import ResolveDelayed
    s = setup('xun_you')
    s.state.players['p2'].granted_skills['guicai'] = 'audit-grant'
    material = put(s, 'basic.slash', 'p1', ZoneType.JUDGMENT)
    s.state.metadata['virtual_delayed_cards'] = {material: 'delayed.indulgence'}
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.SPADE)
    s.engine.start_action(ResolveDelayed('audit-virtual-delayed', 'p1', material))
    while s.engine.pending_request:
        s = restore(s)
        answer(s, s.engine.pending_request.timeout_value())
    assert s.state.players['p1'].marks['skip_play'] == 1
    assert material in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert material not in s.state.metadata['virtual_delayed_cards']
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_retrial_inactive_current_holder_moves_to_end_of_seat_order():
    s=setup('xun_you');s.state.current_player_id='p3';s.state.current_phase=None
    for pid in ('p1','p3','p4'):
        s.state.players[pid].granted_skills['guicai']='audit'
        put(s,'basic.slash',pid)
    s.engine.start_action(JudgmentAction('audit-inactive-order','p2',JudgmentPattern(suit=Suit.HEART)))
    order=[]
    while s.engine.pending_request:
        s=restore(s);order.append(s.engine.pending_request.player_id);answer(s,False)
    assert order==['p4','p1','p3']


def test_declining_tiandu_does_not_cancel_independent_gain_on_match():
    from sanguosha.model.enums import Color
    s=setup('xun_you');s.state.players['p1'].granted_skills['tiandu']='audit'
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top]=replace(s.state.cards[top],suit=Suit.SPADE)
    s.engine.start_action(JudgmentAction('audit-luoshen-tiandu','p1',JudgmentPattern(color=Color.BLACK),gain_on_match=True))
    s=restore(s);answer(s,'天妒');answer(s,False)
    assert s.engine.last_result is True
    assert top in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
