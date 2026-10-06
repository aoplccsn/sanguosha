from dataclasses import replace

import pytest
from test_t17c_first_batch import setup, restore
from test_t17c_qice import clear_hand
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.wind_guhuo import GuhuoAction
from sanguosha.engine.yj2012 import YJ2012Action
from sanguosha.engine.requests import RequestType, PASS_RESPONSE
from sanguosha.model.enums import Suit, PlayerStatus, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType


def drain(s, challenge=False):
    """Reconnect at each request; responses time out except explicit challenge."""
    for _ in range(150):
        r = s.engine.pending_request
        if r is None:
            assert s.engine.stack.is_empty()
            assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
            s.state.__post_init__()
            return s
        s = restore(s)
        if r.request_type is RequestType.RESPOND_WITH_CARD:
            value = PASS_RESPONSE
        elif r.request_type is RequestType.YES_NO:
            value = challenge and ':challenge:' in r.request_id and r.player_id == 'p3'
        else:
            value = r.timeout_value()
        answer(s, value)
    raise AssertionError('AOE did not settle')


@pytest.mark.parametrize('challenged', [False, True])
def test_guhuo_true_heart_savage_is_obtained_by_juxiang(challenged):
    s = setup('xun_you')
    s.state.players['p1'].character_id = 'wind_yuji'
    s.state.players['p2'].character_id = 'forest_zhurong'
    clear_hand(s)
    card = put(s, 'trick.savage_assault')
    s.state.cards[card] = replace(s.state.cards[card], suit=Suit.HEART)
    hp = s.state.players['p2'].hp
    s.engine.start_action(GuhuoAction('audit-guhuo', 'p1'))
    answer(s, 'trick.savage_assault')
    answer(s, card)
    s = drain(s, challenged)
    assert s.state.players['p2'].hp == hp
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert card not in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


@pytest.mark.parametrize('count', [1, 3])
def test_qice_savage_materials_are_not_obtained_by_juxiang(count):
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'forest_zhurong'
    clear_hand(s)
    cards = tuple(put(s, 'basic.slash') for _ in range(count))
    hp = s.state.players['p2'].hp
    s.engine.start_action(YJ2012Action('audit-qice', 'p1', 'qice'))
    answer(s, 'trick.savage_assault')
    s = drain(s)
    assert s.state.players['p2'].hp == hp
    assert set(cards) <= set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert not set(cards) & set(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))

@pytest.mark.parametrize('condition,expected', [
    ('active', 'hand'), ('own', 'discard_pile'),
    ('suppressed', 'discard_pile'), ('dead', 'discard_pile'),
])
def test_physical_savage_juxiang_capture_boundaries(condition, expected):
    from sanguosha.engine.events import CardMovedEvent
    s = setup('xun_you')
    owner = 'p1' if condition == 'own' else 'p2'
    s.state.players[owner].character_id = 'forest_zhurong'
    if condition == 'suppressed':
        s.state.players[owner].disabled_skills.add('juxiang')
    if condition == 'dead':
        s.state.players[owner].status = PlayerStatus.DEAD
        s.state.players[owner].hp = 0
    card = put(s, 'trick.savage_assault')
    hp = s.state.players[owner].hp
    s.engine.start_action(UseCardAction('audit-physical', 'p1', card))
    s = drain(s)
    destination = ZoneRef(ZoneType.HAND, owner) if expected == 'hand' else ZoneRef(ZoneType.DISCARD_PILE)
    assert card in s.state.cards_in(destination)
    if condition == 'active':
        assert s.state.players[owner].hp == hp
        assert not any(isinstance(e, CardMovedEvent) and card in e.card_ids
                       and e.to_zone.zone_type is ZoneType.DISCARD_PILE for e in s.events.events
                       if e.event_id.startswith('audit-physical'))


@pytest.mark.parametrize('actual,suit,challenge,captured', [
    ('basic.slash', Suit.SPADE, False, True),
    ('basic.slash', Suit.HEART, True, False),
    ('trick.savage_assault', Suit.CLUB, True, False),
])
def test_guhuo_only_effective_declaration_is_captured(actual, suit, challenge, captured):
    s = setup('xun_you')
    s.state.players['p1'].character_id = 'wind_yuji'
    s.state.players['p2'].character_id = 'forest_zhurong'
    clear_hand(s)
    card = put(s, actual)
    s.state.cards[card] = replace(s.state.cards[card], suit=suit)
    s.engine.start_action(GuhuoAction('audit-guhuo-boundary', 'p1'))
    answer(s, 'trick.savage_assault')
    answer(s, card)
    s = drain(s, challenge)
    assert (card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) is captured
    if captured:
        assert card not in s.state.metadata.get('concealed_discard_cards', {})


