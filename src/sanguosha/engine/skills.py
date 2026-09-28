"""Registered skills and explicit active/cross-player skill actions."""
from dataclasses import dataclass

from sanguosha.content.characters.standard import STANDARD_25_GENERAL_POOL as CHARACTERS, STANDARD_SKILL_CATALOGUE as SKILLS
from sanguosha.model.enums import Identity, Phase, Color, Kingdom, EquipmentSlot, Suit
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard
from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .deck import DrawCardsAction
from .military_basics import SlashSequence, MilitaryStrike
from .requests import PendingRequest, RequestType
from .response import RespondWithCardAction
from .recovery import RecoverAction
from .card_rules import InvalidCardUse
from .hp import LoseHpAction
from .judgment import JudgmentAction, JudgmentPattern


class SkillRegistry:
    def __init__(self):
        self.characters = {character.id: character for character in CHARACTERS}
        self.skills = {skill.id: skill for skill in SKILLS}

    def has(self, state, player_id, skill_id):
        character = self.characters.get(state.players[player_id].character_id)
        if character is None or skill_id not in character.skill_ids:
            return False
        skill = self.skills[skill_id]
        return not skill.metadata.get('lord') or state.players[player_id].identity is Identity.LORD

    def faction(self, state, player_id):
        character = self.characters.get(state.players[player_id].character_id)
        return character.kingdom if character else None

    def gender(self, state, player_id):
        character = self.characters.get(state.players[player_id].character_id)
        return character.gender if character else None

    def allies(self, state, player_id, faction):
        start = state.seat_order.index(player_id)
        order = state.seat_order[start+1:] + state.seat_order[:start]
        return tuple(pid for pid in order if state.players[pid].is_alive and self.faction(state, pid) is faction)

    def red_slash_materials(self, state, player_id):
        if not self.has(state, player_id, 'wusheng'):
            return ()
        return tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                     if state.cards[cid].color is Color.RED)


class FinishSkillBody:
    """Optional end-phase draw through the normal decision and draw actions."""

    def __init__(self, skills, base=None):
        self.skills = skills
        self.base = base

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 1:
            if self.base is not None:
                self.base.step(state, frame)
            if not self.skills.has(state, actor, 'biyue') or not state.players[actor].is_alive:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(frame.action.action_id + ':biyue', actor,
                RequestType.YES_NO, '是否发动【闭月】摸一张牌？', frame.action.action_id, frame.frame_id))
        if frame.step_index == 2:
            choice = frame.decision
            frame.decision = None
            if not choice:
                return StepResult.complete()
            frame.step_index = 3
            return StepResult.push(DrawCardsAction(frame.action.action_id + ':biyue-draw', actor, 1))
        return StepResult.complete(frame.child_result)


class PreparationSkillBody:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        actor = frame.action.player_id
        if not self.skills.has(state, actor, 'luoshen') or not state.players[actor].is_alive:
            return StepResult.complete()
        if frame.step_index == 1:
            frame.step_index = 2
            return StepResult.ask(PendingRequest(f'{frame.action.action_id}:luoshen:{frame.cursor}', actor,
                RequestType.YES_NO, '是否发动【洛神】进行黑色判定？',
                frame.action.action_id, frame.frame_id))
        if frame.step_index == 2:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 3
            return StepResult.push(JudgmentAction(f'{frame.action.action_id}:luoshen-judge:{frame.cursor}',
                actor, JudgmentPattern(color=Color.BLACK), gain_on_match=True))
        if frame.step_index == 3 and frame.child_result is True:
            frame.cursor += 1
            frame.step_index = 1
            return StepResult.continue_()
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class LianyingAction(Action):
    player_id: str


