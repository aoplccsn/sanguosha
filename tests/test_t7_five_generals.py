"""Five Standard-era skills through real stack requests and card zones."""
from dataclasses import replace

from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.dying import DyingAction
from sanguosha.engine.damage import DamageAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.skills import RendeAction, ZhihengAction, WushengUse, JijiangUse
from sanguosha.engine.view_as import UseSpear
from sanguosha.model.enums import Identity, Phase, Suit, EquipmentSlot
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow
from test_t6_military_basics import put


def skill_game(actor='p1'):
    session = GameSession.new_game(seed=6, military=True, five_generals=True)
    session.state.current_player_id = actor
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState(actor, 1)
    return session


def drive(session, chooser, limit=100):
    observed=[]
    for _ in range(limit):
        request=session.engine.pending_request
        if request is None:
            break
        observed.append(request)
        value=chooser(request)
        session.engine.submit_decision(Decision(request.request_id,request.player_id,value))
        session.state.__post_init__()
    assert session.engine.pending_request is None
    assert session.engine.stack.is_empty()
    return observed


def passive(request):
    if request.request_type is RequestType.YES_NO:
        return False
    if request.request_type is RequestType.RESPOND_WITH_CARD:
        return PASS_RESPONSE
    return request.timeout_value()


def test_registered_characters_and_lord_skills():
    s=skill_game()
    assert tuple(s.state.players[p].character_id for p in s.state.seat_order)==(
        'caocao','liubei','sunquan','lvbu','guanyu')
    assert s.state.players['p1'].max_hp==5
    assert s.state.players['p4'].max_hp==4
    assert s.skills.has(s.state,'p1','hujia')
    assert not s.skills.has(s.state,'p2','jijiang')


def test_jianxiong_gains_damage_card_and_can_decline():
    for activate in (True,False):
        s=skill_game('p2')
        slash=put(s,'basic.slash','p2')
        s.engine.start_action(UseCardAction('attack','p2',slash,('p1',)))
        seen=drive(s,lambda r: activate if '奸雄' in r.prompt else passive(r))
        assert any('奸雄' in r.prompt for r in seen)
        assert (slash in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))) is activate


def test_jianxiong_no_material_does_not_ask():
    s=skill_game('p2')
    s.engine.start_action(DamageAction('cardless','p2','p1',1))
    assert s.engine.pending_request is None
    assert s.state.players['p1'].hp==4


def test_ai_normally_accepts_jianxiong():
    s=skill_game('p2')
    slash=put(s,'basic.slash','p2')
    s.engine.start_action(UseCardAction('ai-jianxiong','p2',slash,('p1',)))
    while s.engine.pending_request and '奸雄' not in s.engine.pending_request.prompt:
        r=s.engine.pending_request
        s.engine.submit_decision(Decision(r.request_id,r.player_id,passive(r)))
    assert '奸雄' in s.engine.pending_request.prompt
    assert s.ai.decide(s.state,s.engine.pending_request).value is True


