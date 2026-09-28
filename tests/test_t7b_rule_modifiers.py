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
from sanguosha.engine.skills import KurouAction, QingnangAction
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
