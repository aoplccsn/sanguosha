"""Classic Fire skills using the shared action stack and card services."""
from dataclasses import dataclass
from sanguosha.model.enums import Color, EquipmentSlot, Phase, Suit, Kingdom, Identity
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .deck import DrawCardsAction
from .distance import DistanceSystem
from .events import CardUsedEvent
from .hp import LoseHpAction
from .judgment import JudgmentAction, JudgmentPattern
from .military_basics import MilitaryDamageAction
from .pindian import PindianAction
from .recovery import RecoverAction
from .suits import effective_color, effective_suit
from .requests import PendingRequest, RequestType


@dataclass(frozen=True, slots=True)
class QiangxiAction(Action):
    player_id: str


class QiangxiHandler:
    def __init__(self, skills, moves, definitions):
        self.skills, self.moves, self.definitions = skills, moves, definitions
        self.distance = DistanceSystem(definitions)

    def targets(self, state, player_id, weapon_cost=None):
        if not state.players[player_id].is_alive:
            return ()
        equipped_weapon = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, player_id, EquipmentSlot.WEAPON))
        attack_range = (1 if weapon_cost in equipped_weapon
                        else self.distance.attack_range(state, player_id))
        return tuple(pid for pid in state.seat_order if pid != player_id
                     and state.players[pid].is_alive
                     and self.distance.distance_between(state, player_id, pid) <= attack_range)

    def weapons(self, state, player_id):
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == player_id
                     and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                     for cid in zone.card_ids
                     if self.definitions.get(state.cards[cid].definition_id).equipment_slot is EquipmentSlot.WEAPON
                     and self.targets(state, player_id, cid))

    def modes(self, state, player_id):
        result = []
        if self.targets(state, player_id):
            result.append('hp')
        if self.weapons(state, player_id):
            result.append('weapon')
        return tuple(result)

    def available(self, state, player_id):
        usage = state.play_usage
        return (self.skills.has(state, player_id, 'qiangxi')
                and state.current_player_id == player_id and state.current_phase is Phase.PLAY
                and usage is not None and usage.player_id == player_id
                and not usage.count('skill.qiangxi') and bool(self.modes(state, player_id)))

    def validate_start(self, state, action):
        if not self.available(state, action.player_id):
            raise InvalidCardUse('强袭当前不可发动')

    def _ask_target(self, state, frame):
        action = frame.action
        targets = self.targets(state, action.player_id, frame.local.get('cost'))
        if not targets:
            raise InvalidCardUse('强袭没有合法目标')
        frame.step_index = 3
        return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
            RequestType.CHOOSE_PLAYER, '强袭：选择攻击范围内的目标', action.action_id,
            frame.frame_id, allowed_player_ids=targets))

    def step(self, state, frame):
        action = frame.action
        player_id = action.player_id
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':cost-mode', player_id,
                RequestType.CHOOSE_OPTION, '强袭：选择失去体力或弃置武器', action.action_id,
                frame.frame_id, choices=self.modes(state, player_id)))
        if frame.step_index == 1:
            mode = frame.decision
            frame.decision = None
            if mode not in self.modes(state, player_id):
                raise InvalidCardUse('强袭代价不可用')
            frame.local['mode'] = mode
            if mode == 'weapon':
                frame.step_index = 2
                return StepResult.ask(PendingRequest(action.action_id + ':weapon', player_id,
                    RequestType.CHOOSE_CARD, '强袭：选择弃置的武器牌', action.action_id,
                    frame.frame_id, eligible_card_ids=self.weapons(state, player_id)))
            return self._ask_target(state, frame)
        if frame.step_index == 2:
            card_id = frame.decision
            frame.decision = None
            if card_id not in self.weapons(state, player_id):
                raise InvalidCardUse('强袭武器牌已不可用')
            frame.local['cost'] = card_id
            return self._ask_target(state, frame)
        if frame.step_index == 3:
            target = frame.decision
            frame.decision = None
            cost = frame.local.get('cost')
            if target not in self.targets(state, player_id, cost):
                raise InvalidCardUse('强袭目标已不可用')
            frame.local['target'] = target
            state.play_usage.record('skill.qiangxi')
            if frame.local['mode'] == 'hp':
                frame.step_index = 4
                return StepResult.push(LoseHpAction(action.action_id + ':lose-hp', player_id, 1))
            if cost not in self.weapons(state, player_id):
                raise InvalidCardUse('强袭武器牌已不可用')
            source = next(ref for ref, zone in state.zones.items() if cost in zone.card_ids)
            self.moves.move(state, CardMove(action.action_id + ':discard-weapon', (cost,), source,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, player_id))
            frame.step_index = 5
            return StepResult.push(MilitaryDamageAction(action.action_id + ':damage', player_id, target, 1))
        if frame.step_index == 4:
            if not state.players[player_id].is_alive or state.status is GameStatus.FINISHED:
                return StepResult.complete()
            frame.step_index = 5
            return StepResult.push(MilitaryDamageAction(action.action_id + ':damage',
                player_id, frame.local['target'], 1))
        return StepResult.complete(frame.child_result)