def test_huoshou_death_mid_aoe_leaves_later_damage_without_source():
    from sanguosha.engine.events import DamageDealtEvent
    from sanguosha.model.enums import Identity
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'xiahou_dun'
    s.state.players['p3'].character_id = 'forest_menghuo'
    s.state.players['p3'].hp = 1
    s.state.players['p3'].identity = Identity.REBEL
    card = put(s, 'trick.savage_assault')
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.SPADE)
    s.engine.start_action(UseCardAction('audit-huoshou', 'p1', card))
    for _ in range(150):
        r = s.engine.pending_request
        if r is None:
            break
        s = restore(s)
        if r.request_type is RequestType.YES_NO:
            value = r.request_id.endswith(':ganglie:offer')
        elif r.request_type is RequestType.CHOOSE_OPTION and r.request_id.endswith(':source-choice'):
            value = 'damage'
        else:
            value = r.timeout_value()
        answer(s, value)
    assert not s.state.players['p3'].is_alive
    # The source is fixed when Savage is declared; death clears attribution,
    # rather than assigning the remaining targets' damage back to the user.
    aoe = [e for e in s.events.events if isinstance(e, DamageDealtEvent)
           and e.target_id in ('p2', 'p4', 'p5')]
    assert [(e.target_id, e.source_id) for e in aoe] == [('p2', 'p3'), ('p4', None), ('p5', None)]


def test_juxiang_does_not_reclaim_material_already_obtained_by_jianxiong():
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'caocao'
    s.state.players['p3'].character_id = 'forest_zhurong'
    card = put(s, 'trick.savage_assault')
    s.engine.start_action(UseCardAction('audit-jianxiong', 'p1', card))
    for _ in range(150):
        r = s.engine.pending_request
        if r is None:
            break
        s = restore(s)
        value = r.request_id.endswith(':jianxiong') if r.request_type is RequestType.YES_NO else r.timeout_value()
        answer(s, value)
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert card not in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_huoshou_source_remains_fixed_after_skill_is_suppressed_mid_use():
    from sanguosha.engine.events import DamageDealtEvent
    s = setup('xun_you')
    s.state.players['p3'].character_id = 'forest_menghuo'
    card = put(s, 'trick.savage_assault')
    s.engine.start_action(UseCardAction('audit-suppressed-source', 'p1', card))
    changed = False
    for _ in range(150):
        r = s.engine.pending_request
        if r is None:
            break
        if not changed and any(isinstance(e, DamageDealtEvent) and e.target_id == 'p2' for e in s.events.events):
            s.state.players['p3'].disabled_skills.add('huoshou')
            changed = True
        s = restore(s)
        answer(s, r.timeout_value())
    assert changed
    aoe = [e for e in s.events.events if isinstance(e, DamageDealtEvent)]
    assert all(e.source_id == 'p3' for e in aoe)

