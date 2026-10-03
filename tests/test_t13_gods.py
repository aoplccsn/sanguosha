"""Targeted classic God-general rule tests."""

from dataclasses import replace

from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.gods import WushenUse, WuhunDeathAction, ShelieAction, GongxinAction, QinyinAction, YeyanAction, GuixinAction
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.gods import QixingExchangeAction, StarWeatherAction, star_zone
from sanguosha.engine.rng import PythonRandomSource
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.projection import project_for_human
from sanguosha.model.enums import Identity
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import Phase, Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session


def test_wushen_heart_card_uses_real_slash_pipeline():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_guanyu'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card] = replace(state.cards[card], suit=Suit.HEART,
                                definition_id='basic.peach')
    session.engine.start_action(WushenUse('wushen', 'p1', card))
    request = session.engine.pending_request
    assert 'p3' in request.allowed_player_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p3'))
    for _ in range(20):
        request = session.engine.pending_request
        if request is None:
            break
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert state.play_usage.count('basic.slash') == 1
    assert card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_wushen_heart_card_can_respond_as_slash():
    from sanguosha.engine.response import RespondWithCardAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_guanyu'
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card] = replace(state.cards[card], suit=Suit.HEART,
                                definition_id='basic.peach')
    session.engine.start_action(RespondWithCardAction('wushen-response', 'p1',
                                                      'basic.slash', 'duel'))
    request = session.engine.pending_request
    option = f'virtual:wushen:{card}'
    assert option in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', option))
    assert card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_wuhun_nonpeach_judgment_kills_max_nightmare_target():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_guanyu'
    state.players['p2'].marks['nightmare'] = 2
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    state.cards[top] = replace(state.cards[top], definition_id='basic.slash')
    session.engine.start_action(WuhunDeathAction('wuhun-death', 'p1'))
    assert not state.players['p2'].is_alive


def test_wuhun_nightmare_mark_survives_snapshot():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_god_guanyu'
    session.state.players['p2'].marks['nightmare'] = 3
    restored = restore_session(snapshot_session(session))
    assert restored.state.players['p2'].marks['nightmare'] == 3


