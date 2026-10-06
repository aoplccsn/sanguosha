"""Minimal reproductions of final audit findings."""
import pytest
from test_t17c_first_batch import setup, restore
from test_t17b_tier1 import answer, finish
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.god_lvbu import WuqianAction, ShenfenAction
from sanguosha.engine.skill_leases import begin_lease, expire_target
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.enums import Phase
from sanguosha.engine.turns import TurnAction


def game():
    s = setup('xun_you')
    for p in s.state.players.values():
        p.character_id = 'caocao'
    s.state.players['p1'].character_id = 'thunder_god_zhangliao'
    s.state.players['p2'].character_id = 'forest_god_lvbu'
    return s



def test_duorui_cannot_borrow_unique_kuangbao():
    from sanguosha.engine.zhangliao import borrowable
    s = game()
    assert 'kuangbao' not in borrowable(s.state, 'p2', s.skills)


def test_duanchang_lost_kuangbao_does_not_gain_rage_on_later_damage():
    from sanguosha.engine.death import DeathAction
    s = game()
    s.state.players['p3'].character_id = 'mountain_cai_wenji'
    s.engine.start_action(DeathAction('duanchang-rage', 'p3', 'p2'))
    finish(s)
    assert not s.skills.has(s.state, 'p2', 'kuangbao')
    before = s.state.players['p2'].marks.get('rage', 0)
    s.engine.start_action(MilitaryDamageAction('after-duanchang', 'p4', 'p2', 1))
    finish(s)
    assert s.state.players['p2'].marks.get('rage', 0) == before


def test_duorui_dawu_suppression_removes_fog_offer_but_preserves_wind():
    from test_t6_military_basics import put
    from sanguosha.engine.gods import StarWeatherAction, star_zone
    from sanguosha.engine.card_moves import CardMove, CardMoveReason
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p2'].character_id = 'fire_god_zhugeliang'
    cid = put(s, 'basic.slash', 'p2')
    s.engine.reaction_provider.__self__.move(s.state, CardMove('star-fixture', (cid,),
        ZoneRef(ZoneType.HAND, 'p2'), star_zone('p2'), CardMoveReason.SYSTEM))
    begin_lease(s.state, 'p1', 'p2', 'dawu')
    s.engine.start_action(StarWeatherAction('leased-dawu', 'p2'))
    assert s.engine.pending_request.choices == ('wind', 'done')
    answer(s, 'done')
    expire_target(s.state, 'p2')
    s.engine.start_action(StarWeatherAction('returned-dawu', 'p2'))
    assert s.engine.pending_request.choices == ('wind', 'fog', 'done')


@pytest.mark.parametrize('first', ['guidao', 'guicai'])
def test_same_owner_retrial_can_choose_order_and_final_replacement(first):
    from dataclasses import replace
    from test_t6_military_basics import put
    from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
    from sanguosha.model.enums import Suit
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p1'].granted_skills.update(guidao='audit', guicai='jilue.permanent')
    s.state.players['p1'].marks['ren'] = 2
    black = put(s, 'basic.slash', 'p1')
    red = put(s, 'basic.slash', 'p1')
    s.state.cards[black] = replace(s.state.cards[black], suit=Suit.SPADE)
    s.state.cards[red] = replace(s.state.cards[red], suit=Suit.HEART)
    s.engine.start_action(JudgmentAction('chosen-retrial', 'p3', JudgmentPattern(suit=Suit.HEART)))
    assert s.engine.pending_request.choices == ('鬼才', '鬼道')
    s = restore(s)
    answer(s, '鬼道' if first == 'guidao' else '鬼才')
    answer(s, True)
    answer(s, black if first == 'guidao' else red)
    answer(s, True)
    answer(s, red if first == 'guidao' else black)
    assert s.engine.last_result is (first == 'guidao')
    assert s.state.players['p1'].marks['ren'] == 2
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


@pytest.mark.parametrize('first', ['tiandu', 'songwei'])
def test_finish_judge_tiandu_songwei_order_is_judged_players_choice(first):
    from dataclasses import replace
    from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
    from sanguosha.engine.events import CardMovedEvent
    from sanguosha.model.enums import Suit, Identity
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p1'].character_id = 'forest_caopi'
    s.state.players['p1'].identity = Identity.LORD
    s.state.players['p2'].character_id = 'guojia'
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.SPADE)
    before = len(s.events.events)
    s.engine.start_action(JudgmentAction('chosen-finish', 'p2', JudgmentPattern()))
    assert s.engine.pending_request.choices == ('天妒', '颂威')
    s = restore(s)
    answer(s, '天妒' if first == 'tiandu' else '颂威')
    answer(s, True)
    answer(s, True)
    moves = [e for e in s.events.events[before:] if isinstance(e, CardMovedEvent) and e.to_zone.zone_type is ZoneType.HAND]
    assert [e.to_zone.player_id for e in moves] == (['p2', 'p1'] if first == 'tiandu' else ['p1', 'p2'])
    assert top in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))


