"""Rule-risk cases for the four advanced mainland mobile boundary generals."""
from dataclasses import replace

import pytest

from sanguosha.engine.boundary_advanced import (
    BoundaryAdvancedAction, BoundaryAdvancedHandler, clear_turn, commit_response,
    event_reactions, jianying_materials, play_options, response_options,
)
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.deck import DrawCardsAction
from sanguosha.engine.events import CardMovedEvent, CardUsedEvent, DamageDealtEvent, Event, PhaseEndedEvent, PhaseStartedEvent
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.recovery import RecoverAction
from sanguosha.engine.yj2012 import power_zone
from sanguosha.model.enums import EquipmentSlot, Phase, Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from test_t6_military_basics import put


def game(general):
    s = GameSession.new_game(military=True, five_generals=True)
    for p in s.state.players.values():
        p.character_id = 'sunquan'
        p.hp = p.max_hp = 4
    s.state.players['p1'].character_id = 'boundary_' + general
    s.state.players['p1'].hp = s.state.players['p1'].max_hp = 3 if general in ('li_ru', 'ju_shou') else 4
    s.state.current_player_id = 'p1'
    s.state.current_phase = Phase.PLAY
    s.state.turn_number = 1
    s.state.play_usage = PlayUsageState('p1', 1)
    for pid in s.state.seat_order:
        cards = s.state.cards_in(ZoneRef(ZoneType.HAND, pid))
        if cards:
            CardMoveService(s.events).move(s.state, CardMove('clear:' + pid, cards,
                ZoneRef(ZoneType.HAND, pid), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM))
    s.state.metadata['reaction_event_cursor'] = len(s.events.events)
    return s


def answer(s, value):
    r = s.engine.pending_request
    assert r is not None
    s.engine.submit_decision(Decision(r.request_id, r.player_id, value))


def restore(s):
    return restore_session(snapshot_session(s))


def drain(s):
    for _ in range(100):
        r = s.engine.pending_request
        if r is None:
            assert s.engine.stack.is_empty()
            s.state.__post_init__()
            return
        answer(s, r.timeout_value())
    raise AssertionError('advanced skill did not terminate')


def colored(s, definition, owner='p1', suit=Suit.CLUB, rank=6, zone=ZoneType.HAND, slot=None):
    cid = put(s, definition, owner, zone, slot)
    s.state.cards[cid] = replace(s.state.cards[cid], suit=suit, rank=rank)
    return cid


def test_quanji_multidamage_piles_and_self_waking_gain_survive_restore():
    s = game('zhong_hui')
    s.engine.start_action(MilitaryDamageAction('two', 'p2', 'p1', 2))
    for _ in range(2):
        assert '权计' in s.engine.pending_request.prompt
        answer(s, True)
        s = restore(s)
        card = s.engine.pending_request.eligible_card_ids[0]
        answer(s, card)
    assert len(s.state.cards_in(power_zone('p1'))) == 2
    c = put(s, 'basic.dodge')
    CardMoveService(s.events).move(s.state, CardMove('third-power', (c,), ZoneRef(ZoneType.HAND, 'p1'), power_zone('p1'), CardMoveReason.SYSTEM))
    s.state.current_phase = Phase.PREPARATION
    s.engine.start_action(BoundaryAdvancedAction('wake', 'p1', 'jie_zili'))
    s = restore(s)
    answer(s, 'recover')
    assert s.state.players['p1'].hp == 3
    assert s.state.players['p1'].max_hp == 3
    assert s.state.players['p1'].marks['jie_zili_awakened'] == 1
    assert s.skills.has(s.state, 'p1', 'jie_paiyi')
    assert s.state.players['p1'].granted_skills['jie_paiyi'] == 'jie_zili'
    s = restore(s)
    s.engine.start_action(BoundaryAdvancedAction('wake-again', 'p1', 'jie_zili'))
    assert s.engine.pending_request is None
    assert s.state.players['p1'].max_hp == 3
    s.state.current_phase = Phase.PLAY
    s.state.play_usage = PlayUsageState('p1', 1)
    s.engine.start_action(BoundaryAdvancedAction('paiyi', 'p1', 'jie_paiyi'))
    answer(s, s.engine.pending_request.eligible_card_ids[0])
    answer(s, 'p2')
    assert s.state.players['p2'].hp == 3
    assert len(s.state.cards_in(power_zone('p1'))) == 2
    assert s.state.play_usage.count('skill.jie_paiyi') == 1
    with pytest.raises(InvalidCardUse):
        s.engine.start_action(BoundaryAdvancedAction('paiyi-again', 'p1', 'jie_paiyi'))