def test_shelie_replaces_draw_with_one_card_per_suit():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_lvmeng'
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:5]
    for cid, suit in zip(top, (Suit.HEART, Suit.HEART, Suit.CLUB,
                               Suit.DIAMOND, Suit.SPADE)):
        state.cards[cid] = replace(state.cards[cid], suit=suit)
    session.engine.start_action(ShelieAction('shelie', 'p1'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    for cid in (top[0], top[2], top[3], top[4]):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', cid))
    assert all(cid in state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
               for cid in (top[0], top[2], top[3], top[4]))
    assert top[1] in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert state.players['p1'].marks['skip_draw'] == 1


def test_gongxin_places_selected_heart_on_draw_top():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_lvmeng'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    heart = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[heart] = replace(state.cards[heart], suit=Suit.HEART)
    session.engine.start_action(GongxinAction('gongxin', 'p1'))
    for choice in ('p2', heart, 'top'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0] == heart
    assert state.play_usage.count('skill.gongxin') == 1


def test_gongxin_private_reveal_survives_reconnect_without_leaking():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_lvmeng'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[card] = replace(state.cards[card], suit=Suit.HEART)
    session.engine.start_action(GongxinAction('gongxin-privacy', 'p1'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    restored = restore_session(snapshot_session(session))
    owner = project_for_human(restored.state, restored.definitions, 'p1', restored.character_names)
    other = project_for_human(restored.state, restored.definitions, 'p3', restored.character_names)
    assert card in {view.card_id for view in owner.players[1].revealed_hand}
    assert not other.players[1].revealed_hand
    request = restored.engine.pending_request
    restored.engine.submit_decision(Decision(request.request_id, 'p1', 'done'))
    assert 'gongxin_reveal' not in restored.state.metadata


def test_qinyin_uses_recover_actions_for_all_living_players():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'fire_god_zhouyu'
    state.players['p2'].hp -= 1
    session.engine.start_action(QinyinAction('qinyin', 'p1'))
    for choice in (True, 'recover'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert state.players['p2'].hp == state.players['p2'].max_hp


def test_yeyan_small_deals_three_fire_damage_through_shared_pipeline():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'fire_god_zhouyu'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    before = {pid: state.players[pid].hp for pid in ('p2', 'p3', 'p4')}
    session.engine.start_action(YeyanAction('yeyan-small', 'p1'))
    for choice in ('small', ('p2', 'p3', 'p4')):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert all(state.players[pid].hp == before[pid] - 1 for pid in before)
    assert state.players['p1'].marks['yeyan_used'] == 1


def test_yeyan_great_pays_four_distinct_suits_and_hp():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'fire_god_zhouyu'
    player.max_hp = 6
    player.hp = 6
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    cards = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[:4]
    suits = (Suit.HEART, Suit.DIAMOND, Suit.CLUB, Suit.SPADE)
    for cid, suit in zip(cards, suits):
        state.cards[cid] = replace(state.cards[cid], suit=suit)
    session.engine.start_action(YeyanAction('yeyan-great', 'p1'))
    for choice in ('great', 'p2', 'p2', *cards):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert player.hp == 3
    assert state.players['p2'].hp == state.players['p2'].max_hp - 3
    assert set(cards) <= set(state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))


def test_guixin_gains_one_card_per_other_player_and_turns_over():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'forest_god_caocao'
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(GuixinAction('guixin', 'p1'))
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        choice = True if request.request_type.value == 'yes_no' else request.eligible_card_ids[0]
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 4
    assert not state.players['p1'].face_up


def test_feiying_increases_distance_to_god_cao_cao():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p3'].character_id = 'forest_god_caocao'
    distance = DistanceSystem()
    assert distance.distance_between(state, 'p1', 'p3') == 3
    state.players['p3'].disabled_skills.add('feiying')
    assert distance.distance_between(state, 'p1', 'p3') == 2


def test_guixin_triggers_once_per_damage_point():
    from sanguosha.engine.military_basics import MilitaryDamageAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'forest_god_caocao'
    state.players['p1'].max_hp = 5
    state.players['p1'].hp = 5
    session.engine.start_action(MilitaryDamageAction('damage-guixin', 'p2', 'p1', 2))
    offers = 0
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        if request.request_type.value == 'yes_no':
            offers += 1
            choice = False
        else:
            choice = request.timeout_value()
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert offers == 2
    assert state.players['p1'].hp == 3


def test_qixing_initial_stars_private_and_exchange_reconnect_safe():
    ids = tuple(f'p{i}' for i in range(1, 6))
    setup = Pregame(PythonRandomSource(9), dict(zip(ids,
        (Identity.LORD, Identity.LOYALIST, Identity.REBEL,
         Identity.REBEL, Identity.RENEGADE))), (), stage=SetupStage.COMPLETE,
        generals=dict(zip(ids, ('fire_god_zhugeliang', 'caocao', 'liubei',
                                 'sunquan', 'guanyu'))))
    session = GameSession.new_game(military=True, setup=setup)
    state = session.state
    stars = state.cards_in(star_zone('p1'))
    assert len(stars) == 7
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == 4
    owner = project_for_human(state, session.definitions, 'p1', session.character_names)
    other = project_for_human(state, session.definitions, 'p2', session.character_names)
    assert owner.players[0].special_piles['star'][0].card_id == stars[0]
    assert all(card.card_id != star for card in other.players[0].special_piles['star'] for star in stars)
    hand = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.engine.start_action(QixingExchangeAction('qixing', 'p1'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', (hand,)))
    restored = restore_session(snapshot_session(session))
    request = restored.engine.pending_request
    restored.engine.submit_decision(Decision(request.request_id, 'p1', (stars[0],)))
    assert hand in restored.state.cards_in(star_zone('p1'))
    assert stars[0] in restored.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))


def test_star_weather_modifies_fire_and_prevents_non_thunder_damage():
    ids = tuple(f'p{i}' for i in range(1, 6))
    setup = Pregame(PythonRandomSource(10), dict(zip(ids,
        (Identity.LORD, Identity.LOYALIST, Identity.REBEL,
         Identity.REBEL, Identity.RENEGADE))), (), stage=SetupStage.COMPLETE,
        generals=dict(zip(ids, ('fire_god_zhugeliang', 'caocao', 'liubei',
                                 'sunquan', 'guanyu'))))
    session = GameSession.new_game(military=True, setup=setup)
    state = session.state
    stars = state.cards_in(star_zone('p1'))
    session.engine.start_action(StarWeatherAction('weather', 'p1'))
    for choice in ('wind', ('p2',), (stars[0],), 'fog', ('p3',), (stars[1],)):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert state.players['p2'].marks['wind:p1'] == 1
    assert state.players['p3'].marks['fog:p1'] == 1
    from sanguosha.engine.military_basics import MilitaryDamageAction
    from sanguosha.model.enums import DamageNature
    session.engine.start_action(MilitaryDamageAction('weather-fire', 'p4', 'p2', 1, DamageNature.FIRE))
    assert state.players['p2'].hp == state.players['p2'].max_hp - 2
    session.engine.start_action(MilitaryDamageAction('weather-fog', 'p4', 'p3', 1))
    assert state.players['p3'].hp == state.players['p3'].max_hp


def test_wumou_pays_rage_before_non_delayed_trick_resolves():
    from sanguosha.engine.card_use import UseCardAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'forest_god_lvbu'
    state.players['p1'].marks['rage'] = 2
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card] = replace(state.cards[card], definition_id='trick.ex_nihilo')
    session.engine.start_action(UseCardAction('wumou-trick', 'p1', card))
    request = session.engine.pending_request
    assert request.choices == ('lose_hp', 'rage')
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'rage'))
    assert state.players['p1'].marks['rage'] == 1
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_juejing_draws_for_missing_hp_and_increases_hand_limit():
    from sanguosha.engine.phases import PhaseAction
    from sanguosha.engine.fire import FireHandLimit
    from sanguosha.engine.wind import WindHandLimit
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_god_zhaoyun'
    state.players['p1'].max_hp = 2
    state.players['p1'].hp = 1
    state.current_player_id = 'p1'
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(PhaseAction('juejing-draw', 'p1', Phase.DRAW))
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 3
    assert FireHandLimit(WindHandLimit(), session.skills)(state, 'p1') == 3


def test_longhun_response_uses_current_hp_same_suit_cards():
    from sanguosha.engine.response import RespondWithCardAction
    from sanguosha.engine.gods import longhun_option
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_god_zhaoyun'
    state.players['p1'].max_hp = 2
    state.players['p1'].hp = 2
    cards = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[:2]
    for cid in cards:
        state.cards[cid] = replace(state.cards[cid], suit=Suit.CLUB)
    session.engine.start_action(RespondWithCardAction(
        'longhun-dodge', 'p1', 'basic.dodge', 'attack'))
    request = session.engine.pending_request
    option = longhun_option(cards)
    assert option in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', option))
    assert all(cid in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for cid in cards)


def test_longhun_fire_slash_uses_shared_slash_pipeline():
    from sanguosha.engine.gods import LonghunUse
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_god_zhaoyun'
    state.players['p1'].max_hp = 2
    state.players['p1'].hp = 1
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card] = replace(state.cards[card], suit=Suit.DIAMOND)
    session.engine.start_action(LonghunUse('longhun-fire', 'p1', (card,), 'basic.fire_slash'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert state.play_usage.count('basic.slash') == 1
    assert card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_longhun_peach_is_offered_and_recovers():
    from sanguosha.engine.gods import LonghunUse
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_god_zhaoyun'
    state.players['p1'].max_hp = 2
    state.players['p1'].hp = 1
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card] = replace(state.cards[card], suit=Suit.HEART)
    session.engine.start_action(LonghunUse('longhun-peach', 'p1', (card,), 'basic.peach'))
    assert state.players['p1'].hp == 2
    assert card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_renjie_marks_damage_and_baiyin_awakens_once():
    from sanguosha.engine.military_basics import MilitaryDamageAction
    from sanguosha.engine.gods import BaiyinAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_god_simayi'
    session.engine.start_action(MilitaryDamageAction('renjie-damage', 'p2', 'p1', 2))
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert player.marks['ren'] == 2
    player.marks['ren'] = 4
    maximum = player.max_hp
    session.engine.start_action(BaiyinAction('baiyin', 'p1'))
    assert player.max_hp == maximum - 1
    assert player.granted_skills['jilue'] == 'baoyin'
    session.engine.start_action(BaiyinAction('baiyin-again', 'p1'))
    assert player.max_hp == maximum - 1


def test_lianpo_offers_extra_turn_after_kill_at_turn_end():
    from sanguosha.engine.death import DeathAction
    from sanguosha.engine.turns import TurnAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'mountain_god_simayi'
    state.current_player_id = 'p1'
    session.engine.start_action(DeathAction('lianpo-kill', 'p3', 'p1'))
    assert state.players['p1'].marks['lianpo_pending'] == 1
    session.engine.start_action(TurnAction('lianpo-turn', 'p1', (Phase.PREPARATION,)))
    request = session.engine.pending_request
    assert request is not None and request.player_id == 'p1'
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert state.extra_turn_queue == ['p1']


def test_jilue_zhiheng_spends_ren_and_uses_existing_handler():
    from sanguosha.engine.gods import JiluePlayAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_god_simayi'
    player.granted_skills['jilue'] = 'baoyin'
    player.marks['ren'] = 2
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.engine.start_action(JiluePlayAction('jilue-zhiheng', 'p1', 'zhiheng'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', (card,)))
    assert player.marks['ren'] == 1
    assert state.play_usage.count('skill.zhiheng') == 1


def test_jilue_wansha_temporary_skill():
    from sanguosha.engine.gods import JiluePlayAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_god_simayi'
    player.granted_skills['jilue'] = 'baoyin'
    player.marks['ren'] = 1
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    session.engine.start_action(JiluePlayAction('jilue-wansha', 'p1', 'wansha'))
    assert session.skills.has(state, 'p1', 'wansha')
    assert player.marks['ren'] == 0


def test_jilue_guicai_spends_ren_and_replaces_judgment():
    from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_god_simayi'
    player.granted_skills['jilue'] = 'baoyin'
    player.marks['ren'] = 1
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.engine.start_action(JudgmentAction('jilue-judge', 'p2', JudgmentPattern()))
    request = session.engine.pending_request
    assert request.player_id == 'p1'
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', card))
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert player.marks['ren'] == 0
    assert card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_jilue_jizhi_spends_ren_on_trick_use():
    from sanguosha.engine.card_use import UseCardAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_god_simayi'
    player.granted_skills['jilue'] = 'baoyin'
    player.marks['ren'] = 1
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card] = replace(state.cards[card], definition_id='trick.ex_nihilo')
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(UseCardAction('jilue-jizhi', 'p1', card))
    request = session.engine.pending_request
    assert '极略' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    while session.engine.pending_request is not None:
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert player.marks['ren'] == 0
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 2


def test_jilue_fangzhu_uses_existing_turnover_action():
    from sanguosha.engine.military_basics import MilitaryDamageAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_god_simayi'
    player.granted_skills['jilue'] = 'baoyin'
    player.marks['ren'] = 1
    session.engine.start_action(MilitaryDamageAction('jilue-fangzhu', 'p2', 'p1', 1))
    request = session.engine.pending_request
    assert '极略' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    assert not state.players['p2'].face_up
    assert player.marks['ren'] == 1


def test_renjie_counts_only_own_discard_phase_rule_discards():
    from sanguosha.engine.phases import PhaseAction
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'mountain_god_simayi'
    state.current_player_id = 'p1'
    state.players['p1'].hp = 1
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(PhaseAction('renjie-discard', 'p1', Phase.DISCARD))
    request = session.engine.pending_request
    assert request.request_type.value == 'choose_cards'
    session.engine.submit_decision(Decision(request.request_id, 'p1',
        tuple(request.eligible_card_ids[:before - 1])))
    assert player.marks['ren'] == before - 1


def test_all_eight_gods_finish_mixed_ai_games():
    groups = (
        ('wind_god_guanyu', 'wind_god_lvmeng', 'fire_god_zhouyu',
         'fire_god_zhugeliang', 'forest_god_caocao'),
        ('forest_god_lvbu', 'mountain_god_zhaoyun', 'mountain_god_simayi',
         'wind_god_guanyu', 'fire_god_zhouyu'),
    )
    for group in groups:
        session = GameSession.new_game(military=True, five_generals=True)
        for pid, character_id in zip(session.state.seat_order, group):
            player = session.state.players[pid]
            player.character_id = character_id
            player.max_hp = session.skills.characters[character_id].max_hp
            player.hp = player.max_hp
            if character_id == 'forest_god_lvbu':
                player.marks['rage'] = 2
        session.human_id = 'automated'
        session.pump_until_human_or_end(10000)
        assert session.state.status.value == 'finished'


def test_static_god_portraits_are_registered_for_web_and_pyside():
    import json
    from pathlib import Path
    from PySide6.QtGui import QImageReader
    from sanguosha.content.characters.standard import GOD_GENERAL_POOL
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'assets' / 'manifest.json').read_text(encoding='utf-8'))
    for character in GOD_GENERAL_POOL:
        asset = manifest[f'general.{character.id}']
        assert character.metadata['portrait_mode'] == 'static'
        assert QImageReader(str(root / 'assets' / asset)).canRead()
        assert (root / 'web' / 'public' / 'assets' / asset).is_file()


def test_ai_priority_does_not_read_hidden_opponent_identity():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    ai = session.ai
    before = ai._priority(state, 'p1', 'p3')
    state.players['p3'].identity = Identity.LOYALIST
    assert ai._priority(state, 'p1', 'p3') == before
    state.metadata['public_hostility_to_lord'] = {'p3': 2}
    assert ai._priority(state, 'p1', 'p3') > before
