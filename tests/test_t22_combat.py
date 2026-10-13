from dataclasses import replace

import pytest

from sanguosha.engine.boundary_combat import (
    BoundaryCombatAction, POJUN_PREFIX, clear_turn, damage_bonus,
    event_reactions, note_damage, register, slash_ignores_distance,
)
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.death import DeathAction
from sanguosha.engine.deck import DrawCardsAction
from sanguosha.engine.phases import END_PLAY_PHASE
from sanguosha.engine.turns import TurnAction
from sanguosha.engine.events import CardMovedEvent, CardUsedEvent, PhaseEndedEvent, TurnStartedEvent
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.model.enums import EquipmentSlot, Identity, Phase, Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.projection import project_for_human
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from test_t6_military_basics import put


def game(general='boundary_xu_sheng'):
    session = GameSession.new_game(military=True, five_generals=True)
    for player in session.state.players.values():
        player.character_id = 'sunquan'
    session.state.players['p1'].character_id = general
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    return session


def answer(session, value):
    request = session.engine.pending_request
    assert request is not None
    session.engine.submit_decision(Decision(request.request_id, request.player_id, value))


def drain(session):
    for _ in range(80):
        request = session.engine.pending_request
        if request is None:
            assert session.engine.stack.is_empty()
            session.state.__post_init__()
            return
        answer(session, request.timeout_value())
    raise AssertionError('boundary combat resolution did not terminate')


def empty_hand(session, player_id):
    ref = ZoneRef(ZoneType.HAND, player_id)
    cards = session.state.cards_in(ref)
    if cards:
        CardMoveService(session.events).move(session.state, CardMove(
            'test-empty:' + player_id, cards, ref, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM))
    session.state.metadata['reaction_event_cursor'] = len(session.events.events)


def test_pojun_repeated_mixed_zone_removal_is_private_restorable_and_returns_once():
    s = game()
    a = put(s, 'basic.dodge', 'p2')
    b = put(s, 'basic.peach', 'p2')
    armor = put(s, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    before = len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    s.engine.start_action(BoundaryCombatAction('pojun-a', 'p1', 'jie_pojun', 'p2'))
    answer(s, True)
    assert s.engine.pending_request.subject_player_id == 'p2'
    assert s.engine.pending_request.max_count == s.state.players['p2'].hp
    s = restore_session(snapshot_session(s))
    answer(s, (a, armor))
    s.engine.start_action(BoundaryCombatAction('pojun-b', 'p1', 'jie_pojun', 'p2'))
    answer(s, True)
    answer(s, (b,))
    pile = next(ref for ref in s.state.zones if ref.zone_type is ZoneType.SPECIAL and ref.special_key.startswith(POJUN_PREFIX))
    assert s.state.cards_in(pile) == (a, armor, b)
    public = project_for_human(s.state, s.definitions, 'p1', s.character_names)
    views = next(player for player in public.players if player.player_id == 'p2').special_piles[pile.special_key]
    assert views[0].card_id.startswith('hidden:') and views[2].card_id.startswith('hidden:')
    assert views[1].card_id == armor
    clear_turn(s.state, s.engine.reaction_provider.__self__, 'p1', 'return')
    assert not s.state.cards_in(pile)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == before + 1
    clear_turn(s.state, s.engine.reaction_provider.__self__, 'p1', 'return-again')
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == before + 1
    s.state.__post_init__()


def test_pojun_damage_checks_hand_and_equipment_separately_and_only_slash():
    s = game()
    empty_hand(s, 'p2')
    slash = MilitaryDamageAction('damage', 'p1', 'p2', 1, card_kind='slash')
    assert damage_bonus(s.state, slash, s.skills) == 1
    put(s, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    assert damage_bonus(s.state, slash, s.skills) == 0
    put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    assert damage_bonus(s.state, slash, s.skills) == 1
    assert damage_bonus(s.state, replace(slash, card_kind='duel'), s.skills) == 0
    assert damage_bonus(s.state, replace(slash, propagated=True), s.skills) == 0


def test_pojun_target_death_discards_removed_cards_without_later_duplication():
    s = game()
    selected = put(s, 'basic.dodge', 'p2')
    s.engine.start_action(BoundaryCombatAction('remove', 'p1', 'jie_pojun', 'p2'))
    answer(s, True)
    answer(s, (selected,))
    s.engine.start_action(DeathAction('death', 'p2', None))
    drain(s)
    assert selected in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    clear_turn(s.state, s.engine.reaction_provider.__self__, 'p1', 'return')
    assert sum(zone.card_ids.count(selected) for zone in s.state.zones.values()) == 1
    assert selected not in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))


