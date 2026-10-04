from dataclasses import replace

import pytest
from sanguosha.session import GameSession
from sanguosha.engine.military_basics import MilitaryStrike, MilitaryDamageAction
from sanguosha.engine.yj2011 import PojunAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.engine.events import AfterDamageEvent
from sanguosha.model.enums import Color, DamageNature, EquipmentSlot, Suit
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.content.characters.standard import ALL_65_GENERAL_POOL
from test_t6_military_basics import put


def game():
    s = GameSession.new_game(military=True, five_generals=True)
    # Avoid unrelated optional triggers in these timing tests.
    for p in s.state.players.values():
        p.character_id = 'sunquan'
    return s


def answer(s, value):
    r = s.engine.pending_request
    s.engine.submit_decision(Decision(r.request_id, r.player_id, value))


def finish(s, offer=False):
    for _ in range(100):
        r = s.engine.pending_request
        if r is None:
            assert s.engine.stack.is_empty()
            return
        if r.request_type is RequestType.YES_NO:
            answer(s, offer if ':pojun:' in r.request_id else False)
        elif r.request_type is RequestType.RESPOND_WITH_CARD:
            answer(s, PASS_RESPONSE)
        else:
            raise AssertionError(r)
    raise AssertionError('resolution did not finish')


@pytest.mark.parametrize('suit,blocked', [(Suit.SPADE, True), (Suit.CLUB, True), (Suit.HEART, False), (Suit.DIAMOND, False)])
@pytest.mark.parametrize('definition', ['basic.slash','basic.fire_slash','basic.thunder_slash'])
def test_yizhong_effect_immunity_for_all_slash_colors(suit, blocked, definition):
    s=game(); s.state.players['p2'].character_id='yj2011_yu_jin'
    card=put(s, definition); s.state.cards[card]=replace(s.state.cards[card],suit=suit)
    hp=s.state.players['p2'].hp
    s.engine.start_action(MilitaryStrike('slash','p1','p2',card,'basic.dodge'))
    finish(s)
    assert s.state.players['p2'].hp == hp-int(not blocked)


def test_yizhong_armor_present_and_qinggang_does_not_disable_skill():
    s=game(); s.state.players['p2'].character_id='yj2011_yu_jin'
    card=put(s,'basic.slash'); s.state.cards[card]=replace(s.state.cards[card],suit=Suit.SPADE)
    put(s,'equipment.weapon.qinggang_sword','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    s.engine.start_action(MilitaryStrike('first','p1','p2',card,'basic.dodge')); finish(s)
    assert s.state.players['p2'].hp==4
    put(s,'equipment.armor.eight_trigrams','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.engine.start_action(MilitaryStrike('second','p1','p2',card,'basic.dodge')); finish(s)
    assert s.state.players['p2'].hp==3


def test_yizhong_colorless_virtual_slash_and_no_general_branch():
    s=game(); s.state.players['p2'].granted_skills['yizhong']='test-grant'
    card=put(s,'basic.slash')
    virtual=VirtualCard('basic.slash',(),None,None)
    s.engine.start_action(MilitaryStrike('virtual','p1','p2',card,'basic.dodge',virtual_card=virtual)); finish(s)
    assert s.state.players['p2'].hp==3


@pytest.mark.parametrize('hp,draw',[(1,1),(2,2),(4,4),(7,5)])
@pytest.mark.parametrize('accept',[False,True])
def test_pojun_chosen_text_draw_current_hp_then_turn(hp,draw,accept):
    s=game(); s.state.players['p1'].character_id='yj2011_xu_sheng'
    s.state.players['p2'].max_hp=max(4,hp); s.state.players['p2'].hp=hp
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    s.engine.start_action(PojunAction('pojun','p1','p2'))
    r=s.engine.pending_request
    assert r.player_id=='p1' and r.subject_player_id=='p2'
    s=restore_session(snapshot_session(s))
    assert s.engine.pending_request==r
    answer(s,accept); finish(s)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==before+(draw if accept else 0)
    assert s.state.players['p2'].face_up is (not accept)


def test_pojun_slash_damage_not_unrelated_damage_or_chain():
    s=game(); s.state.players['p1'].character_id='yj2011_xu_sheng'
    s.engine.start_action(MilitaryDamageAction('unrelated','p1','p2',1)); finish(s)
    assert s.state.players['p2'].face_up
    s.engine.start_action(MilitaryDamageAction('slash','p1','p3',1,card_kind='slash'))
    assert ':pojun:' in s.engine.pending_request.request_id
    answer(s,True); finish(s)
    assert not s.state.players['p3'].face_up


def test_pojun_waits_for_dying_and_does_not_offer_for_dead_target():
    s=game(); s.state.players['p1'].character_id='yj2011_xu_sheng'
    s.state.players['p2'].hp=1
    s.engine.start_action(MilitaryDamageAction('fatal','p1','p2',1,card_kind='slash'))
    assert ':pojun:' not in s.engine.pending_request.request_id
    finish(s,offer=True)
    assert not s.state.players['p2'].is_alive
    assert not any(':pojun:' in rid for rid in s.engine._seen_request_ids)


def test_development_metadata_is_not_production_draft():
    s=game()
    assert len(ALL_65_GENERAL_POOL)==65
    assert not any(str(g.id).startswith('yj2011') for g in ALL_65_GENERAL_POOL)
    assert s.skills.characters['yj2011_yu_jin'].metadata['playable']
    assert not s.skills.characters['yj2011_yu_jin'].metadata['development_only']
