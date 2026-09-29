"""First standard-character rules through shared engine legality paths."""

from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.events import CardRespondedEvent as RecordedResponse
from sanguosha.engine.events import TurnStartedEvent, CardUsedEvent, CardRespondedEvent
from sanguosha.engine.resolution import ResolutionFrame
from sanguosha.engine.requests import Decision, RequestType
from sanguosha.engine.skills import KurouAction, QingnangAction, JieyinAction, QixiUse, GuoseUse, FanjianAction, LijianAction, LongdanUse
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.enums import Phase
from sanguosha.model.enums import EquipmentSlot, Gender
from sanguosha.model.enums import Suit, Color
from dataclasses import replace
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from test_t6_military_basics import put
from test_t6_equipment_chains import gear, resolve, choose
import pytest


def rules_for(session):
    handler = session.engine.registry.handler_for(UseCardAction('lookup', 'p1', 'missing'))
    return handler.validator.rules


def test_guanxing_reorders_top_and_bottom_without_losing_cards():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.current_player_id = 'p1'
    session.state.players['p1'].character_id = 'zhugeliang'
    draw = ZoneRef(ZoneType.DRAW_PILE)
    original = session.state.cards_in(draw)
    session.engine.start_action(PhaseAction('guanxing-phase', 'p1', Phase.PREPARATION))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    for side, cid in [('top', original[2]), ('bottom', original[0]),
                      ('top', original[1]), ('bottom', original[3]), ('top', original[4])]:
        request = session.engine.pending_request
        assert f'{side}:{cid}' in request.choices
        session.engine.submit_decision(Decision(request.request_id, 'p1', f'{side}:{cid}'))
    assert session.engine.pending_request is None
    assert session.state.cards_in(draw) == (original[2], original[1], original[4],
                                             *original[5:], original[0], original[3])
    assert session.engine.stack.is_empty()


def test_guose_diamond_becomes_indulgence_until_judgment_then_reverts():
    from sanguosha.engine.military_tricks import ResolveDelayed
    from sanguosha.projection import project_for_human
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'daqiao'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    material = put(session, 'basic.peach', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.DIAMOND)
    session.engine.start_action(GuoseUse('guose-use', 'p1', material))
    request = session.engine.pending_request
    assert 'p2' in request.allowed_player_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    judgment = ZoneRef(ZoneType.JUDGMENT, 'p2')
    assert material in session.state.cards_in(judgment)
    assert session.state.cards[material].definition_id == 'basic.peach'
    assert 'p2' not in rules_for(session).get('delayed.indulgence').target_candidates(session.state, 'p1')
    view = project_for_human(session.state, session.definitions, 'p1', session.character_names)
    assert next(player for player in view.players if player.player_id == 'p2').judgments[0].name == '乐不思蜀'
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE)
    session.engine.start_action(ResolveDelayed('guose-resolve', 'p2', material))
    resolve(session)
    assert session.state.players['p2'].marks['skip_play'] == 1
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert material not in session.state.metadata['virtual_delayed_cards']


def test_paoxiao_removes_slash_count_limit_without_changing_range():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'zhangfei'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    slash = put(session, 'basic.slash', 'p1')
    rule = rules_for(session).get('basic.slash')
    assert rule.usage_limit(session.state, 'p1') is None
    assert 'p3' not in rule.target_candidates(session.state, 'p1')
    session.state.play_usage.record('basic.slash')
    handler = session.engine.registry.handler_for(UseCardAction('validate', 'p1', slash))
    assert handler.validator.validate_card(session.state, 'p1', slash) is rule


def test_mashu_uses_shared_distance_system():
    session = GameSession.new_game(military=True, five_generals=True)
    distance = DistanceSystem(session.definitions)
    assert distance.base_distance(session.state, 'p1', 'p3') == 2
    session.state.players['p1'].character_id = 'machao'
    assert distance.distance_between(session.state, 'p1', 'p3') == 1