def test_jianxiong_collects_both_virtual_spear_materials():
    s=skill_game('p2')
    put(s,'equipment.weapon.serpent_spear','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    a=put(s,'basic.peach','p2')
    b=put(s,'basic.dodge','p2')
    s.engine.start_action(UseSpear('spear-jianxiong','p2'))
    drive(s,lambda r:(a,b) if r.request_type is RequestType.CHOOSE_CARDS else
        'p1' if r.request_type is RequestType.CHOOSE_PLAYER else
        True if '奸雄' in r.prompt else passive(r))
    assert all(cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')) for cid in (a,b))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_hujia_asks_wei_ally_for_dodge():
    s=skill_game()
    s.state.players['p2'].character_id='caocao'
    dodge=put(s,'basic.dodge','p2')
    s.engine.start_action(RespondWithCardAction('hujia','p1','basic.dodge','attack'))
    assert 'virtual:hujia' in s.engine.pending_request.eligible_card_ids
    seen=drive(s,lambda r: 'virtual:hujia' if r.player_id=='p1' else dodge if dodge in r.eligible_card_ids else passive(r))
    assert any(r.player_id=='p2' for r in seen)
    assert s.engine.last_result==dodge
    assert dodge in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_hujia_all_allies_pass_returns_no_dodge():
    s=skill_game()
    s.state.players['p2'].character_id='caocao'
    s.engine.start_action(RespondWithCardAction('hujia-pass','p1','basic.dodge','attack'))
    seen=drive(s,lambda r:'virtual:hujia' if r.player_id=='p1' else PASS_RESPONSE)
    assert any(r.player_id=='p2' for r in seen)
    assert s.engine.last_result is None


def test_rende_recovers_once_at_two_cards():
    s=skill_game('p2')
    s.state.players['p2'].hp=2
    first=put(s,'basic.slash','p2')
    second=put(s,'basic.dodge','p2')
    for index,cid in enumerate((first,second)):
        s.engine.start_action(RendeAction(f'rende:{index}','p2'))
        drive(s,lambda r: (cid,) if r.request_type is RequestType.CHOOSE_CARDS else 'p5')
    assert s.state.players['p2'].hp==3
    assert s.state.play_usage.count('skill.rende.cards')==2
    assert all(cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p5')) for cid in (first,second))
    third=put(s,'basic.peach','p2')
    s.engine.start_action(RendeAction('rende:third','p2'))
    drive(s,lambda r:(third,) if r.request_type is RequestType.CHOOSE_CARDS else 'p5')
    assert s.state.players['p2'].hp==3


def test_jijiang_active_uses_shu_ally_slash():
    s=skill_game('p2')
    s.state.players['p2'].identity=Identity.LORD
    slash=put(s,'basic.slash','p5')
    s.engine.start_action(JijiangUse('jijiang','p2'))
    seen=drive(s,lambda r: 'p3' if r.request_type is RequestType.CHOOSE_PLAYER else
        slash if slash in r.eligible_card_ids else passive(r))
    assert any(r.player_id=='p5' and r.required_definition_id=='basic.slash' for r in seen)
    assert s.state.players['p3'].hp==3
    assert s.state.play_usage.count('basic.slash')==1


def test_jijiang_declined_does_not_repeat_forever():
    s=skill_game('p2')
    s.state.players['p2'].identity=Identity.LORD
    s.engine.start_action(JijiangUse('jijiang-pass','p2'))
    drive(s,lambda r:'p3' if r.request_type is RequestType.CHOOSE_PLAYER else PASS_RESPONSE)
    assert s.state.play_usage.count('basic.slash')==0
    assert s.state.play_usage.count('skill.jijiang.attempted')==1


def test_zhiheng_discards_hand_and_equipment_draws_and_locks():
    s=skill_game('p3')
    hand=put(s,'basic.slash','p3')
    armor=put(s,'equipment.armor.vine','p3',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))
    s.engine.start_action(ZhihengAction('zhiheng','p3'))
    drive(s,lambda r: (hand,armor))
    assert s.state.play_usage.count('skill.zhiheng')==1
    assert armor in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))==before-1+2
    phase_handler=s.engine.registry.handler_for(PhaseAction('probe','p3',Phase.PLAY))
    assert 'skill:zhiheng' not in phase_handler.bodies.body_for(Phase.PLAY).provider.options(s.state,'p3')
    s.engine.start_action(PhaseAction('another-play','p3',Phase.PLAY))
    assert 'skill:zhiheng' in s.engine.pending_request.choices
    # A fresh phase has a new typed usage state; prior phase consumption does not persist.
    drive(s,lambda r:'end_play_phase')


def test_jiuyuan_dying_pipeline_bonus():
    s=skill_game('p3')
    s.state.players['p3'].identity=Identity.LORD
    s.state.players['p4'].character_id='sunquan'
    s.state.players['p3'].hp=0
    peach=put(s,'basic.peach','p4')
    s.engine.start_action(DyingAction('rescue','p3','p2'))
    drive(s,lambda r: peach if peach in r.eligible_card_ids else passive(r))
    assert s.state.players['p3'].hp==2


def test_jiuyuan_does_not_bonus_non_wu_rescue():
    s=skill_game('p3')
    s.state.players['p3'].identity=Identity.LORD
    s.state.players['p3'].hp=0
    peach=put(s,'basic.peach','p5')
    s.engine.start_action(DyingAction('non-wu-rescue','p3','p2'))
    drive(s,lambda r:peach if peach in r.eligible_card_ids else passive(r))
    assert s.state.players['p3'].hp==1