class LianyingHandler:
    def step(self, state, frame):
        action = frame.action
        if not state.players[action.player_id].is_alive:
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':choice', action.player_id,
                RequestType.YES_NO, '失去最后一张手牌，是否发动【连营】摸一张牌？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1 and frame.decision is True:
            frame.decision = None
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(action.action_id + ':draw', action.player_id, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class XiaojiAction(Action):
    player_id: str
    lost_count: int


class XiaojiHandler:
    def step(self, state, frame):
        action = frame.action
        if not state.players[action.player_id].is_alive:
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':choice', action.player_id,
                RequestType.YES_NO, f'失去 {action.lost_count} 张装备，是否发动【枭姬】摸牌？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1 and frame.decision is True:
            frame.decision = None
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(action.action_id + ':draw', action.player_id,
                                                   2 * action.lost_count))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class GanglieAction(Action):
    owner_id: str
    source_id: str


class GanglieHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', action.owner_id,
                RequestType.YES_NO, '受到伤害后，是否发动【刚烈】判定？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not state.players[action.source_id].is_alive:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.push(JudgmentAction(action.action_id + ':judge', action.owner_id,
                                                   JudgmentPattern(suit=Suit.HEART)))
        if frame.step_index == 2:
            if frame.child_result is True or not state.players[action.source_id].is_alive:
                return StepResult.complete()
            hand = state.cards_in(ZoneRef(ZoneType.HAND, action.source_id))
            if len(hand) < 2:
                return self._damage(frame)
            frame.step_index = 3
            return StepResult.ask(PendingRequest(action.action_id + ':source-choice', action.source_id,
                RequestType.CHOOSE_OPTION, '刚烈：弃两张手牌或受到一点伤害',
                action.action_id, frame.frame_id, choices=('discard', 'damage')))
        if frame.step_index == 3:
            choice = frame.decision
            frame.decision = None
            if choice == 'damage':
                return self._damage(frame)
            hand = state.cards_in(ZoneRef(ZoneType.HAND, action.source_id))
            if len(hand) < 2:
                return self._damage(frame)
            frame.step_index = 4
            return StepResult.ask(PendingRequest(action.action_id + ':discard', action.source_id,
                RequestType.CHOOSE_CARDS, '刚烈：选择弃置两张手牌', action.action_id,
                frame.frame_id, eligible_card_ids=hand, min_count=2, max_count=2))
        if frame.step_index == 4:
            cards = tuple(frame.decision)
            frame.decision = None
            self.moves.move(state, CardMove(action.action_id + ':discard-move', cards,
                ZoneRef(ZoneType.HAND, action.source_id), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.DISCARD, action.source_id))
        return StepResult.complete()

    def _damage(self, frame):
        from .military_basics import MilitaryDamageAction
        action = frame.action
        frame.step_index = 5
        return StepResult.push(MilitaryDamageAction(action.action_id + ':damage',
                                                     action.owner_id, action.source_id, 1))


@dataclass(frozen=True, slots=True)
class TuxiAction(Action):
    player_id: str


class TuxiHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            candidates = tuple(pid for pid in state.seat_order if pid != action.player_id
                               and state.players[pid].is_alive
                               and state.cards_in(ZoneRef(ZoneType.HAND, pid)))
            if not candidates:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':targets', action.player_id,
                RequestType.CHOOSE_PLAYERS, '突袭：选择至多两名有手牌的其他角色',
                action.action_id, frame.frame_id, allowed_player_ids=candidates,
                min_count=1, max_count=min(2, len(candidates))))
        if frame.step_index == 1:
            frame.local['targets'] = '|'.join(frame.decision)
            frame.decision = None
            frame.cursor = 0
            frame.step_index = 2
        if frame.step_index == 3:
            target = str(frame.local['current_target'])
            card = frame.decision
            frame.decision = None
            hand = ZoneRef(ZoneType.HAND, target)
            if card in state.cards_in(hand):
                self.moves.move(state, CardMove(f'{action.action_id}:gain:{frame.cursor}', (card,),
                    hand, ZoneRef(ZoneType.HAND, action.player_id), CardMoveReason.SYSTEM,
                    action.player_id, action.action_id))
            frame.step_index = 2
        targets = str(frame.local['targets']).split('|') if frame.local['targets'] else []
        while frame.cursor < len(targets):
            target = targets[frame.cursor]
            frame.cursor += 1
            cards = state.cards_in(ZoneRef(ZoneType.HAND, target))
            if not state.players[target].is_alive or not cards:
                continue
            frame.local['current_target'] = target
            frame.step_index = 3
            return StepResult.ask(PendingRequest(f'{action.action_id}:card:{frame.cursor}',
                action.player_id, RequestType.CHOOSE_CARD, '突袭：选择目标的一张背面手牌',
                action.action_id, frame.frame_id, eligible_card_ids=cards,
                subject_player_id=target))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class YijiAction(Action):
    player_id: str
    damage_points: int


class YijiHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        hand = ZoneRef(ZoneType.HAND, owner)
        if frame.step_index == 0:
            frame.cursor = 0
            frame.step_index = 1
        if frame.step_index == 1:
            if frame.cursor >= action.damage_points or not state.players[owner].is_alive:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(f'{action.action_id}:offer:{frame.cursor}', owner,
                RequestType.YES_NO, f'第 {frame.cursor + 1} 点伤害：是否发动【遗计】摸两张牌并分配？',
                action.action_id, frame.frame_id))
        if frame.step_index == 2:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                frame.cursor += 1
                frame.step_index = 1
                return StepResult.continue_()
            frame.local['before_draw'] = '|'.join(state.cards_in(hand))
            frame.step_index = 3
            return StepResult.push(DrawCardsAction(f'{action.action_id}:draw:{frame.cursor}', owner, 2))
        if frame.step_index == 3:
            before = set(str(frame.local['before_draw']).split('|'))
            frame.local['new_cards'] = '|'.join(cid for cid in state.cards_in(hand) if cid not in before)
            frame.local['card_cursor'] = 0
            frame.step_index = 4
        if frame.step_index == 5:
            target = frame.decision
            frame.decision = None
            card = str(frame.local['current_card'])
            if target != owner and card in state.cards_in(hand) and state.players[target].is_alive:
                self.moves.move(state, CardMove(f'{action.action_id}:give:{frame.cursor}:{frame.local["card_cursor"]}',
                    (card,), hand, ZoneRef(ZoneType.HAND, target), CardMoveReason.SYSTEM,
                    owner, action.action_id))
            frame.local['card_cursor'] = int(frame.local['card_cursor']) + 1
            frame.step_index = 4
        if frame.step_index == 4:
            cards = str(frame.local['new_cards']).split('|') if frame.local['new_cards'] else []
            index = int(frame.local['card_cursor'])
            if index >= len(cards):
                frame.cursor += 1
                frame.step_index = 1
                return StepResult.continue_()
            card = cards[index]
            frame.local['current_card'] = card
            frame.step_index = 5
            return StepResult.ask(PendingRequest(f'{action.action_id}:recipient:{frame.cursor}:{index}',
                owner, RequestType.CHOOSE_PLAYER,
                f'【遗计】第 {index + 1} 张牌交给谁？选择自己则保留。',
                action.action_id, frame.frame_id,
                allowed_player_ids=tuple(pid for pid in state.seat_order if state.players[pid].is_alive)))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class KurouAction(Action):
    player_id: str


class KurouHandler:
    def __init__(self, skills):
        self.skills = skills

    def validate_start(self, state, action):
        if (not self.skills.has(state, action.player_id, 'kurou') or
                state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY or
                not state.players[action.player_id].is_alive):
            raise InvalidCardUse('苦肉不可用')

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':confirm', action.player_id,
                RequestType.YES_NO, '是否发动【苦肉】？失去一点体力后摸两张牌。',
                action.action_id, frame.frame_id))
        if frame.step_index == 1:
            choice = frame.decision
            frame.decision = None
            if not choice:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.push(LoseHpAction(action.action_id + ':lose-hp', action.player_id, 1))
        if frame.step_index == 2:
            if not state.players[action.player_id].is_alive:
                return StepResult.complete()
            frame.step_index = 3
            return StepResult.push(DrawCardsAction(action.action_id + ':draw', action.player_id, 2))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class QingnangAction(Action):
    player_id: str