def test_kongcheng_and_qianxun_restrict_engine_targets():
    session = GameSession.new_game(military=True, five_generals=True)
    rules = rules_for(session)
    session.state.players['p2'].character_id = 'zhugeliang'
    hand = ZoneRef(ZoneType.HAND, 'p2')
    cards = session.state.cards_in(hand)
    CardMoveService(session.events).move(session.state, CardMove('empty-p2', cards, hand,
        ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM, 'p2'))
    assert 'p2' not in rules.get('basic.slash').target_candidates(session.state, 'p1')
    assert 'p2' not in rules.get('trick.duel').target_candidates(session.state, 'p1')
    session.state.players['p2'].character_id = 'luxun'
    put(session, 'basic.peach', 'p2')
    assert 'p2' not in rules.get('trick.snatch').target_candidates(session.state, 'p1')
    assert 'p2' not in rules.get('delayed.indulgence').target_candidates(session.state, 'p1')


def test_qicai_removes_snatch_distance_restriction():
    session = GameSession.new_game(military=True, five_generals=True)
    rule = rules_for(session).get('trick.snatch')
    assert 'p3' not in rule.target_candidates(session.state, 'p1')
    session.state.players['p1'].character_id = 'huangyueying'
    assert 'p3' in rule.target_candidates(session.state, 'p1')


def test_yingzi_draw_and_biyue_optional_end_draw():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.current_player_id = 'p1'
    session.state.turn_number = 1
    session.state.players['p1'].character_id = 'zhouyu'
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    session.engine.start_action(PhaseAction('yingzi-phase', 'p1', Phase.DRAW))
    assert len(session.state.cards_in(hand)) - before == 3
    session.state.players['p1'].character_id = 'diaochan'
    before = len(session.state.cards_in(hand))
    session.engine.start_action(PhaseAction('biyue-phase', 'p1', Phase.FINISH))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO
    assert '闭月' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert len(session.state.cards_in(hand)) - before == 1
    assert session.engine.stack.is_empty()


def test_keji_only_offered_without_slash_use_or_response_this_turn():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'lvmeng'
    session.state.players['p1'].hp = 1
    session.events.record(TurnStartedEvent('turn-1', 'p1', 1))
    action = PhaseAction('discard-1', 'p1', Phase.DISCARD)
    body = session.engine.registry.handler_for(action).bodies.body_for(Phase.DISCARD)
    frame = ResolutionFrame('keji-frame', action, step_index=1)
    outcome = body.step(session.state, frame)
    assert outcome.request.request_type is RequestType.YES_NO
    assert '克己' in outcome.request.prompt
    frame.decision = True
    assert body.step(session.state, frame).value == 0

    slash = put(session, 'basic.slash', 'p1')
    session.events.record(CardUsedEvent('used-slash', 'p1', slash, ('p2',)))
    frame = ResolutionFrame('no-keji-use', action, step_index=1)
    assert body.step(session.state, frame).request.request_type is RequestType.CHOOSE_CARDS
    session.events.record(TurnStartedEvent('turn-2', 'p1', 2))
    session.events.record(CardRespondedEvent('responded-slash', 'p1', slash, 'duel', 'basic.slash'))
    frame = ResolutionFrame('no-keji-response', action, step_index=1)
    assert body.step(session.state, frame).request.request_type is RequestType.CHOOSE_CARDS


def test_jizhi_draws_before_non_delayed_trick_resolves():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'huangyueying'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    card = put(session, 'trick.ex_nihilo', 'p1')
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    session.engine.start_action(UseCardAction('jizhi-card', 'p1', card))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '集智' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    resolve(session)
    assert session.engine.stack.is_empty()
    assert len(session.state.cards_in(hand)) == before + 2  # cost one, 集智 one, 无中生有 two