def test_wusheng_active_virtual_slash_keeps_single_instance():
    s=skill_game('p5')
    material=put(s,'basic.peach','p5')
    s.state.cards[material]=replace(s.state.cards[material],suit=Suit.HEART)
    s.engine.start_action(WushengUse('wusheng','p5',material))
    drive(s,lambda r: 'p4' if r.request_type is RequestType.CHOOSE_PLAYER else passive(r))
    assert s.state.players['p4'].hp==3
    assert material in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert len(s.state.cards)==160


def test_wushuang_slash_requires_two_dodges():
    for count,expected_hp in ((1,3),(2,4)):
        s=skill_game('p4')
        slash=put(s,'basic.slash','p4')
        dodges=[put(s,'basic.dodge','p5') for _ in range(count)]
        s.engine.start_action(UseCardAction('wushuang','p4',slash,('p5',)))
        seen=drive(s,lambda r: next((cid for cid in dodges if cid in r.eligible_card_ids),PASS_RESPONSE)
                   if r.request_type is RequestType.RESPOND_WITH_CARD else passive(r))
        assert sum(r.required_definition_id=='basic.dodge' and r.player_id=='p5' for r in seen)==2
        assert s.state.players['p5'].hp==expected_hp


def test_wushuang_duel_requires_two_slashes_and_wusheng_can_supply_them():
    s=skill_game('p4')
    duel=put(s,'trick.duel','p4')
    old=s.state.cards_in(ZoneRef(ZoneType.HAND,'p5'))
    CardMoveService(s.events).move(s.state,CardMove('clear-guanyu',old,
        ZoneRef(ZoneType.HAND,'p5'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    materials=[put(s,'basic.peach','p5') for _ in range(2)]
    for cid in materials:
        s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.HEART)
    s.engine.start_action(UseCardAction('duel','p4',duel,('p5',)))
    def choose(request):
        virtual=next((c for c in request.eligible_card_ids if isinstance(c,str) and c.startswith('virtual:wusheng:')),None)
        return virtual or passive(request)
    seen=drive(s,choose)
    assert sum(r.player_id=='p5' and r.required_definition_id=='basic.slash' for r in seen)==2
    assert all(cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for cid in materials)


def test_wusheng_still_obeys_slash_distance():
    s=skill_game('p5')
    material=put(s,'basic.peach','p5')
    s.state.cards[material]=replace(s.state.cards[material],suit=Suit.HEART)
    s.engine.start_action(WushengUse('range','p5',material))
    assert 'p2' not in s.engine.pending_request.allowed_player_ids
    drive(s,lambda r:'p4' if r.request_type is RequestType.CHOOSE_PLAYER else passive(r))


def test_crossbow_allows_repeated_wusheng_slashes():
    s=skill_game('p5')
    put(s,'equipment.weapon.crossbow','p5',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    cards=[put(s,'basic.peach','p5') for _ in range(2)]
    for cid in cards:
        s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.HEART)
    for index,cid in enumerate(cards):
        s.engine.start_action(WushengUse(f'crossbow:{index}','p5',cid))
        drive(s,lambda r:'p4' if r.request_type is RequestType.CHOOSE_PLAYER else passive(r))
    assert s.state.play_usage.count('basic.slash')==2


def test_qinggang_wushuang_does_not_offer_armor_for_second_dodge():
    s=skill_game('p4')
    put(s,'equipment.weapon.qinggang_sword','p4',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    put(s,'equipment.armor.eight_trigrams','p5',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    dodge=put(s,'basic.dodge','p5')
    slash=put(s,'basic.slash','p4')
    s.engine.start_action(UseCardAction('qinggang-wushuang','p4',slash,('p5',)))
    seen=drive(s,lambda r:dodge if dodge in r.eligible_card_ids else passive(r))
    assert sum('八卦阵' in r.prompt for r in seen)==0
    assert s.state.players['p5'].hp==3


def test_renwang_does_not_block_red_wusheng_slash():
    s=skill_game('p5')
    put(s,'equipment.armor.renwang_shield','p4',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    material=put(s,'basic.peach','p5')
    s.state.cards[material]=replace(s.state.cards[material],suit=Suit.HEART)
    s.engine.start_action(WushengUse('red-versus-renwang','p5',material))
    drive(s,lambda r:'p4' if r.request_type is RequestType.CHOOSE_PLAYER else passive(r))
    assert s.state.players['p4'].hp==3


def test_halberd_multi_target_wushuang_applies_per_target():
    s=skill_game('p4')
    put(s,'equipment.weapon.halberd','p4',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    old=s.state.cards_in(ZoneRef(ZoneType.HAND,'p4'))
    CardMoveService(s.events).move(s.state,CardMove('clear-lvbu',old,
        ZoneRef(ZoneType.HAND,'p4'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    slash=put(s,'basic.slash','p4')
    dodges=[put(s,'basic.dodge','p5') for _ in range(2)]
    s.engine.start_action(UseCardAction('halberd-wushuang','p4',slash,('p3','p5')))
    seen=drive(s,lambda r:next((cid for cid in dodges if cid in r.eligible_card_ids),PASS_RESPONSE)
        if r.request_type is RequestType.RESPOND_WITH_CARD else passive(r))
    assert s.state.players['p3'].hp==3
    assert s.state.players['p5'].hp==4
    assert sum(r.player_id=='p5' and r.required_definition_id=='basic.dodge' for r in seen)==2


def test_hujia_decline_and_armor_response_remain_legal():
    s=skill_game()
    s.state.players['p2'].character_id='caocao'
    put(s,'equipment.armor.eight_trigrams','p1',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.engine.start_action(RespondWithCardAction('armor-hujia','p1','basic.dodge','attack'))
    seen=drive(s,lambda r:False if r.request_type is RequestType.YES_NO else passive(r))
    assert any('八卦阵' in r.prompt for r in seen)
    assert any('virtual:hujia' in r.eligible_card_ids for r in seen)
    assert s.engine.last_result is None


def test_jijiang_can_answer_duel_slash_request():
    s=skill_game('p4')
    s.state.players['p2'].identity=Identity.LORD
    duel=put(s,'trick.duel','p4')
    ally_slash=put(s,'basic.slash','p5')
    s.engine.start_action(UseCardAction('duel-jijiang','p4',duel,('p2',)))
    seen=drive(s,lambda r:'virtual:jijiang' if r.player_id=='p2' and 'virtual:jijiang' in r.eligible_card_ids
        else ally_slash if ally_slash in r.eligible_card_ids else passive(r))
    assert any(r.player_id=='p5' and r.required_definition_id=='basic.slash' for r in seen)
    assert ally_slash in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_spear_and_wusheng_are_separate_slash_response_sources():
    s=skill_game('p5')
    put(s,'equipment.weapon.serpent_spear','p5',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    red=put(s,'basic.peach','p5')
    s.state.cards[red]=replace(s.state.cards[red],suit=Suit.HEART)
    s.engine.start_action(RespondWithCardAction('sources','p5','basic.slash','duel'))
    request=s.engine.pending_request
    assert 'virtual:spear' in request.eligible_card_ids
    assert f'virtual:wusheng:{red}' in request.eligible_card_ids
    drive(s,lambda r:f'virtual:wusheng:{red}')
    assert isinstance(s.engine.last_result,VirtualCard)
    assert s.engine.last_result.material_ids==(red,)


def test_gui_shows_character_skills_and_active_skill_button():
    s=skill_game('p2')
    s.human_id='p2'
    put(s,'basic.peach','p2')
    s.engine.start_action(PhaseAction('gui-skills','p2',Phase.PLAY))
    w=MainWindow()
    w.session=s
    w._render()
    assert '仁德' in w.table.panels['p2'].view.skill_labels[0]
    assert any(button.text()=='仁德' for button in w.decision.buttons)
    next(button for button in w.decision.buttons if button.text()=='仁德').click()
    assert s.engine.pending_request.request_type is RequestType.CHOOSE_CARDS
    assert '仁德' in w.decision.prompt_label.text()
    w.close()


def test_gui_wusheng_response_highlights_red_material():
    s=skill_game('p5')
    s.human_id='p5'
    red=put(s,'basic.peach','p5')
    s.state.cards[red]=replace(s.state.cards[red],suit=Suit.HEART)
    s.engine.start_action(RespondWithCardAction('gui-wusheng','p5','basic.slash','duel'))
    w=MainWindow()
    w.session=s
    w._render()
    assert w.hand.cards[str(red)]._selectable
    w._card_clicked(str(red))
    w._submit_value('ui.confirm_response')
    assert isinstance(s.engine.last_result,VirtualCard)
    w.close()