def test_quanji_phase_end_requires_hand_above_hp_and_is_optional():
    s = game('zhong_hui')
    s.state.players['p1'].hp = 1
    put(s, 'basic.dodge')
    e = PhaseEndedEvent('end-play', 'p1', Phase.PLAY)
    assert not event_reactions(s.state, e, s.skills)
    put(s, 'basic.peach')
    actions = event_reactions(s.state, e, s.skills)
    assert len(actions) == 1 and actions[0].skill == 'jie_quanji'
    s.state.metadata['reaction_event_cursor'] = len(s.events.events)
    s.engine.start_action(actions[0])
    answer(s, False)
    assert not s.state.cards_in(power_zone('p1'))


@pytest.mark.parametrize('branch', ['give_trick', 'discard_nontricks'])
def test_mieji_black_top_cost_gives_trick_or_discards_each_nontrick_separately(branch):
    s = game('li_ru')
    cost = colored(s, 'delayed.indulgence')
    gift = colored(s, 'trick.duel', 'p2')
    basic = put(s, 'basic.dodge', 'p2')
    gear = put(s, 'equipment.armor.vine', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    s.engine.start_action(BoundaryAdvancedAction('mieji', 'p1', 'jie_mieji'))
    answer(s, cost)
    answer(s, 'p2')
    s = restore(s)
    assert s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0] == cost
    assert s.engine.pending_request.player_id == 'p2'
    answer(s, branch)
    if branch == 'give_trick':
        answer(s, gift)
        assert gift in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
        assert gift not in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    else:
        assert gift not in s.engine.pending_request.eligible_card_ids
        answer(s, basic)
        s = restore(s)
        answer(s, gear)
        events = [e for e in s.events.events if isinstance(e, CardMovedEvent)
                  and e.related_action_id == 'mieji' and e.reason == 'discard']
        assert [e.card_ids for e in events] == [(basic,), (gear,)]
    assert s.engine.pending_request is None
    assert s.state.play_usage.count('skill.jie_mieji') == 1