class QingnangHandler:
    def __init__(self, skills, moves):
        self.skills, self.moves = skills, moves

    def validate_start(self, state, action):
        usage = state.play_usage
        if (not self.skills.has(state, action.player_id, 'qingnang') or
                state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY or
                usage is None or usage.count('skill.qingnang') or
                not state.cards_in(ZoneRef(ZoneType.HAND, action.player_id)) or
                not any(p.is_alive and p.hp < p.max_hp for p in state.players.values())):
            raise InvalidCardUse('青囊不可用')

    def step(self, state, frame):
        action = frame.action
        hand = ZoneRef(ZoneType.HAND, action.player_id)
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':card', action.player_id,
                RequestType.CHOOSE_CARD, '青囊：选择要弃置的手牌', action.action_id,
                frame.frame_id, eligible_card_ids=state.cards_in(hand)))
        if frame.step_index == 1:
            frame.local['card'] = frame.decision
            frame.decision = None
            targets = tuple(pid for pid in state.seat_order
                            if state.players[pid].is_alive and state.players[pid].hp < state.players[pid].max_hp)
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '青囊：选择受伤角色', action.action_id,
                frame.frame_id, allowed_player_ids=targets))
        if frame.step_index == 2:
            card_id, target = frame.local['card'], frame.decision
            if (card_id not in state.cards_in(hand) or not state.players[target].is_alive or
                    state.players[target].hp >= state.players[target].max_hp):
                raise InvalidCardUse('青囊材料或目标已失效')
            self.moves.move(state, CardMove(action.action_id + ':discard', (card_id,), hand,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, action.player_id))
            state.play_usage.record('skill.qingnang')
            frame.step_index = 3
            return StepResult.push(RecoverAction(action.action_id + ':recover', action.player_id, target, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class AllianceResponse(Action):
    lord_id: str
    required_definition_id: str
    source_action_id: str
    faction: Kingdom


class AllianceResponseHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        action = frame.action
        allies = self.skills.allies(state, action.lord_id, action.faction)
        if frame.step_index == 1:
            if frame.child_result is not None:
                return StepResult.complete(frame.child_result)
            frame.step_index = 0
        if frame.cursor >= len(allies):
            return StepResult.complete()
        ally = allies[frame.cursor]
        frame.cursor += 1
        frame.step_index = 1
        return StepResult.push(RespondWithCardAction(
            f'{action.action_id}:ally:{frame.cursor}', ally, action.required_definition_id,
            action.source_action_id, f'是否为同势力主公提供【{"闪" if action.required_definition_id == "basic.dodge" else "杀"}】？',
            action.lord_id))


@dataclass(frozen=True, slots=True)
class RendeAction(Action):
    player_id: str


class RendeHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        hand = ZoneRef(ZoneType.HAND, action.player_id)
        if frame.step_index == 0:
            if state.current_phase is not Phase.PLAY or state.current_player_id != action.player_id or not state.cards_in(hand):
                raise InvalidCardUse('仁德不可用')
            frame.step_index = 1
            cards = state.cards_in(hand)
            return StepResult.ask(PendingRequest(action.action_id+':cards', action.player_id,
                RequestType.CHOOSE_CARDS, '仁德：选择要交出的手牌', action.action_id, frame.frame_id,
                eligible_card_ids=cards, min_count=1, max_count=len(cards)))
        if frame.step_index == 1:
            frame.local['cards'] = tuple(frame.decision)
            frame.decision = None
            frame.step_index = 2
            targets = tuple(pid for pid in state.seat_order if pid != action.player_id and state.players[pid].is_alive)
            return StepResult.ask(PendingRequest(action.action_id+':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '仁德：选择获得手牌的角色', action.action_id, frame.frame_id,
                allowed_player_ids=targets))
        if frame.step_index == 2:
            target = frame.decision
            cards = frame.local['cards']
            if target == action.player_id or not state.players[target].is_alive or any(cid not in state.cards_in(hand) for cid in cards):
                raise InvalidCardUse('仁德目标或手牌已失效')
            self.moves.move(state, CardMove(action.action_id+':give', cards, hand,
                ZoneRef(ZoneType.HAND,target), CardMoveReason.SYSTEM, action.player_id))
            usage = state.play_usage
            before = usage.count('skill.rende.cards')
            for _ in cards:
                usage.record('skill.rende.cards')
            frame.step_index = 3
            if before < 2 <= usage.count('skill.rende.cards') and state.players[action.player_id].hp < state.players[action.player_id].max_hp:
                return StepResult.push(RecoverAction(action.action_id+':heal', action.player_id, action.player_id, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class ZhihengAction(Action):
    player_id: str


class ZhihengHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        usage = state.play_usage
        if frame.step_index == 0:
            if state.current_phase is not Phase.PLAY or state.current_player_id != action.player_id or usage.count('skill.zhiheng'):
                raise InvalidCardUse('制衡本阶段已用或不可用')
            cards = tuple(cid for ref, zone in state.zones.items() if ref.player_id == action.player_id
                          and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT) for cid in zone.card_ids)
            if not cards:
                raise InvalidCardUse('制衡无可弃牌')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id+':cards', action.player_id,
                RequestType.CHOOSE_CARDS, '制衡：选择要弃置的牌', action.action_id, frame.frame_id,
                eligible_card_ids=cards, min_count=1, max_count=len(cards)))
        if frame.step_index == 1:
            cards = tuple(frame.decision)
            usage.record('skill.zhiheng')
            for index, cid in enumerate(cards):
                ref = next(ref for ref, zone in state.zones.items() if cid in zone.card_ids)
                self.moves.move(state, CardMove(f'{action.action_id}:discard:{index}', (cid,), ref,
                    ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, action.player_id))
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(action.action_id+':draw', action.player_id, len(cards)))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class WushengUse(Action):
    player_id: str
    material_id: str