def test_lianying_follows_real_loss_of_last_hand_card():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'luxun'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    hand = ZoneRef(ZoneType.HAND, 'p1')
    original = session.state.cards_in(hand)
    CardMoveService(session.events).move(session.state, CardMove('clear-for-lianying', original,
        hand, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM, 'p1'))
    card = put(session, 'trick.ex_nihilo', 'p1')
    session.engine.start_action(UseCardAction('last-card', 'p1', card))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '连营' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    resolve(session)
    assert len(session.state.cards_in(hand)) == 3  # 连营一张，无中生有两张


def test_xiaoji_triggers_from_equipment_zone_loss():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'sunshangxiang'
    session.state.current_player_id = 'p1'
    session.state.turn_number = 1
    card = gear(session, 'weapon.double_sword')
    equipment = ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON)
    moves = session.engine.registry.handler_for(PhaseAction('lookup', 'p1', Phase.DISCARD)).bodies.body_for(Phase.DISCARD).moves
    moves.move(session.state, CardMove('lose-equipment', (card,), equipment,
        ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM, 'p1'))
    before = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(PhaseAction('xiaoji-finish', 'p1', Phase.FINISH))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '枭姬' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert session.engine.stack.is_empty()
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 2


def test_fankui_takes_one_real_card_from_damage_source():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'simayi'
    source_card = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.engine.start_action(MilitaryDamageAction('fankui-hit', 'p1', 'p2', 1))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '反馈' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p2', True))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_CARD and source_card in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p2', source_card))
    assert source_card in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert source_card not in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert session.engine.stack.is_empty()


def test_luoyi_draws_one_and_adds_slash_damage_this_turn():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'xuchu'
    session.state.current_player_id = 'p1'
    session.state.turn_number = 1
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    session.engine.start_action(PhaseAction('luoyi-draw', 'p1', Phase.DRAW))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '裸衣' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert len(session.state.cards_in(hand)) == before + 1
    assert session.state.players['p1'].marks['luoyi'] == 1
    slash = put(session, 'basic.slash', 'p1')
    session.engine.start_action(MilitaryDamageAction('luoyi-hit', 'p1', 'p2', 1,
                                                     card_id=slash))
    assert session.state.players['p2'].hp == 2
    session.engine.start_action(PhaseAction('luoyi-finish', 'p1', Phase.FINISH))
    assert 'luoyi' not in session.state.players['p1'].marks


def test_qingguo_turns_black_hand_card_into_real_dodge_response():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'zhenji'
    material = put(session, 'basic.peach', 'p2')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.SPADE)
    session.engine.start_action(RespondWithCardAction('qingguo-response', 'p2',
        'basic.dodge', 'incoming-slash'))
    request = session.engine.pending_request
    choice = f'virtual:qingguo:{material}'
    assert choice in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p2', choice))
    assert material not in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert any(isinstance(event, RecordedResponse) and event.card_id == material
               and event.response_definition_id == 'basic.dodge' for event in session.events.events)
    assert session.engine.stack.is_empty()


def test_tiandu_obtains_own_resolved_judgment_card():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'guojia'
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    session.engine.start_action(JudgmentAction('tiandu-judge', 'p1', JudgmentPattern()))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '天妒' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert top in session.state.cards_in(hand)
    assert len(session.state.cards_in(hand)) == before + 1
    assert session.engine.stack.is_empty()


def test_guicai_replaces_revealed_card_before_judgment_result():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'simayi'
    old = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[old] = replace(session.state.cards[old], suit=Suit.SPADE)
    material = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.HEART)
    session.engine.start_action(JudgmentAction('guicai-judge', 'p1', JudgmentPattern(color=Color.RED)))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '鬼才' in request.prompt
    assert session.ai.decide(session.state, request).value is True
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    request = session.engine.pending_request
    assert material in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', material))
    assert old in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert any(getattr(event, 'event_type', '') == 'judgment_result'
               and event.metadata['card_id'] == material and event.metadata['matched']
               for event in session.events.events)
    assert session.engine.stack.is_empty()