@dataclass(frozen=True, slots=True)
class QuhuAction(Action):
    player_id: str


class QuhuHandler:
    def __init__(self, skills, definitions):
        self.skills = skills
        self.distance = DistanceSystem(definitions)

    def targets(self, state, player_id):
        if not state.cards_in(ZoneRef(ZoneType.HAND, player_id)):
            return ()
        hp = state.players[player_id].hp
        return tuple(pid for pid in state.seat_order if pid != player_id
                     and state.players[pid].is_alive and state.players[pid].hp > hp
                     and state.cards_in(ZoneRef(ZoneType.HAND, pid)))

    def available(self, state, player_id):
        usage = state.play_usage
        return (self.skills.has(state, player_id, 'quhu')
                and state.current_player_id == player_id and state.current_phase is Phase.PLAY
                and usage is not None and usage.player_id == player_id
                and not usage.count('skill.quhu') and bool(self.targets(state, player_id)))

    def step(self, state, frame):
        action = frame.action
        source = action.player_id
        if frame.step_index == 0:
            if not self.available(state, source):
                raise InvalidCardUse('驱虎当前不可发动')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':opponent', source,
                RequestType.CHOOSE_PLAYER, '驱虎：选择体力值大于你的拼点角色',
                action.action_id, frame.frame_id, allowed_player_ids=self.targets(state, source)))
        if frame.step_index == 1:
            opponent = frame.decision
            frame.decision = None
            if opponent not in self.targets(state, source):
                raise InvalidCardUse('驱虎拼点对象已不可用')
            frame.local['opponent'] = opponent
            state.play_usage.record('skill.quhu')
            frame.step_index = 2
            return StepResult.push(PindianAction(action.action_id + ':pindian', source, opponent))
        opponent = frame.local['opponent']
        if frame.step_index == 2:
            if frame.child_result is not True:
                if not state.players[source].is_alive or not state.players[opponent].is_alive:
                    return StepResult.complete()
                frame.step_index = 4
                return StepResult.push(MilitaryDamageAction(action.action_id + ':lost',
                    opponent, source, 1))
            if not state.players[opponent].is_alive:
                return StepResult.complete()
            victims = tuple(pid for pid in state.seat_order if pid != opponent
                and state.players[pid].is_alive
                and self.distance.can_reach_with_slash(state, opponent, pid))
            if not victims:
                return StepResult.complete()
            frame.step_index = 3
            return StepResult.ask(PendingRequest(action.action_id + ':victim', source,
                RequestType.CHOOSE_PLAYER, '驱虎：选择其攻击范围内的受伤角色',
                action.action_id, frame.frame_id, allowed_player_ids=victims))
        if frame.step_index == 3:
            victim = frame.decision
            frame.decision = None
            if (victim == opponent or not state.players[victim].is_alive
                    or not self.distance.can_reach_with_slash(state, opponent, victim)):
                raise InvalidCardUse('驱虎伤害目标已不可用')
            frame.step_index = 4
            return StepResult.push(MilitaryDamageAction(action.action_id + ':won',
                opponent, victim, 1))
        return StepResult.complete(frame.child_result)


@dataclass(frozen=True, slots=True)
class JiemingAction(Action):
    player_id: str
    damage_points: int