class WushengUseHandler:
    def __init__(self, skills, moves, slash_rule):
        self.skills, self.moves, self.slash_rule = skills, moves, slash_rule

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            limit = self.slash_rule.usage_limit(state,action.player_id)
            if (state.current_phase is not Phase.PLAY or state.current_player_id != action.player_id or
                    action.material_id not in self.skills.red_slash_materials(state,action.player_id) or
                    limit is not None and state.play_usage.count('basic.slash') >= limit):
                raise InvalidCardUse('武圣不可用')
            targets = self.slash_rule.target_candidates(state, action.player_id)
            if not targets:
                raise InvalidCardUse('武圣没有合法杀目标')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id+':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '武圣：请选择杀目标', action.action_id, frame.frame_id,
                allowed_player_ids=targets))
        if frame.step_index == 1:
            target = frame.decision
            self.slash_rule.validate_targets(state, action.player_id, (target,))
            card = state.cards[action.material_id]
            virtual = VirtualCard('basic.slash', (action.material_id,), card.suit, card.color)
            self.moves.move(state, CardMove(action.action_id+':processing', (action.material_id,),
                ZoneRef(ZoneType.HAND,action.player_id), ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.USE, action.player_id))
            state.play_usage.record('basic.slash')
            frame.step_index = 2
            return StepResult.push(SlashSequence(action.action_id+':slash', action.player_id,
                action.material_id, (target,), virtual))
        if action.material_id in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
            self.moves.move(state, CardMove(action.action_id+':discard', (action.material_id,),
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.USE, action.player_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class JijiangUse(Action):
    player_id: str


class JijiangUseHandler:
    def __init__(self, skills, slash_rule):
        self.skills, self.slash_rule = skills, slash_rule

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            limit = self.slash_rule.usage_limit(state,action.player_id)
            if (not self.skills.has(state,action.player_id,'jijiang') or state.current_phase is not Phase.PLAY or
                    state.play_usage.count('skill.jijiang.attempted') or
                    limit is not None and state.play_usage.count('basic.slash') >= limit):
                raise InvalidCardUse('激将不可用')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id+':target',action.player_id,
                RequestType.CHOOSE_PLAYER,'激将：选择杀目标',action.action_id,frame.frame_id,
                allowed_player_ids=self.slash_rule.target_candidates(state,action.player_id)))
        if frame.step_index == 1:
            target=frame.decision
            self.slash_rule.validate_targets(state,action.player_id,(target,))
            state.play_usage.record('skill.jijiang.attempted')
            frame.local['target']=target
            frame.step_index=2
            return StepResult.push(AllianceResponse(action.action_id+':allies',action.player_id,
                'basic.slash',action.action_id,Kingdom.SHU))
        if frame.step_index == 2:
            result=frame.child_result
            if result is None:
                return StepResult.complete()
            material=result.material_ids[0] if isinstance(result,VirtualCard) else result
            state.play_usage.record('basic.slash')
            frame.step_index=3
            return StepResult.push(MilitaryStrike(action.action_id+':strike',action.player_id,
                frame.local['target'],material,'basic.dodge',virtual_card=result if isinstance(result,VirtualCard) else None))
        return StepResult.complete()