def test_finish_judge_field_before_tiandu_removes_obtain_window():
    from dataclasses import replace
    from sanguosha.engine.mountain import TuntianAction, field_zone
    from sanguosha.model.enums import Suit
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p2'].character_id = 'mountain_deng_ai'
    s.state.players['p2'].granted_skills['tiandu'] = 'audit'
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.CLUB)
    s.engine.start_action(TuntianAction('chosen-field', 'p2'))
    answer(s, True)
    assert s.engine.pending_request.choices == ('天妒', '屯田')
    s = restore(s)
    answer(s, '屯田')
    assert s.engine.pending_request is None
    assert top in s.state.cards_in(field_zone('p2'))


@pytest.mark.parametrize('count', [1, 2])
def test_small_yeyan_allows_fewer_than_three_targets(count):
    from sanguosha.engine.gods import YeyanAction
    s = game()
    s.state.players['p1'].character_id = 'fire_god_zhouyu'
    s.engine.start_action(YeyanAction('small-yeyan', 'p1'))
    answer(s, 'small')
    targets = ('p3', 'p4')[:count]
    before = {pid: s.state.players[pid].hp for pid in targets}
    answer(s, targets)
    finish(s)
    assert all(s.state.players[pid].hp == before[pid] - 1 for pid in targets)
    assert s.state.players['p1'].marks['yeyan_used'] == 1


def test_yeyan_can_target_self():
    from sanguosha.engine.gods import YeyanAction
    s = game()
    s.state.players['p1'].character_id = 'fire_god_zhouyu'
    s.engine.start_action(YeyanAction('self-yeyan', 'p1'))
    answer(s, 'small')
    assert 'p1' in s.engine.pending_request.allowed_player_ids
    hp = s.state.players['p1'].hp
    answer(s, ('p1',))
    finish(s)
    assert s.state.players['p1'].hp == hp - 1


def test_great_yeyan_cannot_pay_missing_suit_with_equipped_card():
    from dataclasses import replace
    from test_t6_military_basics import put
    from test_t17c_juece import empty
    from sanguosha.engine.gods import YeyanAction
    from sanguosha.model.enums import Suit, EquipmentSlot
    from sanguosha.model.zones import ZoneType
    s = game()
    s.state.players['p1'].character_id = 'fire_god_zhouyu'
    empty(s, 'p1')
    for suit in (Suit.HEART, Suit.CLUB, Suit.SPADE):
        cid = put(s, 'basic.slash', 'p1')
        s.state.cards[cid] = replace(s.state.cards[cid], suit=suit)
    cid = put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    s.state.cards[cid] = replace(s.state.cards[cid], suit=Suit.DIAMOND)
    s.engine.start_action(YeyanAction('hand-yeyan', 'p1'))
    assert s.engine.pending_request.choices == ('small',)