def test_xuanfeng_equipment_exchange_has_one_batch_trigger_and_no_duplicate_raw_trigger():
    s = game('boundary_ling_tong')
    cid = put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    ref = ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON)
    raw = CardMovedEvent('exchange', (cid,), ref, ZoneRef(ZoneType.EQUIPMENT, 'p2', EquipmentSlot.WEAPON),
                         'system', 'p1', 'equipment-exchange:test')
    assert not event_reactions(s.state, raw, s.skills, s.events, s.definitions)
    from sanguosha.engine.events import Event
    batch = Event('batch', 'equipment_departure_batch', 'p1', metadata={'count': 2})
    reactions = event_reactions(s.state, batch, s.skills, s.events, s.definitions)
    assert len(reactions) == 1 and reactions[0].skill == 'jie_xuanfeng'


def test_xuanfeng_move_uses_other_players_empty_matching_slot_and_restore():
    s = game('boundary_ling_tong')
    cid = put(s, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    put(s, 'equipment.armor.vine', 'p3', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    s.engine.start_action(BoundaryCombatAction('xuanfeng', 'p1', 'jie_xuanfeng'))
    answer(s, 'move')
    answer(s, cid)
    assert 'p1' not in s.engine.pending_request.allowed_player_ids
    assert 'p2' not in s.engine.pending_request.allowed_player_ids
    assert 'p3' not in s.engine.pending_request.allowed_player_ids
    s = restore_session(snapshot_session(s))
    answer(s, 'p4')
    assert s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p4', EquipmentSlot.ARMOR)) == (cid,)
    assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p2', EquipmentSlot.ARMOR))


def test_xuanfeng_two_cards_can_share_target_and_hidden_choices_remain_authoritative():
    s = game('boundary_ling_tong')
    cards = s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[:2]
    s.engine.start_action(BoundaryCombatAction('xuanfeng-discard', 'p1', 'jie_xuanfeng'))
    answer(s, 'discard')
    for cid in cards:
        answer(s, 'p2')
        assert s.engine.pending_request.subject_player_id == 'p2'
        answer(s, cid)
    assert all(cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for cid in cards)
    assert s.engine.pending_request is None


def test_paoxiao_unlimited_slash_and_distance_only_after_first_in_play_phase():
    s = game('boundary_zhang_fei')
    assert not slash_ignores_distance(s.state, 'p1', s.skills)
    slash = put(s, 'basic.slash')
    event_reactions(s.state, CardUsedEvent('first:used', 'p1', slash, ('p2',)), s.skills, s.events, s.definitions)
    assert slash_ignores_distance(s.state, 'p1', s.skills)
    from sanguosha.engine.military_basics import SkillSlashLimit
    assert SkillSlashLimit(s.skills).limit(s.state, 'p1') is None
    s.state.current_phase = Phase.FINISH
    assert not slash_ignores_distance(s.state, 'p1', s.skills)


def test_tishen_discards_all_tricks_and_horses_but_preserves_other_cards_and_expires():
    s = game('boundary_zhang_fei')
    empty_hand(s, 'p1')
    trick = put(s, 'trick.duel')
    delayed = put(s, 'delayed.indulgence')
    horse = put(s, 'equipment.horse.chitu')
    equip_horse = put(s, 'equipment.horse.dilu', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.DEFENSIVE_HORSE)
    peach = put(s, 'basic.peach')
    weapon = put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    reactions = event_reactions(s.state, PhaseEndedEvent('play:end', 'p1', Phase.PLAY), s.skills, s.events, s.definitions)
    assert len(reactions) == 1
    s.engine.start_action(reactions[0])
    answer(s, True)
    assert s.state.players['p1'].marks['jie_tishen_active'] == 1
    assert set((trick, delayed, horse, equip_horse)).issubset(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert peach in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert weapon in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON))
    s = restore_session(snapshot_session(s))
    event_reactions(s.state, TurnStartedEvent('next', 'p1', 2), s.skills, s.events, s.definitions)
    assert not s.state.players['p1'].marks.get('jie_tishen_active')


@pytest.mark.parametrize('hit', [False, True])
def test_tishen_collects_complete_slash_only_when_target_took_no_damage(hit):
    s = game('boundary_zhang_fei')
    s.state.players['p1'].marks['jie_tishen_active'] = 1
    slash = put(s, 'basic.slash', 'p2')
    CardMoveService(s.events).move(s.state, CardMove('use', (slash,), ZoneRef(ZoneType.HAND, 'p2'),
        ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE, 'p2'))
    event_reactions(s.state, CardUsedEvent('slash:used', 'p2', slash, ('p1', 'p3')),
                    s.skills, s.events, s.definitions)
    if hit:
        note_damage(s.state, MilitaryDamageAction('hit', 'p2', 'p1', 1, card_id=slash, card_kind='slash'))
    CardMoveService(s.events).move(s.state, CardMove('resolved', (slash,), ZoneRef(ZoneType.PROCESSING),
        ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.USE, 'p2'))
    event = s.events.events[-1]
    reactions = event_reactions(s.state, event, s.skills, s.events, s.definitions)
    assert len(reactions) == int(not hit)
    if reactions:
        s.engine.start_action(reactions[0])
        drain(s)
    assert (slash in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) is (not hit)
    s.state.__post_init__()


def test_xuanfeng_official_discard_branch_requires_second_card():
    s = game('boundary_ling_tong')
    cards = s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[:2]
    s.engine.start_action(BoundaryCombatAction('one-discard', 'p1', 'jie_xuanfeng'))
    answer(s, 'discard')
    answer(s, 'p2')
    answer(s, cards[0])
    assert s.engine.pending_request.request_type is RequestType.CHOOSE_PLAYER
    answer(s, 'p2')
    answer(s, cards[1])
    assert all(cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for cid in cards)
    assert s.engine.stack.is_empty()


def test_xuanfeng_real_equipment_exchange_with_two_slots_triggers_once():
    from sanguosha.engine.card_moves import EquipmentExchangeTransaction
    s = game('boundary_ling_tong')
    weapon = put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    armor = put(s, 'equipment.armor.vine', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    moves = s.engine.reaction_provider.__self__
    moves.exchange_equipment(s.state, EquipmentExchangeTransaction('real-exchange', ('p1', 'p2'), 'p3'))
    s.engine.start_action(DrawCardsAction('dispatch-exchange', 'p3', 1))
    requests = 0
    while s.engine.pending_request is not None:
        request = s.engine.pending_request
        assert request.player_id == 'p1' and '旋风' in request.prompt
        requests += 1
        answer(s, 'cancel')
    assert requests == 1
    assert weapon in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p2', EquipmentSlot.WEAPON))
    assert armor in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p2', EquipmentSlot.ARMOR))


def test_pojun_true_use_removing_two_equipment_slots_gives_one_xuanfeng():
    s = game()
    s.state.players['p2'].character_id = 'boundary_ling_tong'
    weapon = put(s, 'equipment.weapon.crossbow', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    armor = put(s, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    slash = put(s, 'basic.slash')
    s.engine.start_action(UseCardAction('true-pojun', 'p1', slash, ('p2',)))
    assert s.engine.pending_request.player_id == 'p1' and '破军' in s.engine.pending_request.prompt
    answer(s, True)
    answer(s, (weapon, armor))
    wind_requests = 0
    while s.engine.pending_request is not None:
        request = s.engine.pending_request
        if '旋风' in request.prompt:
            wind_requests += 1
            assert request.player_id == 'p2'
            answer(s, 'cancel')
        else:
            answer(s, request.timeout_value())
    assert wind_requests == 1
    facts = [e for e in s.events.events if getattr(e, 'event_type', '') == 'equipment_departure_batch']
    assert len(facts) == 1 and facts[0].source_id == 'p2' and facts[0].metadata['count'] == 2
    assert all(cid in s.state.cards_in(next(ref for ref in s.state.zones
        if ref.zone_type is ZoneType.SPECIAL and ref.special_key.startswith(POJUN_PREFIX)))
        for cid in (weapon, armor))
    s.state.__post_init__()


def test_pojun_true_use_returns_at_normal_turn_end_and_not_phase_end():
    s = game()
    empty_hand(s, 'p2')
    armor = put(s, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    slash = put(s, 'basic.slash')
    s.engine.start_action(TurnAction('ordinary-turn', 'p1', phases=(Phase.PLAY, Phase.FINISH)))
    answer(s, 'use:' + slash)
    answer(s, 'p2')
    answer(s, True)
    answer(s, (armor,))
    for _ in range(20):
        request = s.engine.pending_request
        if request.request_type is RequestType.CHOOSE_OPTION and END_PLAY_PHASE in request.choices:
            break
        answer(s, request.timeout_value())
    else:
        raise AssertionError('Slash did not finish before the turn resumed')
    pile = next(ref for ref in s.state.zones
                if ref.zone_type is ZoneType.SPECIAL and ref.special_key.startswith(POJUN_PREFIX))
    assert s.state.cards_in(pile) == (armor,)
    assert s.state.players['p2'].hp == 2
    s = restore_session(snapshot_session(s))
    answer(s, END_PLAY_PHASE)
    drain(s)
    assert not s.state.cards_in(pile)
    assert armor in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p2', EquipmentSlot.ARMOR))
    assert not s.state.metadata.get('revealed_committed')


def test_pojun_terminal_cleanup_returns_living_target_cards_and_leaves_no_transient_pile():
    from sanguosha.model.state import GameStatus
    s = game()
    s.state.players['p1'].identity = Identity.LORD
    for pid in ('p2', 'p3', 'p4', 'p5'):
        s.state.players[pid].identity = Identity.REBEL
    card = put(s, 'basic.dodge', 'p2')
    s.engine.start_action(BoundaryCombatAction('terminal-remove', 'p1', 'jie_pojun', 'p2'))
    answer(s, True)
    answer(s, (card,))
    s.engine.start_action(DeathAction('end-game', 'p1', None))
    drain(s)
    assert s.state.status is GameStatus.FINISHED
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert not any(s.state.cards_in(ref) for ref in s.state.zones
                   if ref.zone_type is ZoneType.SPECIAL and ref.special_key.startswith(POJUN_PREFIX))
    assert not s.state.metadata.get('t22_slash_uses')
    assert s.engine.pending_request is None and s.engine.stack.is_empty()


def test_tishen_real_cost_loses_two_horses_in_one_xuanfeng_batch():
    s = game('boundary_zhang_fei')
    s.state.players['p1'].granted_skills['jie_xuanfeng'] = 'test'
    put(s, 'equipment.horse.chitu', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.OFFENSIVE_HORSE)
    put(s, 'equipment.horse.dilu', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.DEFENSIVE_HORSE)
    s.engine.start_action(BoundaryCombatAction('horse-cost', 'p1', 'jie_tishen'))
    answer(s, True)
    requests = 0
    while s.engine.pending_request is not None:
        request = s.engine.pending_request
        assert '旋风' in request.prompt
        requests += 1
        answer(s, 'cancel')
    assert requests == 1
    assert s.state.players['p1'].marks['jie_tishen_active'] == 1
    assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.OFFENSIVE_HORSE))
    assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.DEFENSIVE_HORSE))


@pytest.mark.parametrize('virtual', [False, True])
@pytest.mark.parametrize('zhang_fei_hit', [False, True])
def test_tishen_true_multitarget_slash_waits_for_all_targets_and_restores(virtual, zhang_fei_hit):
    s = game('boundary_zhang_fei')
    s.state.players['p1'].marks['jie_tishen_active'] = 1
    empty_hand(s, 'p2')
    put(s, 'equipment.weapon.halberd', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    slash = put(s, 'basic.peach' if virtual else 'basic.slash', 'p2')
    if virtual:
        s.state.cards[slash] = replace(s.state.cards[slash], suit=Suit.HEART)
        s.state.players['p2'].granted_skills['wushen'] = 'test'
    dodge = put(s, 'basic.dodge', 'p1')
    s.state.current_player_id = 'p2'
    s.state.play_usage = PlayUsageState('p2', 1)
    s.engine.start_action(UseCardAction('multitarget', 'p2', slash, ('p1', 'p3')))
    assert s.engine.pending_request.player_id == 'p1'
    answer(s, PASS_RESPONSE if zhang_fei_hit else dodge)
    assert s.engine.pending_request.player_id == 'p3'
    assert slash in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    assert slash not in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    s = restore_session(snapshot_session(s))
    answer(s, PASS_RESPONSE)
    drain(s)
    assert s.state.players['p3'].hp == 3
    destination = ZoneRef(ZoneType.DISCARD_PILE) if zhang_fei_hit else ZoneRef(ZoneType.HAND, 'p1')
    assert slash in s.state.cards_in(destination)
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    assert not s.state.metadata.get('t22_slash_uses')


def test_tishen_real_spear_slash_recovers_both_physical_materials_after_dodge():
    from sanguosha.engine.view_as import UseSpear
    s = game('boundary_zhang_fei')
    s.state.players['p1'].marks['jie_tishen_active'] = 1
    empty_hand(s, 'p2')
    put(s, 'equipment.weapon.serpent_spear', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    cards = (put(s, 'basic.peach', 'p2'), put(s, 'basic.wine', 'p2'))
    dodge = put(s, 'basic.dodge', 'p1')
    s.state.current_player_id = 'p2'
    s.state.play_usage = PlayUsageState('p2', 1)
    s.engine.start_action(UseSpear('virtual-two-materials', 'p2'))
    answer(s, cards)
    answer(s, 'p1')
    assert set(cards).issubset(s.state.cards_in(ZoneRef(ZoneType.PROCESSING)))
    s = restore_session(snapshot_session(s))
    answer(s, dodge)
    drain(s)
    assert set(cards).issubset(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    assert not s.state.metadata.get('t22_slash_uses')