class SkillPlayOptions:
    def __init__(self, base, skills, slash_rule):
        self.base, self.skills, self.slash_rule = base, skills, slash_rule
        self.validator = base.validator

    def spear_legal(self, state, pid):
        return self.base.spear_legal(state,pid)

    def options(self, state, pid):
        ordinary = self.base.options(state,pid)
        extra = []
        hand = state.cards_in(ZoneRef(ZoneType.HAND,pid))
        if self.skills.has(state,pid,'rende') and hand and any(state.players[q].is_alive for q in state.seat_order if q != pid):
            extra.append('skill:rende')
        if self.skills.has(state,pid,'zhiheng') and not state.play_usage.count('skill.zhiheng') and any(
                ref.player_id == pid and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT) and zone.card_ids
                for ref,zone in state.zones.items()):
            extra.append('skill:zhiheng')
        if self.skills.has(state,pid,'kurou'):
            extra.append('skill:kurou')
        if (self.skills.has(state,pid,'qingnang') and not state.play_usage.count('skill.qingnang') and hand
                and any(p.is_alive and p.hp < p.max_hp for p in state.players.values())):
            extra.append('skill:qingnang')
        limit = self.slash_rule.usage_limit(state,pid)
        slash_available = (limit is None or state.play_usage.count('basic.slash') < limit) and bool(self.slash_rule.target_candidates(state,pid))
        if slash_available:
            extra.extend(f'virtual:wusheng:{cid}' for cid in self.skills.red_slash_materials(state,pid))
            if self.skills.has(state,pid,'jijiang') and not state.play_usage.count('skill.jijiang.attempted') and self.skills.allies(state,pid,Kingdom.SHU):
                extra.append('skill:jijiang')
        return (*ordinary,*extra)

    def build_action(self, state, pid, option, aid):
        if option not in self.options(state,pid):
            raise InvalidCardUse('skill option is no longer legal')
        if option == 'skill:rende':
            return RendeAction(aid+':rende',pid)
        if option == 'skill:zhiheng':
            return ZhihengAction(aid+':zhiheng',pid)
        if option == 'skill:jijiang':
            return JijiangUse(aid+':jijiang',pid)
        if option == 'skill:kurou':
            return KurouAction(aid+':kurou', pid)
        if option == 'skill:qingnang':
            return QingnangAction(aid+':qingnang', pid)
        if option.startswith('virtual:wusheng:'):
            return WushengUse(aid+':wusheng',pid,option.split(':',2)[2])
        return self.base.build_action(state,pid,option,aid)