class JiemingHandler:
    def step(self, state, frame):
        action = frame.action
        owner = action.player_id
        if not state.players[owner].is_alive or frame.cursor >= action.damage_points:
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                f'{action.action_id}:offer:{frame.cursor}', owner, RequestType.YES_NO,
                '节命：是否令一名角色补牌至体力上限（最多五张）？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                frame.cursor += 1
                frame.step_index = 0
                return StepResult.continue_()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                f'{action.action_id}:target:{frame.cursor}', owner, RequestType.CHOOSE_PLAYER,
                '节命：选择补牌角色', action.action_id, frame.frame_id,
                allowed_player_ids=tuple(pid for pid in state.seat_order
                    if state.players[pid].is_alive)))
        if frame.step_index == 2:
            target = frame.decision
            frame.decision = None
            if target not in state.players or not state.players[target].is_alive:
                raise InvalidCardUse('节命目标已不可用')
            count = min(5, max(0, state.players[target].max_hp -
                len(state.cards_in(ZoneRef(ZoneType.HAND, target)))))
            frame.cursor += 1
            frame.step_index = 0
            if count:
                return StepResult.push(DrawCardsAction(
                    f'{action.action_id}:draw:{frame.cursor}', target, count))
            return StepResult.continue_()
        raise InvalidCardUse('节命步骤无效')


@dataclass(frozen=True, slots=True)
class NiepanAction(Action):
    player_id: str


class NiepanOffer:
    def __init__(self, skills):
        self.skills = skills

    def __call__(self, state, player_id, action_id):
        player = state.players[player_id]
        if (player.is_alive and player.hp <= 0
                and not player.marks.get('niepan_used')
                and self.skills.has(state, player_id, 'niepan')):
            return NiepanAction(action_id + ':niepan', player_id)
        return None


class FirstDyingOffer:
    def __init__(self, *offers):
        self.offers = offers

    def __call__(self, state, player_id, action_id):
        for offer in self.offers:
            action = offer(state, player_id, action_id)
            if action is not None:
                return action
        return None


class NiepanHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        player_id = action.player_id
        player = state.players[player_id]
        if frame.step_index == 0:
            if not player.is_alive or player.hp > 0 or player.marks.get('niepan_used'):
                return StepResult.complete(False)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', player_id,
                RequestType.YES_NO, '是否发动限定技【涅槃】？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete(False)
            player.marks['niepan_used'] = 1
            for ref, zone in tuple(state.zones.items()):
                if (ref.player_id == player_id
                        and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT, ZoneType.JUDGMENT)
                        and zone.card_ids):
                    self.moves.move(state, CardMove(action.action_id + ':clear:' + str(ref),
                        tuple(zone.card_ids), ref, ZoneRef(ZoneType.DISCARD_PILE),
                        CardMoveReason.DISCARD, player_id))
            player.face_up = True
            from .chaining import set_chained
            set_chained(state,player_id,False,getattr(self.moves,'skills',None))
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(action.action_id + ':draw', player_id, 3))
        if frame.step_index == 2:
            frame.step_index = 3
            amount = 3 - player.hp
            if amount > 0:
                return StepResult.push(RecoverAction(action.action_id + ':recover',
                    player_id, player_id, amount))
        return StepResult.complete(True)


@dataclass(frozen=True, slots=True)
class FireViewAsTrick(Action):
    player_id: str
    material_id: str
    skill_id: str