@pytest.mark.parametrize('mode,suit', [('peach', 'heart'), ('slash', 'diamond'), ('response', 'club')])
def test_classic_longhun_can_pay_mixed_hand_equipment_materials(mode, suit):
    from dataclasses import replace
    from test_t6_military_basics import put
    from sanguosha.engine.gods import LonghunUse, longhun_option
    from sanguosha.engine.response import RespondWithCardAction
    from sanguosha.model.enums import Suit, EquipmentSlot
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p1'].character_id = 'mountain_god_zhaoyun'
    s.state.players['p1'].hp = 2
    s.state.players['p1'].max_hp = 3
    a = put(s, 'basic.slash', 'p1')
    b = put(s, 'equipment.armor.vine', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    for cid in (a, b):
        s.state.cards[cid] = replace(s.state.cards[cid], suit=Suit(suit))
    if mode == 'response':
        s.engine.start_action(RespondWithCardAction('equipment-longhun', 'p1', 'basic.dodge', 'incoming'))
        assert longhun_option((a, b)) in s.engine.pending_request.eligible_card_ids
        s = restore(s)
        answer(s, longhun_option((a, b)))
    else:
        s.engine.start_action(LonghunUse('equipment-longhun', 'p1', (a, b),
            'basic.peach' if mode == 'peach' else 'basic.fire_slash'))
        if mode == 'slash':
            s = restore(s)
            answer(s, 'p2')
        finish(s)
    assert {a, b} <= set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    if mode == 'peach':
        assert s.state.players['p1'].hp == 3



def test_wushen_heart_peach_has_locked_slash_identity_and_distant_targets():
    from dataclasses import replace
    from test_t6_military_basics import put
    from sanguosha.projection import project_for_human
    from sanguosha.engine.card_use import UseCardAction
    from sanguosha.model.enums import Suit
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p1'].character_id = 'wind_god_guanyu'
    cid = put(s, 'basic.peach', 'p1')
    s.state.cards[cid] = replace(s.state.cards[cid], suit=Suit.HEART)
    view = project_for_human(s.state, s.definitions, 'p1', {})
    assert next(c for c in view.hand if c.card_id == cid).definition_id == 'basic.slash'
    s.engine.start_action(UseCardAction('locked-wushen', 'p1', cid, ('p3',)))
    finish(s)
    assert s.state.play_usage.count('basic.slash') == 1
    assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_wushen_heart_peach_cannot_be_offered_as_peach_response():
    from dataclasses import replace
    from test_t6_military_basics import put
    from sanguosha.engine.response import RespondWithCardAction
    from sanguosha.model.enums import Suit
    s = game()
    s.state.players['p1'].character_id = 'wind_god_guanyu'
    cid = put(s, 'basic.peach', 'p1')
    s.state.cards[cid] = replace(s.state.cards[cid], suit=Suit.HEART)
    s.engine.start_action(RespondWithCardAction('heart-rescue', 'p1', 'basic.peach', 'rescue'))
    assert s.engine.pending_request is None or cid not in s.engine.pending_request.eligible_card_ids


def test_classic_wuhun_god_salvation_judgment_preserves_target():
    from dataclasses import replace
    from sanguosha.engine.gods import WuhunDeathAction
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p1'].character_id = 'wind_god_guanyu'
    s.state.players['p2'].marks['nightmare'] = 2
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], definition_id='trick.god_salvation')
    s.engine.start_action(WuhunDeathAction('peach-garden-wuhun', 'p1'))
    finish(s)
    assert s.state.players['p2'].is_alive



def test_wuhun_self_damage_does_not_create_nightmare():
    s = game()
    s.state.players['p1'].character_id = 'wind_god_guanyu'
    s.engine.start_action(MilitaryDamageAction('self-wuhun', 'p1', 'p1', 1))
    finish(s)
    assert not s.state.players['p1'].marks.get('nightmare')


def test_wuhun_revenge_clears_nightmare_marks_after_resolution():
    from dataclasses import replace
    from sanguosha.engine.gods import WuhunDeathAction
    from sanguosha.model.zones import ZoneRef, ZoneType
    s = game()
    s.state.players['p1'].character_id = 'wind_god_guanyu'
    s.state.players['p2'].marks['nightmare'] = 2
    s.state.players['p3'].marks['nightmare'] = 1
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], definition_id='basic.peach')
    s.engine.start_action(WuhunDeathAction('clean-wuhun', 'p1'))
    finish(s)
    assert not any(p.marks.get('nightmare') for p in s.state.players.values())



def test_zhijian_cannot_replace_occupied_equipment_slot():
    from test_t6_military_basics import put
    from sanguosha.engine.mountain import ZhijianAction
    from sanguosha.model.enums import EquipmentSlot
    from sanguosha.model.zones import ZoneType
    s = game()
    s.state.players['p1'].character_id = 'mountain_zhang_zhaozhang'
    cid = put(s, 'equipment.weapon.serpent_spear', 'p1')
    put(s, 'equipment.weapon.crossbow', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    s.engine.start_action(ZhijianAction('occupied-zhijian', 'p1'))
    answer(s, cid)
    assert 'p2' not in s.engine.pending_request.allowed_player_ids
    assert 'p3' in s.engine.pending_request.allowed_player_ids



def test_native_guicai_and_jilue_same_skill_only_retrials_once():
    from dataclasses import replace
    from test_t6_military_basics import put
    from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
    from sanguosha.model.enums import Suit
    from sanguosha.multiplayer.room import MultiplayerRoom
    s = game()
    s.state.players['p1'].granted_skills.update(guicai='audit', jilue='audit')
    s.state.players['p1'].marks['ren'] = 1
    first = put(s, 'basic.slash', 'p1')
    last = put(s, 'basic.slash', 'p1')
    s.state.cards[first] = replace(s.state.cards[first], suit=Suit.HEART)
    s.state.cards[last] = replace(s.state.cards[last], suit=Suit.SPADE)
    s.engine.start_action(JudgmentAction('public-two-retrials', 'p3', JudgmentPattern(suit=Suit.SPADE)))
    for choice in (True, first):
        answer(s, choice)
    room = MultiplayerRoom()
    room.session = s
    public = [room._public_event(e) for e in s.events.events if getattr(e, 'event_type', '') == 'judgment_card_replaced']
    assert len(public) == 1
    # Presentation's seen set uses event_id, so both accepted replacements need identities.
    assert len({e['event_id'] for e in public}) == 1