@pytest.mark.parametrize('mode', ['qice-savage', 'qice-archery', 'luanji'])
def test_virtual_aoe_jianxiong_obtains_all_materials(mode):
    from sanguosha.engine.fire import LuanjiAction
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'caocao'
    clear_hand(s)
    materials = tuple(put(s, 'basic.slash') for _ in range(2))
    for card in materials:
        s.state.cards[card] = replace(s.state.cards[card], suit=Suit.HEART)
    if mode == 'luanji':
        s.state.players['p1'].character_id = 'fire_yuan_shao'
        s.engine.start_action(LuanjiAction('audit-materials', 'p1', materials))
    else:
        s.engine.start_action(YJ2012Action('audit-materials', 'p1', 'qice'))
        answer(s, 'trick.savage_assault' if mode == 'qice-savage' else 'trick.archery_attack')
    for _ in range(150):
        r = s.engine.pending_request
        if r is None:
            break
        s = restore(s)
        answer(s, r.request_id.endswith(':jianxiong') if r.request_type is RequestType.YES_NO else r.timeout_value())
    assert set(materials) <= set(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


@pytest.mark.parametrize('skill', ['wuyan-target', 'wuyan-source', 'luoyi'])
def test_qice_aoe_damage_uses_virtual_trick_identity_not_basic_material(skill):
    s = setup('xun_you')
    clear_hand(s)
    put(s, 'basic.slash')
    if skill.startswith('wuyan'):
        owner = 'p2' if skill.endswith('target') else 'p1'
        s.state.players[owner].granted_skills['wuyan'] = 'audit-grant'
    else:
        s.state.players['p1'].marks['luoyi'] = 1
    hp = s.state.players['p2'].hp
    s.engine.start_action(YJ2012Action('audit-type', 'p1', 'qice'))
    answer(s, 'trick.savage_assault')
    s = drain(s)
    assert s.state.players['p2'].hp == hp - (skill == 'luoyi')

@pytest.mark.parametrize('other_zone', [ZoneType.HAND, ZoneType.DISCARD_PILE])
def test_classic_jianxiong_requires_whole_virtual_card_still_on_table(other_zone):
    from sanguosha.engine.military_basics import MilitaryDamageAction
    from sanguosha.engine.card_moves import CardMove, CardMoveReason
    from sanguosha.model.virtual_card import VirtualCard
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'caocao'
    cards = tuple(put(s, 'basic.slash') for _ in range(2))
    moves = s.engine.reaction_provider.__self__
    moves.move(s.state, CardMove('audit-one-on-table', (cards[0],), ZoneRef(ZoneType.HAND, 'p1'),
                               ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE, 'p1'))
    if other_zone is ZoneType.DISCARD_PILE:
        moves.move(s.state, CardMove('audit-already-discarded', (cards[1],), ZoneRef(ZoneType.HAND, 'p1'),
                                   ZoneRef(other_zone), CardMoveReason.USE, 'p1'))
    virtual = VirtualCard('trick.archery_attack', cards, Suit.HEART, None, 'luanji')
    s.engine.start_action(MilitaryDamageAction('audit-partial-card', 'p1', 'p2', 1,
                                              card_id=cards[0], material_card_ids=cards, virtual_card=virtual))
    assert s.engine.pending_request is None
    assert cards[0] in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_amazing_grace_reveals_for_all_living_seats_without_temporary_hand_gain():
    from sanguosha.engine.events import CardMovedEvent
    s = setup('xun_you')
    s.state.players['p2'].character_id = 'forest_jia_xu'
    card = put(s, 'trick.amazing_grace')
    s.state.cards[card] = replace(s.state.cards[card], suit=Suit.SPADE)
    s.engine.start_action(UseCardAction('audit-grace', 'p1', card))
    pool = next(ref for ref in s.state.zones if ref.special_key == 'audit-grace:effect')
    assert len(s.state.cards_in(pool)) == 5
    reveal_moves = [e for e in s.events.events if isinstance(e, CardMovedEvent)
                    and e.event_id.startswith('audit-grace:effect:')]
    assert not any(e.to_zone.zone_type is ZoneType.HAND for e in reveal_moves)
    s = drain(s)
    assert not s.state.cards_in(pool)


def test_classic_guhuo_black_declared_aoe_is_not_prohibited_by_weimu():
    s = setup('xun_you')
    s.state.players['p1'].character_id = 'wind_yuji'
    s.state.players['p2'].character_id = 'forest_jia_xu'
    clear_hand(s)
    card = put(s, 'basic.slash')
    s.state.cards[card] = replace(s.state.cards[card], suit=Suit.SPADE)
    hp = s.state.players['p2'].hp
    s.engine.start_action(GuhuoAction('audit-nosguhuo-weimu', 'p1'))
    answer(s, 'trick.archery_attack')
    answer(s, card)
    s = drain(s)
    assert s.state.players['p2'].hp == hp - 1

@pytest.mark.parametrize('skill,definition,suit,suppressed,blocked', [
    ('qianxun', 'trick.snatch', Suit.HEART, False, True),
    ('qianxun', 'delayed.indulgence', Suit.HEART, False, True),
    ('qianxun', 'trick.dismantlement', Suit.HEART, False, False),
    ('qianxun', 'trick.duel', Suit.SPADE, False, False),
    ('qianxun', 'delayed.indulgence', Suit.HEART, True, False),
    ('weimu', 'trick.snatch', Suit.SPADE, False, True),
    ('weimu', 'trick.duel', Suit.CLUB, False, True),
    ('weimu', 'delayed.indulgence', Suit.SPADE, False, True),
    ('weimu', 'delayed.supply_shortage', Suit.CLUB, False, True),
    ('weimu', 'trick.duel', Suit.HEART, False, False),
    ('weimu', 'trick.duel', Suit.SPADE, True, False),
])
def test_classic_prohibit_skills_reject_before_cost_and_restore(skill, definition, suit, suppressed, blocked):
    from sanguosha.engine.card_rules import InvalidCardUse
    s = setup('xun_you')
    s.state.players['p2'].granted_skills[skill] = 'audit-grant'
    if suppressed:
        s.state.players['p2'].disabled_skills.add(skill)
    card = put(s, definition)
    s.state.cards[card] = replace(s.state.cards[card], suit=suit)
    s = restore(s)
    if blocked:
        with pytest.raises(InvalidCardUse):
            s.engine.start_action(UseCardAction('audit-prohibit', 'p1', card, ('p2',)))
        assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    else:
        s.engine.start_action(UseCardAction('audit-prohibit', 'p1', card, ('p2',)))
        s = drain(s)
        assert card not in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))