class FireViewAsTrickHandler:
    DEFINITIONS = {
        'lianhuan': 'trick.iron_chain',
        'huoji': 'trick.fire_attack',
        'shuangxiong': 'trick.duel',
    }

    def __init__(self, skills, moves, events, rules):
        self.skills, self.moves, self.events, self.rules = skills, moves, events, rules

    def materials(self, state, player_id, skill_id):
        hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
        if skill_id == 'lianhuan':
            return tuple(cid for cid in hand
                         if effective_suit(state, cid, player_id) is Suit.CLUB)
        if skill_id == 'huoji':
            return tuple(cid for cid in hand
                         if effective_color(state, cid, player_id) is Color.RED)
        if skill_id == 'shuangxiong':
            judged = state.players[player_id].marks.get('shuangxiong_color')
            if judged not in (1, 2):
                return ()
            return tuple(cid for cid in hand if
                         (1 if effective_color(state, cid, player_id) is Color.RED else 2) != judged)
        return ()

    def available(self, state, player_id, skill_id, material_id=None):
        if skill_id not in self.DEFINITIONS or not self.skills.has(state, player_id, skill_id):
            return False
        usage = state.play_usage
        if (not state.players[player_id].is_alive or state.current_player_id != player_id
                or state.current_phase is not Phase.PLAY or usage is None
                or usage.player_id != player_id):
            return False
        materials = self.materials(state, player_id, skill_id)
        if not materials or material_id is not None and material_id not in materials:
            return False
        rule = self.rules.get(self.DEFINITIONS[skill_id])
        return skill_id == 'lianhuan' or (any(
            self.targets(state, player_id, skill_id, cid) for cid in materials)
            if material_id is None else bool(self.targets(
                state, player_id, skill_id, material_id)))

    def targets(self, state, player_id, skill_id, material_id):
        from .forest import weimu_blocks
        definition = self.DEFINITIONS[skill_id]
        rule = self.rules.get(definition)
        return tuple(pid for pid in rule.target_candidates(state, player_id)
                     if not weimu_blocks(state, pid, material_id, definition,
                                         player_id, self.skills))

    def step(self, state, frame):
        from .military_tricks import TrickAction
        action = frame.action
        player_id = action.player_id
        definition = self.DEFINITIONS.get(action.skill_id)
        if definition is None:
            raise InvalidCardUse('未知转化锦囊技能')
        rule = self.rules.get(definition)
        if frame.step_index == 0:
            if not self.available(state, player_id, action.skill_id, action.material_id):
                raise InvalidCardUse('转化锦囊当前不可用')
            low, high = rule.target_bounds(state, player_id, action.material_id)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':targets', player_id,
                RequestType.CHOOSE_PLAYERS if high > 1 else RequestType.CHOOSE_PLAYER,
                '选择转化锦囊目标；连环可选零名角色重铸', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, player_id,
                    action.skill_id, action.material_id),
                min_count=low, max_count=high))
        if frame.step_index == 1:
            choice = frame.decision
            frame.decision = None
            targets = tuple(choice) if isinstance(choice, tuple) else (choice,)
            if not self.available(state, player_id, action.skill_id, action.material_id):
                raise InvalidCardUse('转化锦囊材料已不可用')
            rule.validate_targets(state, player_id, targets)
            if any(pid not in self.targets(state, player_id, action.skill_id,
                                           action.material_id) for pid in targets):
                raise InvalidCardUse('帷幕阻止该转化锦囊目标')
            virtual = VirtualCard(definition, (action.material_id,),
                effective_suit(state, action.material_id, player_id),
                effective_color(state, action.material_id, player_id))
            self.moves.move(state, CardMove(action.action_id + ':processing',
                (action.material_id,), ZoneRef(ZoneType.HAND, player_id),
                ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.RECAST if not targets else CardMoveReason.USE, player_id, action.action_id))
            if targets:
                state.play_usage.record(definition)
                self.events.record(CardUsedEvent(action.action_id + ':used', player_id,
                    action.material_id, targets, virtual.definition_id, virtual_card=virtual))
            frame.step_index = 2
            return StepResult.push(TrickAction(action.action_id + ':trick', player_id,
                action.material_id, definition, targets, virtual))
        if action.material_id in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
            self.moves.move(state, CardMove(action.action_id + ':discard',
                (action.material_id,), ZoneRef(ZoneType.PROCESSING),
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.USE, player_id, action.action_id))
        return StepResult.complete(frame.child_result)


@dataclass(frozen=True, slots=True)
class ShuangxiongAction(Action):
    player_id: str


class ShuangxiongHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        action = frame.action
        pid = action.player_id
        if frame.step_index == 0:
            if (not self.skills.has(state, pid, 'shuangxiong')
                    or not state.players[pid].is_alive
                    or state.current_phase is not Phase.DRAW):
                return StepResult.complete(False)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', pid,
                RequestType.YES_NO, '是否发动【双雄】改为判定并获得判定牌？',
                action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete(False)
            state.players[pid].marks['skip_draw'] = 1
            frame.step_index = 2
            return StepResult.push(JudgmentAction(action.action_id + ':judgment', pid,
                JudgmentPattern(), gain_on_match=True, return_card_id=True))
        card_id = str(frame.child_result)
        state.players[pid].marks['shuangxiong_color'] = (
            1 if effective_color(state, card_id, pid) is Color.RED else 2)
        return StepResult.complete(card_id)


@dataclass(frozen=True, slots=True)
class LuanjiAction(Action):
    player_id: str
    card_ids: tuple[str, str]


class LuanjiHandler:
    def __init__(self, skills, moves, events):
        self.skills, self.moves, self.events = skills, moves, events

    def pairs(self, state, pid):
        from .card_limits import card_allowed
        from .military_tricks import MilitaryTrickRule
        if not MilitaryTrickRule('trick.archery_attack', None, self.skills).can_use(state, pid):
            return ()
        hand = state.cards_in(ZoneRef(ZoneType.HAND, pid))
        return tuple((a, b) for i, a in enumerate(hand) for b in hand[i+1:]
                     if effective_suit(state, a, pid) is effective_suit(state, b, pid)
                     and card_allowed(state, pid, (a, b)))

    def step(self, state, frame):
        from .military_tricks import TrickAction
        action = frame.action
        pid = action.player_id
        if frame.step_index == 0:
            if (not self.skills.has(state, pid, 'luanji')
                    or state.current_player_id != pid or state.current_phase is not Phase.PLAY
                    or len(action.card_ids) != 2 or len(set(action.card_ids)) != 2
                    or not any(set(action.card_ids) == set(pair) for pair in self.pairs(state, pid))):
                raise InvalidCardUse('乱击材料不可用')
            targets = tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive)
            if not targets:
                return StepResult.complete(False)
            for cid in action.card_ids:
                self.moves.move(state, CardMove(action.action_id + ':processing:' + cid,
                    (cid,), ZoneRef(ZoneType.HAND, pid), ZoneRef(ZoneType.PROCESSING),
                    CardMoveReason.USE, pid, action.action_id))
            virtual = VirtualCard('trick.archery_attack', action.card_ids,
                effective_suit(state, action.card_ids[0], pid),
                effective_color(state, action.card_ids[0], pid), 'luanji')
            state.play_usage.record('trick.archery_attack')
            self.events.record(CardUsedEvent(action.action_id + ':used', pid,
                action.card_ids[0], targets, 'trick.archery_attack', virtual_card=virtual))
            frame.step_index = 1
            return StepResult.push(TrickAction(action.action_id + ':trick', pid,
                action.card_ids[0], 'trick.archery_attack', targets, virtual))
        for cid in action.card_ids:
            if cid in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
                self.moves.move(state, CardMove(action.action_id + ':discard:' + cid, (cid,),
                    ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                    CardMoveReason.USE, pid, action.action_id))
        return StepResult.complete(frame.child_result)


class FireHandLimit:
    def __init__(self, base, skills,definitions=None):
        self.base, self.skills = base, skills
        self.definitions=definitions

    def __call__(self, state, player_id):
        value = self.base(state, player_id)
        if self.skills.has(state, player_id, 'juejing'):
            value += 2
        if (self.skills.has(state, player_id, 'xueyi')
                and state.players[player_id].identity is Identity.LORD):
            value += 2 * sum(1 for pid in state.seat_order if pid != player_id
                             and state.players[pid].is_alive
                             and self.skills.faction(state, pid) is Kingdom.QUN)
        from .remaining_gods import camp_bonus
        value += camp_bonus(state,player_id,self.skills)
        from .chaining import jieying_hand_bonus
        value += jieying_hand_bonus(state,player_id,self.skills)
        value -= int(state.players[player_id].marks.get('poxi_hand_limit')==state.turn_number)
        from .zhangliao import hand_penalty
        value -= hand_penalty(state,player_id,self.skills,self.definitions)
        return max(0,value)


def effective_armor(state, player_id, skills):
    physical = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, player_id, EquipmentSlot.ARMOR))
    if physical:
        return state.cards[physical[0]].definition_id
    if skills is not None and skills.has(state, player_id, 'bazhen'):
        return 'equipment.armor.eight_trigrams'
    return None