def test_ganglie_failed_judgment_lets_source_take_damage():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'xiahou_dun'
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE)
    session.engine.start_action(MilitaryDamageAction('ganglie-incoming', 'p1', 'p2', 1))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '刚烈' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p2', True))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_OPTION
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'damage'))
    assert session.state.players['p2'].hp == 3
    assert session.state.players['p1'].hp == 4
    assert session.engine.stack.is_empty()


def test_ganglie_source_can_discard_two_hand_cards():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'xiahou_dun'
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE)
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    session.engine.start_action(MilitaryDamageAction('ganglie-discard', 'p1', 'p2', 1))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p2', True))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'discard'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_CARDS and request.min_count == 2
    session.engine.submit_decision(Decision(request.request_id, 'p1', request.eligible_card_ids[:2]))
    assert len(session.state.cards_in(hand)) == before - 2
    assert session.state.players['p1'].hp == 5
    assert session.engine.stack.is_empty()


def test_tuxi_replaces_draw_with_two_other_players_hand_cards():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'zhangliao'
    session.state.current_player_id = 'p1'
    session.state.turn_number = 1
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    deck_before = len(session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE)))
    stolen = (session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0],
              session.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))[0])
    session.engine.start_action(PhaseAction('tuxi-phase', 'p1', Phase.DRAW))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '突袭' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_PLAYERS and request.max_count == 2
    session.engine.submit_decision(Decision(request.request_id, 'p1', ('p2', 'p3')))
    for card in stolen:
        request = session.engine.pending_request
        assert request.request_type is RequestType.CHOOSE_CARD and card in request.eligible_card_ids
        session.engine.submit_decision(Decision(request.request_id, 'p1', card))
    assert len(session.state.cards_in(hand)) == before + 2
    assert all(card in session.state.cards_in(hand) for card in stolen)
    assert len(session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))) == deck_before
    assert session.engine.stack.is_empty()


def test_yiji_handles_each_damage_point_and_splits_drawn_cards():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'guojia'
    session.state.players['p2'].max_hp = 3
    session.state.players['p2'].hp = 3
    own_hand = ZoneRef(ZoneType.HAND, 'p2')
    ally_hand = ZoneRef(ZoneType.HAND, 'p1')
    own_before = len(session.state.cards_in(own_hand))
    ally_before = len(session.state.cards_in(ally_hand))
    session.engine.start_action(MilitaryDamageAction('yiji-hit', 'p1', 'p2', 2))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '遗计' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p2', True))
    first = session.engine.pending_request
    assert first.request_type is RequestType.CHOOSE_PLAYER
    session.engine.submit_decision(Decision(first.request_id, 'p2', 'p1'))
    second = session.engine.pending_request
    session.engine.submit_decision(Decision(second.request_id, 'p2', 'p2'))
    next_point = session.engine.pending_request
    assert next_point.request_type is RequestType.YES_NO and '第 2 点' in next_point.prompt
    session.engine.submit_decision(Decision(next_point.request_id, 'p2', False))
    assert len(session.state.cards_in(own_hand)) == own_before + 1
    assert len(session.state.cards_in(ally_hand)) == ally_before + 1
    assert session.state.players['p2'].hp == 1
    assert session.engine.stack.is_empty()


def test_luoshen_repeats_black_judgment_and_stops_on_red():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'zhenji'
    session.state.current_player_id = 'p1'
    session.state.turn_number = 1
    draw = ZoneRef(ZoneType.DRAW_PILE)
    black, red = session.state.cards_in(draw)[:2]
    session.state.cards[black] = replace(session.state.cards[black], suit=Suit.SPADE)
    session.state.cards[red] = replace(session.state.cards[red], suit=Suit.HEART)
    hand = ZoneRef(ZoneType.HAND, 'p1')
    session.engine.start_action(PhaseAction('luoshen-preparation', 'p1', Phase.PREPARATION))
    first = session.engine.pending_request
    assert first.request_type is RequestType.YES_NO and '洛神' in first.prompt
    session.engine.submit_decision(Decision(first.request_id, 'p1', True))
    second = session.engine.pending_request
    assert second.request_type is RequestType.YES_NO and '洛神' in second.prompt
    assert black in session.state.cards_in(hand)
    session.engine.submit_decision(Decision(second.request_id, 'p1', True))
    assert red in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert session.engine.stack.is_empty()