@pytest.mark.parametrize('suits,allowed', [((Suit.SPADE, Suit.HEART), True), ((Suit.SPADE, Suit.CLUB), False)])
def test_qice_qiaoshui_extra_target_weimu_checks_combined_virtual_color(suits, allowed):
    s = setup('xun_you')
    s.state.players['p1'].granted_skills['qiaoshui'] = 'audit-grant'
    s.state.players['p1'].marks['qiaoshui_success'] = s.state.turn_number
    s.state.players['p3'].character_id = 'forest_jia_xu'
    clear_hand(s)
    for suit in suits:
        card = put(s, 'basic.slash')
        s.state.cards[card] = replace(s.state.cards[card], suit=suit)
    s.engine.start_action(YJ2012Action('audit-qice-qiaoshui', 'p1', 'qice'))
    answer(s, 'trick.duel')
    answer(s, ('p2',))
    s = restore(s)
    assert 'add' in s.engine.pending_request.choices
    answer(s, 'add')
    s = restore(s)
    assert ('p3' in s.engine.pending_request.allowed_player_ids) is allowed
    answer(s, 'p3' if allowed else 'p4')
    s = drain(s)

@pytest.mark.parametrize('immunity', ['vine', 'huoshou', 'juxiang', 'zhichi'])
def test_zhenlie_target_confirmation_occurs_before_aoe_effect_immunity(immunity):
    from sanguosha.engine.military_basics import MilitaryDamageAction
    s = setup('xun_you')
    s.state.players['p2'].granted_skills['zhenlie'] = 'audit-grant'
    if immunity == 'vine':
        put(s, 'equipment.armor.vine', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    elif immunity == 'zhichi':
        s.state.players['p2'].granted_skills['zhichi'] = 'audit-grant'
        s.engine.start_action(MilitaryDamageAction('audit-zhichi-first', 'p1', 'p2', 1))
        assert s.engine.pending_request is None
    else:
        s.state.players['p2'].granted_skills[immunity] = 'audit-grant'
    card = put(s, 'trick.savage_assault')
    hp = s.state.players['p2'].hp
    cost = put(s, 'basic.slash')
    s.engine.start_action(UseCardAction('audit-immune-zhenlie', 'p1', card))
    r = s.engine.pending_request
    assert r.player_id == 'p2' and r.request_type is RequestType.YES_NO
    s = restore(s)
    answer(s, True)
    assert cost in s.engine.pending_request.eligible_card_ids
    answer(s, cost)
    s = drain(s)
    assert s.state.players['p2'].hp == hp - 1
    assert cost in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

@pytest.mark.parametrize('definition,hp,wanted', [('trick.duel', 3, True), ('trick.god_salvation', 3, False), ('trick.duel', 1, False)])
def test_zhenlie_ai_uses_public_card_kind_and_avoids_lethal_cost(definition, hp, wanted):
    from sanguosha.decisions.yj2012 import decide
    class PublicAttitude:
        def _priority(self, state, pid, source):
            return 1
    s = setup('xun_you')
    s.state.players['p2'].granted_skills['zhenlie'] = 'audit-grant'
    s.state.players['p2'].hp = hp
    card = put(s, definition)
    s.engine.start_action(UseCardAction('audit-zhenlie-ai', 'p1', card, ('p2',) if definition == 'trick.duel' else ()))
    r = s.engine.pending_request
    assert r.player_id == 'p2' and r.request_type is RequestType.YES_NO
    decision = decide(PublicAttitude(), s.state, r)
    r.validate(decision.value)
    assert decision.value is wanted


def test_zhenlie_source_hand_choice_hides_ids_and_faces_after_reconnect():
    from sanguosha.multiplayer.room import MultiplayerRoom
    s = setup('xun_you')
    s.state.players['p2'].granted_skills['zhenlie'] = 'audit-grant'
    hidden = put(s, 'basic.slash')
    card = put(s, 'trick.duel')
    s.engine.start_action(UseCardAction('audit-zhenlie-private', 'p1', card, ('p2',)))
    answer(s, True)
    s = restore(s)
    r = s.engine.pending_request
    assert r.request_type is RequestType.CHOOSE_CARD
    room = MultiplayerRoom()
    room.session = s
    before = room._request_payload(r)
    assert hidden not in str(before)
    old = s.state.cards[hidden]
    s.state.cards[hidden] = replace(old, definition_id='basic.peach', suit=Suit.DIAMOND, rank=13)
    assert room._request_payload(r) == before