@dataclass(frozen=True, slots=True)
class TianyiAction(Action):
    player_id: str


class TianyiHandler:
    def __init__(self, skills):
        self.skills = skills

    def targets(self, state, player_id):
        return tuple(pid for pid in state.seat_order if pid != player_id
                     and state.players[pid].is_alive
                     and state.cards_in(ZoneRef(ZoneType.HAND, pid)))

    def available(self, state, player_id):
        usage = state.play_usage
        return (self.skills.has(state, player_id, 'tianyi')
                and state.current_player_id == player_id and state.current_phase is Phase.PLAY
                and usage is not None and usage.player_id == player_id
                and not usage.count('skill.tianyi')
                and bool(state.cards_in(ZoneRef(ZoneType.HAND, player_id)))
                and bool(self.targets(state, player_id)))

    def step(self, state, frame):
        action = frame.action
        player_id = action.player_id
        if frame.step_index == 0:
            if not self.available(state, player_id):
                raise InvalidCardUse('天义当前不可发动')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':opponent', player_id,
                RequestType.CHOOSE_PLAYER, '天义：选择拼点角色', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, player_id)))
        if frame.step_index == 1:
            opponent = frame.decision
            frame.decision = None
            if opponent not in self.targets(state, player_id):
                raise InvalidCardUse('天义拼点对象已不可用')
            state.play_usage.record('skill.tianyi')
            frame.step_index = 2
            return StepResult.push(PindianAction(action.action_id + ':pindian',
                player_id, opponent))
        won = frame.child_result is True
        marks = state.players[player_id].marks
        if won:
            marks['slash_quota_bonus'] = 1
            marks['slash_ignore_distance'] = 1
            marks['slash_extra_targets'] = 1
        else:
            marks['slash_prohibited'] = 1
        return StepResult.complete(won)


def mengjin_choices(state, target_id):
    hand = state.cards_in(ZoneRef(ZoneType.HAND, target_id))
    public = tuple(cid for ref, zone in state.zones.items()
                   if ref.player_id == target_id
                   and ref.zone_type in (ZoneType.EQUIPMENT, ZoneType.JUDGMENT)
                   for cid in zone.card_ids)
    return (tuple(f'hand:{index}' for index in range(len(hand)))
            + tuple(f'area:{cid}' for cid in public))


@dataclass(frozen=True, slots=True)
class MengjinAction(Action):
    source_id: str
    target_id: str


class MengjinHandler:
    def __init__(self, skills, moves):
        self.skills, self.moves = skills, moves

    def available(self, state, action):
        return (state.players[action.source_id].is_alive
                and state.players[action.target_id].is_alive
                and self.skills.has(state, action.source_id, 'mengjin')
                and bool(mengjin_choices(state, action.target_id)))

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            if not self.available(state, action):
                return StepResult.complete(False)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':offer', action.source_id,
                RequestType.YES_NO, '是否发动【猛进】弃置目标一张牌？',
                action.action_id, frame.frame_id, subject_player_id=action.target_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted or not self.available(state, action):
                return StepResult.complete(False)
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':card', action.source_id,
                RequestType.CHOOSE_OPTION, '猛进：选择目标的背面手牌位置或明置区域牌',
                action.action_id, frame.frame_id,
                choices=mengjin_choices(state, action.target_id),
                subject_player_id=action.target_id))
        choice = frame.decision
        frame.decision = None
        if choice not in mengjin_choices(state, action.target_id):
            raise InvalidCardUse('猛进目标牌已不可用')
        if choice.startswith('hand:'):
            source = ZoneRef(ZoneType.HAND, action.target_id)
            card_id = state.cards_in(source)[int(choice.split(':', 1)[1])]
        else:
            card_id = choice.split(':', 1)[1]
            source = next(ref for ref, zone in state.zones.items()
                          if ref.player_id == action.target_id and card_id in zone.card_ids)
        self.moves.move(state, CardMove(action.action_id + ':discard', (card_id,),
            source, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
            action.source_id, action.action_id))
        return StepResult.complete(str(card_id))