def test_mieji_can_target_equipment_only_and_discard_shortfall():
    s = game('li_ru')
    cost = colored(s, 'trick.duel')
    gear = put(s, 'equipment.armor.vine', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    s.engine.start_action(BoundaryAdvancedAction('only-gear', 'p1', 'jie_mieji'))
    answer(s, cost)
    assert 'p2' in s.engine.pending_request.allowed_player_ids
    answer(s, 'p2')
    assert s.engine.pending_request.choices == ('discard_nontricks',)
    answer(s, 'discard_nontricks')
    answer(s, gear)
    assert s.engine.pending_request is None
    assert gear in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_fencheng_seat_order_uses_actual_payment_then_resets_after_fire_damage():
    s = game('li_ru')
    cards = tuple(put(s, 'basic.dodge', 'p2') for _ in range(2))
    last = put(s, 'basic.dodge', 'p4')
    s.engine.start_action(BoundaryAdvancedAction('fire', 'p1', 'jie_fencheng'))
    assert s.engine.pending_request.player_id == 'p2'
    answer(s, cards)
    # p3 has no cards and takes two fire damage. p4 follows a zero payment,
    # hence needs one card rather than the previous three-card threshold.
    assert s.state.players['p3'].hp == 2
    assert s.engine.pending_request.player_id == 'p4'
    assert s.engine.pending_request.minimum_nonempty_count == 1
    s = restore(s)
    answer(s, (last,))
    drain(s)
    assert s.state.players['p1'].marks['jie_fencheng_used'] == 1
    hits = [e for e in s.events.events if isinstance(e, DamageDealtEvent) and e.event_id.startswith('fire:')]
    assert [e.target_id for e in hits] == ['p3', 'p5']
    with pytest.raises(InvalidCardUse):
        s.engine.start_action(BoundaryAdvancedAction('fire-again', 'p1', 'jie_fencheng'))


def test_juece_uses_real_loss_including_private_removal_with_nonempty_hand():
    s = game('li_ru')
    kept = put(s, 'basic.dodge', 'p2')
    removed = put(s, 'basic.peach', 'p2')
    s.state.metadata['reaction_event_cursor'] = len(s.events.events)
    CardMoveService(s.events).move(s.state, CardMove('pojun-remove', (removed,), ZoneRef(ZoneType.HAND, 'p2'),
                         ZoneRef(ZoneType.SPECIAL, 'p2', special_key='committed:pojun:test'), CardMoveReason.SYSTEM, 'p1', 'pojun'))
    event_reactions(s.state, s.events.events[-1], s.skills)
    s.state.metadata['reaction_event_cursor'] = len(s.events.events)
    actions = event_reactions(s.state, PhaseStartedEvent('finish', 'p1', Phase.FINISH), s.skills)
    s.state.current_phase = Phase.FINISH
    s.engine.start_action(actions[0])
    answer(s, True)
    assert s.engine.pending_request.allowed_player_ids == ('p2',)
    answer(s, 'p2')
    assert s.state.players['p2'].hp == 3
    assert kept in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    clear_turn(s.state)
    assert not s.state.metadata.get('jie_juece_lost')


def test_jianying_compares_suit_or_rank_uses_inherited_suit_and_resets_each_phase():
    s = game('ju_shou')
    first = colored(s, 'basic.wine', suit=Suit.HEART, rank=4)
    same_rank = colored(s, 'trick.ex_nihilo', suit=Suit.CLUB, rank=4)
    material = colored(s, 'basic.dodge', suit=Suit.SPADE, rank=9)
    s.engine.start_action(UseCardAction('first', 'p1', first))
    assert s.engine.pending_request is None
    s.engine.start_action(UseCardAction('same-rank', 'p1', same_rank))
    assert '渐营' in s.engine.pending_request.prompt
    answer(s, True)
    drain(s)
    s = restore(s)
    s.state.players['p1'].hp = 2
    s.engine.start_action(BoundaryAdvancedAction('convert', 'p1', 'jie_jianying'))
    answer(s, 'basic.peach')
    answer(s, material)
    assert '渐营' in s.engine.pending_request.prompt
    s = restore(s)
    answer(s, True)
    assert s.state.players['p1'].hp == 3
    event = next(e for e in s.events.events if isinstance(e, CardUsedEvent) and e.event_id == 'convert:used')
    assert event.virtual_card.suit is Suit.CLUB
    assert s.state.cards[material].suit is Suit.SPADE
    assert s.state.play_usage.count('skill.jie_jianying') == 1
    assert 'skill:jie_jianying' not in play_options(s.state, 'p1', s.skills, s.definitions)
    event_reactions(s.state, PhaseStartedEvent('extra-play', 'p1', Phase.PLAY), s.skills)
    s.state.play_usage = PlayUsageState('p1', 1)
    assert not s.state.metadata['jie_jianying_previous'].get('p1')
    assert jianying_materials(s.state, 'p1', s.skills)


def test_jianying_color_limit_uses_inherited_suit_and_paid_weapon_range_preview():
    s = game('ju_shou')
    card = colored(s, 'basic.dodge', suit=Suit.SPADE)
    s.state.metadata['jie_jianying_previous'] = {'p1': {'suit': 'heart', 'rank': 8}}
    s.state.metadata['qianxi_limits'] = {'p2': {'target': 'p1', 'color': 'black', 'turn': 1}}
    assert card in jianying_materials(s.state, 'p1', s.skills)
    s.state.metadata['qianxi_limits']['p2']['color'] = 'red'
    assert card not in jianying_materials(s.state, 'p1', s.skills)
    s.state.metadata.pop('qianxi_limits')
    weapon = put(s, 'equipment.weapon.serpent_spear', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    handler = s.engine.registry.handler_for(BoundaryAdvancedAction('probe', 'p1', 'jie_jianying'))
    assert 'p3' in handler.jianying_targets(s.state, 'p1', card)
    assert 'p3' not in handler.jianying_targets(s.state, 'p1', weapon)


def test_jianying_dying_peach_uses_same_authority_and_cannot_plain_respond_slash():
    s = game('ju_shou')
    material = colored(s, 'basic.dodge')
    s.state.players['p1'].hp = 0
    action = RespondWithCardAction('save', 'p1', 'basic.peach', 'dying', subject_player_id='p1')
    assert response_options(s.state, action, s.skills) == ('virtual:jie_jianying:' + material,)
    assert not response_options(s.state, replace(action, required_definition_id='basic.slash'), s.skills)
    assert response_options(s.state, replace(action, required_definition_id='basic.slash', use_card=True), s.skills)
    s.engine.start_action(action)
    assert 'virtual:jie_jianying:' + material in s.engine.pending_request.eligible_card_ids
    s = restore(s)
    answer(s, 'virtual:jie_jianying:' + material)
    assert s.engine.last_result.skill_id == 'jie_jianying'
    assert material in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert s.state.play_usage.count('skill.jie_jianying') == 1


def test_shibei_multidamage_counts_one_event_and_later_loss_is_not_damage():
    s = game('ju_shou')
    s.engine.start_action(MilitaryDamageAction('first-hit', 'p2', 'p1', 2))
    assert s.state.players['p1'].hp == 2
    assert s.state.metadata['jie_shibei_counts']['p1'] == 1
    s.engine.start_action(RecoverAction('between-hits', 'p1', 'p1', 1))
    s.engine.start_action(MilitaryDamageAction('second-hit', 'p2', 'p1', 1))
    drain(s)
    losses = [e for e in s.events.events if isinstance(e, Event) and e.event_type == 'hp_lost']
    assert len(losses) == 1
    assert s.state.metadata['jie_shibei_counts']['p1'] == 2
    clear_turn(s.state)
    assert not s.state.metadata.get('jie_shibei_counts')


@pytest.mark.parametrize('pay', [False, True])
def test_qingxi_all_damage_once_per_turn_and_exact_hand_cost_reconnect(pay):
    s = game('cao_xiu')
    cards = tuple(put(s, 'basic.dodge', 'p2') for _ in range(3))
    s.engine.start_action(MilitaryDamageAction('qingxi', 'p1', 'p2', 1))
    assert '倾袭' in s.engine.pending_request.prompt
    answer(s, True)
    assert s.engine.pending_request.player_id == 'p2'
    s = restore(s)
    answer(s, cards if pay else ())
    assert s.state.players['p2'].hp == (3 if pay else 2)
    assert s.state.players['p1'].marks['jie_qingxi_turn'] == 1
    s.engine.start_action(MilitaryDamageAction('same-turn', 'p1', 'p3', 1))
    assert s.engine.pending_request is None
    assert s.state.players['p3'].hp == 3
    clear_turn(s.state)
    s.state.turn_number = 2
    s.engine.start_action(MilitaryDamageAction('next-turn', 'p1', 'p3', 1))
    assert '倾袭' in s.engine.pending_request.prompt
    answer(s, False)
    assert s.state.players['p3'].hp == 2