def test_jieyin_discards_two_and_recovers_both_once_per_play_phase():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'sunshangxiang'
    session.state.players['p1'].hp = 3
    session.state.players['p2'].hp = 2
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    session.engine.start_action(JieyinAction('jieyin-test', 'p1'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_CARDS and request.min_count == 2
    session.engine.submit_decision(Decision(request.request_id, 'p1', request.eligible_card_ids[:2]))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_PLAYER and 'p2' in request.allowed_player_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    assert len(session.state.cards_in(hand)) == before - 2
    assert session.state.players['p1'].hp == 4
    assert session.state.players['p2'].hp == 3
    assert session.state.play_usage.count('skill.jieyin') == 1
    assert session.engine.stack.is_empty()


def test_qixi_black_card_uses_real_dismantlement_resolution():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'ganning'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    material = put(session, 'basic.peach', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.SPADE)
    target_hand = ZoneRef(ZoneType.HAND, 'p2')
    before = len(session.state.cards_in(target_hand))
    session.engine.start_action(QixiUse('qixi-use', 'p1', material))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_PLAYER and 'p2' in request.allowed_player_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    resolve(session, choose)
    assert len(session.state.cards_in(target_hand)) == before - 1
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert any(getattr(event, 'virtual_definition_id', '') == 'trick.dismantlement'
               for event in session.events.events)


def test_fanjian_random_hand_card_is_given_and_wrong_guess_deals_damage():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'zhouyu'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    hand = ZoneRef(ZoneType.HAND, 'p1')
    original = session.state.cards_in(hand)
    CardMoveService(session.events).move(session.state, CardMove('clear-fanjian', original,
        hand, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM, 'p1'))
    material = put(session, 'basic.peach', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.HEART)
    session.engine.start_action(FanjianAction('fanjian-test', 'p1'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_PLAYER
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_OPTION and Suit.SPADE.value in request.choices
    session.engine.submit_decision(Decision(request.request_id, 'p2', Suit.SPADE.value))
    assert material in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert session.state.players['p2'].hp == 3
    assert session.state.play_usage.count('skill.fanjian') == 1
    assert session.engine.stack.is_empty()


@pytest.mark.parametrize('zone,slot', [
    (ZoneType.HAND, None), (ZoneType.EQUIPMENT, EquipmentSlot.WEAPON),
])
def test_jijiu_red_hand_or_equipment_responds_as_peach_outside_turn(zone, slot):
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'huatuo'
    session.state.current_player_id = 'p1'
    material = put(session, 'basic.slash' if zone is ZoneType.HAND else 'equipment.weapon.double_sword',
                   'p2', zone, slot)
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.HEART)
    session.engine.start_action(RespondWithCardAction('jijiu-response', 'p2', 'basic.peach',
                                                      'dying-save', subject_player_id='p3'))
    request = session.engine.pending_request
    choice = f'virtual:jijiu:{material}'
    assert choice in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p2', choice))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert any(isinstance(event, CardRespondedEvent) and event.card_id == material
               and event.response_definition_id == 'basic.peach' for event in session.events.events)
    assert session.engine.stack.is_empty()


def test_lijian_discards_cost_and_starts_two_male_duel_without_counter_window():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'diaochan'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    target_hand = ZoneRef(ZoneType.HAND, 'p3')
    original = session.state.cards_in(target_hand)
    CardMoveService(session.events).move(session.state, CardMove('clear-lijian-target', original,
        target_hand, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM, 'p3'))
    cost = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.engine.start_action(LijianAction('lijian-test', 'p1'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_CARD and cost in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', cost))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_PLAYERS
    session.engine.submit_decision(Decision(request.request_id, 'p1', ('p2', 'p3')))
    assert session.engine.pending_request.request_type is RequestType.RESPOND_WITH_CARD
    assert session.engine.pending_request.player_id == 'p3'
    resolve(session)
    assert cost in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert session.state.players['p3'].hp == 3
    assert session.state.play_usage.count('skill.lijian') == 1
    assert session.engine.stack.is_empty()


@pytest.mark.parametrize('suit,can_dodge', [(Suit.HEART, False), (Suit.SPADE, True)])
def test_tieqi_red_judgment_blocks_dodge_black_allows_it(suit, can_dodge):
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'machao'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    slash = put(session, 'basic.slash', 'p1')
    dodge = put(session, 'basic.dodge', 'p2')
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=suit)
    session.engine.start_action(UseCardAction('tieqi-slash', 'p1', slash, ('p2',)))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO and '铁骑' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    if can_dodge:
        request = session.engine.pending_request
        assert request.request_type is RequestType.RESPOND_WITH_CARD
        session.engine.submit_decision(Decision(request.request_id, 'p2', dodge))
        assert session.state.players['p2'].hp == 4
    else:
        assert session.engine.pending_request is None
        assert session.state.players['p2'].hp == 3
        assert dodge in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert session.engine.stack.is_empty()


def test_longdan_uses_dodge_as_slash_in_play_phase():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'zhaoyun'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    material = put(session, 'basic.dodge', 'p1')
    session.engine.start_action(LongdanUse('longdan-use', 'p1', material))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_PLAYER
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    resolve(session)
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert session.state.play_usage.count('basic.slash') == 1
    assert any(getattr(event, 'virtual_definition_id', '') == 'basic.slash'
               for event in session.events.events)


@pytest.mark.parametrize('required,material_definition', [
    ('basic.dodge', 'basic.slash'), ('basic.slash', 'basic.dodge'),
])
def test_longdan_responds_with_opposite_basic_card(required, material_definition):
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'zhaoyun'
    material = put(session, material_definition, 'p2')
    session.engine.start_action(RespondWithCardAction('longdan-response', 'p2', required, 'source'))
    request = session.engine.pending_request
    choice = f'virtual:longdan:{material}'
    assert choice in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p2', choice))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert any(isinstance(event, CardRespondedEvent) and event.card_id == material
               and event.response_definition_id == required for event in session.events.events)
    assert session.engine.stack.is_empty()

def test_double_sword_reads_character_gender_in_standard_mode():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].character_id = 'zhenji'
    session.state.players['p2'].max_hp = 3
    session.state.players['p2'].hp = 3
    assert session.skills.gender(session.state, 'p2') is Gender.FEMALE
    gear(session, 'weapon.double_sword')
    slash = put(session, 'basic.slash', 'p1')
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    session.engine.start_action(UseCardAction('gender-slash', 'p1', slash, ('p2',)))
    assert '雌雄双股剑' in session.engine.pending_request.prompt
    resolve(session, choose)
    assert session.engine.stack.is_empty()


def test_kurou_uses_hp_loss_and_can_enter_dying():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'huanggai'
    session.state.players['p1'].hp = 1
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    session.engine.start_action(KurouAction('kurou-test', 'p1'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert session.state.players['p1'].hp == 0
    resolve(session)
    assert not session.state.players['p1'].is_alive
    assert session.engine.stack.is_empty()


def test_qingnang_discards_real_card_recovers_and_is_once_per_phase():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'huatuo'
    session.state.players['p1'].max_hp = 3
    session.state.players['p1'].hp = 2
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    hand = ZoneRef(ZoneType.HAND, 'p1')
    card = session.state.cards_in(hand)[0]
    session.engine.start_action(QingnangAction('qingnang-test', 'p1'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_CARD
    session.engine.submit_decision(Decision(request.request_id, 'p1', card))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_PLAYER
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p1'))
    assert card in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert session.state.players['p1'].hp == 3
    assert session.state.play_usage.count('skill.qingnang') == 1
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(QingnangAction('qingnang-again', 'p1'))
