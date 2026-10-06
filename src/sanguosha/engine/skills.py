"""Registered skills and explicit active/cross-player skill actions."""
from dataclasses import dataclass, replace
import json

from sanguosha.content.characters.standard import ALL_GENERAL_POOL as CHARACTERS, ALL_SKILL_CATALOGUE as SKILLS
from sanguosha.model.enums import Identity, Phase, Color, Kingdom, EquipmentSlot, Suit, Gender
from sanguosha.model.zones import ZoneRef, ZoneType, CardZone
from sanguosha.model.virtual_card import VirtualCard
from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .deck import DrawCardsAction
from .military_basics import SlashSequence, MilitaryStrike
from .requests import PendingRequest, RequestType
from .response import RespondWithCardAction
from .recovery import RecoverAction
from .card_rules import InvalidCardUse
from .hp import LoseHpAction
from .judgment import JudgmentAction, JudgmentPattern
from .events import CardUsedEvent, EventRecorder
from .suits import effective_color, effective_suit


class SkillRegistry:
    def __init__(self):
        self.characters = {character.id: character for character in CHARACTERS}
        self.skills = {skill.id: skill for skill in SKILLS}
        # Keep historical development snapshots loadable without overriding
        # accepted production metadata.
        from sanguosha.content.characters.yj2011 import YJ2011_DEV_GENERALS, YJ2011_DEV_SKILLS
        self.characters.update({c.id: c for c in YJ2011_DEV_GENERALS if c.id not in self.characters})
        self.skills.update({s.id: s for s in YJ2011_DEV_SKILLS if s.id not in self.skills})

        from sanguosha.content.characters.remaining import REMAINING_DEV_GENERALS, REMAINING_DEV_SKILLS
        self.characters.update({c.id: c for c in REMAINING_DEV_GENERALS if c.id not in self.characters})
        self.skills.update({s.id: s for s in REMAINING_DEV_SKILLS if s.id not in self.skills})

    def has(self, state, player_id, skill_id):
        player = state.players[player_id]
        if skill_id in player.disabled_skills:
            return False
        from .skill_leases import suppressed
        if suppressed(state,player_id,skill_id):return False
        character = self.characters.get(player.character_id)
        transformed = (skill_id == player.transformation_skill
                       and player.active_transformation in player.transformation_pool
                       and player.character_id == 'mountain_zuoci'
                       and 'huashen' not in player.disabled_skills)
        if skill_id == 'wushuang' and state.players[player_id].marks.get('wuwei', 0):
            return True
        if skill_id == 'wansha' and player.marks.get('jilue_wansha', 0):
            return True
        native = (character is not None and skill_id in character.skill_ids
                  and skill_id not in character.metadata.get('derived_skills', ()))
        if character is None or (not native
                                 and skill_id not in player.granted_skills
                                 and not transformed):
            return False
        skill = self.skills[skill_id]
        return not skill.metadata.get('lord') or state.players[player_id].identity is Identity.LORD

    def suppress_character_skills(self, state, player_id):
        player = state.players[player_id]
        character = self.characters.get(player.character_id)
        if character is None:
            return ()
        skills = tuple(dict.fromkeys((*character.skill_ids, *player.granted_skills,
                                      *((player.transformation_skill,)
                                        if player.transformation_skill else ()))))
        player.disabled_skills.update(skills)
        return skills

    def faction(self, state, player_id):
        player = state.players[player_id]
        transformed = (player.active_transformation if player.character_id == 'mountain_zuoci'
                       and 'huashen' not in player.disabled_skills else None)
        character = self.characters.get(transformed or player.character_id)
        return character.kingdom if character else None

    def gender(self, state, player_id):
        player = state.players[player_id]
        transformed = (player.active_transformation if player.character_id == 'mountain_zuoci'
                       and 'huashen' not in player.disabled_skills else None)
        character = self.characters.get(transformed or player.character_id)
        return character.gender if character else None

    def allies(self, state, player_id, faction):
        start = state.seat_order.index(player_id)
        order = state.seat_order[start+1:] + state.seat_order[:start]
        return tuple(pid for pid in order if state.players[pid].is_alive and self.faction(state, pid) is faction)

    def red_slash_materials(self, state, player_id):
        if not self.has(state, player_id, 'wusheng'):
            return ()
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == player_id and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                     for cid in zone.card_ids if effective_color(state, cid, player_id) is Color.RED)

    def emergency_peach_materials(self, state, player_id):
        if not self.has(state, player_id, 'jijiu') or state.current_player_id == player_id:
            return ()
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == player_id and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                     for cid in zone.card_ids if effective_color(state, cid, player_id) is Color.RED)


class FinishSkillBody:
    """Optional end-phase draw through the normal decision and draw actions."""

    def __init__(self, skills, base=None):
        self.skills = skills
        self.base = base

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 1:
            if not frame.local.get('liubei_jieying_offered') and self.skills.has(state,actor,'jieying_liubei'):
                from .remaining_gods import RemainingGodAction
                frame.local['liubei_jieying_offered']=True
                return StepResult.push(RemainingGodAction(frame.action.action_id+':jieying',actor,'jieying_liubei'))
            if not frame.local.get('camp_transfer_offered') and self.skills.has(state,actor,'jieying_ganning'):
                from .remaining_gods import RemainingGodAction
                frame.local['camp_transfer_offered']=True
                return StepResult.push(RemainingGodAction(frame.action.action_id+':camp-transfer',actor,'camptransfer'))
            if not frame.local.get('yj2013_zhiyan') and self.skills.has(state,actor,'zhiyan'):
                from .yj2013 import YJ2013Action
                frame.local['yj2013_zhiyan']=True
                return StepResult.push(YJ2013Action(frame.action.action_id+':zhiyan',actor,'zhiyan'))
            if not frame.local.get('yj2013_juece') and self.skills.has(state,actor,'juece'):
                from .yj2013 import YJ2013Action
                frame.local['yj2013_juece']=True
                return StepResult.push(YJ2013Action(frame.action.action_id+':juece',actor,'juece'))
            if not frame.local.get('yj2012_chunlao') and self.skills.has(state,actor,'chunlao'):
                from .yj2012 import YJ2012Action
                frame.local['yj2012_chunlao']=True
                return StepResult.push(YJ2012Action(frame.action.action_id+':chunlao',actor,'chunlao'))
            if not frame.local.get('yj2012_miji') and self.skills.has(state, actor, 'miji'):
                from .yj2012 import YJ2012Action
                frame.local['yj2012_miji'] = True
                return StepResult.push(YJ2012Action(frame.action.action_id + ':miji', actor, 'miji'))
            if not frame.local.get('yj2011_jujian') and self.skills.has(state, actor, 'jujian'):
                from .yj2011 import JujianAction
                frame.local['yj2011_jujian'] = True
                return StepResult.push(JujianAction(frame.action.action_id + ':jujian', actor))
            if state.players[actor].marks.pop('fangquan_pending', 0):
                from .mountain import FangquanEndAction
                frame.step_index = 10
                return StepResult.push(FangquanEndAction(frame.action.action_id + ':fangquan-end', actor))
            if (not frame.local.get('benghuai_offered')
                    and self.skills.has(state, actor, 'benghuai')
                    and state.players[actor].is_alive):
                from .forest import BenghuaiAction
                frame.local['benghuai_offered'] = True
                frame.step_index = 10
                return StepResult.push(BenghuaiAction(frame.action.action_id + ':benghuai', actor))
            if self.base is not None:
                self.base.step(state, frame)
            if self.skills.has(state, actor, 'jushou') and state.players[actor].is_alive:
                frame.step_index = 5
                return StepResult.ask(PendingRequest(frame.action.action_id + ':jushou', actor,
                    RequestType.YES_NO, '是否发动【据守】摸三张牌并翻面？',
                    frame.action.action_id, frame.frame_id))
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
        if frame.step_index == 5:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 6
            return StepResult.push(DrawCardsAction(frame.action.action_id + ':jushou-draw', actor, 3))
        if frame.step_index == 6:
            state.players[actor].face_up = not state.players[actor].face_up
            return StepResult.complete()
        if frame.step_index == 10:
            frame.step_index = 1
            return StepResult.continue_()
        return StepResult.complete(frame.child_result)


class PreparationSkillBody:
    def __init__(self, skills, deck):
        self.skills = skills
        self.deck = deck

    def step(self, state, frame):
        actor = frame.action.player_id
        if not state.players[actor].is_alive:
            return StepResult.complete()
        if frame.step_index == 1 and not frame.local.get('yj2013_xiansi') and self.skills.has(state,actor,'xiansi'):
            from .yj2013 import YJ2013Action
            frame.local['yj2013_xiansi']=True;frame.step_index=20
            return StepResult.push(YJ2013Action(frame.action.action_id+':xiansi',actor,'xiansi'))
        if frame.step_index == 1 and not frame.local.get('yj2012_qianxi') and self.skills.has(state, actor, 'qianxi'):
            from .yj2012 import YJ2012Action
            frame.local['yj2012_qianxi'] = True
            frame.step_index = 20
            return StepResult.push(YJ2012Action(frame.action.action_id + ':qianxi', actor, 'qianxi'))
        if frame.step_index == 1 and not frame.local.get('yj2012_zili') and self.skills.has(state, actor, 'zili'):
            from .yj2012 import YJ2012Action
            frame.local['yj2012_zili'] = True
            frame.step_index = 20
            return StepResult.push(YJ2012Action(frame.action.action_id + ':zili', actor, 'zili'))
        if (frame.step_index == 1 and not frame.local.get('baiyin_checked')
                and self.skills.has(state, actor, 'baoyin')):
            from .gods import BaiyinAction
            frame.local['baiyin_checked'] = True
            frame.step_index = 20
            return StepResult.push(BaiyinAction(frame.action.action_id + ':baiyin', actor))
        if frame.step_index == 20:
            frame.step_index = 1
            return StepResult.continue_()
        if (frame.step_index == 1 and not frame.local.get('yinghun_offered')
                and self.skills.has(state, actor, 'yinghun')
                and state.players[actor].hp < state.players[actor].max_hp):
            from .forest import YinghunAction
            frame.local['yinghun_offered'] = True
            frame.step_index = 20
            return StepResult.push(YinghunAction(frame.action.action_id + ':yinghun', actor))
        if self.skills.has(state, actor, 'guanxing'):
            return self._guanxing(state, frame, actor)
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

    def _guanxing(self, state, frame, actor):
        draw_ref = ZoneRef(ZoneType.DRAW_PILE)
        if frame.step_index == 1:
            frame.step_index = 5
            return StepResult.ask(PendingRequest(frame.action.action_id + ':guanxing', actor,
                RequestType.YES_NO, '是否发动【观星】查看并调整牌堆顶？',
                frame.action.action_id, frame.frame_id))
        if frame.step_index == 5:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            self.deck.ensure_draw(state, frame.action.action_id + ':guanxing')
            count = min(5, sum(p.is_alive for p in state.players.values()), len(state.cards_in(draw_ref)))
            frame.local['guanxing_remaining'] = json.dumps(state.cards_in(draw_ref)[:count])
            frame.local['guanxing_top'] = '[]'
            frame.local['guanxing_bottom'] = '[]'
            frame.step_index = 6
        if frame.step_index == 6:
            remaining = json.loads(frame.local['guanxing_remaining'])
            if not remaining:
                top = json.loads(frame.local['guanxing_top'])
                bottom = json.loads(frame.local['guanxing_bottom'])
                zone = state.zones[draw_ref].card_ids
                zone[:] = top + zone[len(top) + len(bottom):] + bottom
                return StepResult.complete()
            frame.step_index = 7
            choices = tuple(f'{side}:{cid}' for side in ('top', 'bottom') for cid in remaining)
            return StepResult.ask(PendingRequest(
                f'{frame.action.action_id}:guanxing:{frame.cursor}', actor, RequestType.CHOOSE_OPTION,
                '观星：选择一张牌放到牌堆顶或牌堆底（按选择顺序排列）',
                frame.action.action_id, frame.frame_id, choices=choices))
        if frame.step_index == 7:
            side, cid = frame.decision.split(':', 1)
            remaining = json.loads(frame.local['guanxing_remaining'])
            remaining.remove(cid)
            ordered = json.loads(frame.local['guanxing_' + side])
            ordered.append(cid)
            frame.local['guanxing_remaining'] = json.dumps(remaining)
            frame.local['guanxing_' + side] = json.dumps(ordered)
            frame.decision = None
            frame.cursor += 1
            frame.step_index = 6
            return StepResult.continue_()
        raise InvalidCardUse('观星状态无效')


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
class JieyinAction(Action):
    player_id: str


class JieyinHandler:
    def __init__(self, skills, moves):
        self.skills, self.moves = skills, moves

    def targets(self, state, actor):
        return tuple(pid for pid in state.seat_order if pid != actor and state.players[pid].is_alive
                     and state.players[pid].hp < state.players[pid].max_hp
                     and self.skills.gender(state, pid) is Gender.MALE)

    def validate_start(self, state, action):
        if (not self.skills.has(state, action.player_id, 'jieyin')
                or state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY
                or state.play_usage is None or state.play_usage.count('skill.jieyin')
                or len(state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))) < 2
                or not self.targets(state, action.player_id)):
            raise InvalidCardUse('结姻不可用')

    def step(self, state, frame):
        action = frame.action
        hand = ZoneRef(ZoneType.HAND, action.player_id)
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':cards', action.player_id,
                RequestType.CHOOSE_CARDS, '结姻：选择弃置两张手牌', action.action_id,
                frame.frame_id, eligible_card_ids=state.cards_in(hand), min_count=2, max_count=2))
        if frame.step_index == 1:
            frame.local['cards'] = tuple(frame.decision)
            frame.decision = None
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '结姻：选择受伤的男性角色', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, action.player_id)))
        if frame.step_index == 2:
            target = frame.decision
            frame.decision = None
            cards = frame.local['cards']
            if target not in self.targets(state, action.player_id) or any(cid not in state.cards_in(hand) for cid in cards):
                raise InvalidCardUse('结姻目标或材料已失效')
            self.moves.move(state, CardMove(action.action_id + ':discard', cards, hand,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, action.player_id))
            state.play_usage.record('skill.jieyin')
            frame.local['target'] = target
            frame.step_index = 3
            return StepResult.push(RecoverAction(action.action_id + ':self', action.player_id, action.player_id, 1))
        if frame.step_index == 3:
            frame.step_index = 4
            target = frame.local['target']
            if state.players[target].is_alive:
                return StepResult.push(RecoverAction(action.action_id + ':target', action.player_id, target, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class QixiUse(Action):
    player_id: str
    material_id: str


class QixiUseHandler:
    def __init__(self, skills, moves, recorder, trick_rule):
        self.skills, self.moves, self.recorder, self.trick_rule = skills, moves, recorder, trick_rule

    def targets(self, state, player_id, material_id):
        from .forest import weimu_blocks
        return tuple(pid for pid in self.trick_rule.target_candidates(state, player_id)
                     if not weimu_blocks(state, pid, material_id,
                         'trick.dismantlement', player_id, self.skills))

    def validate_start(self, state, action):
        source = next((ref for ref, zone in state.zones.items()
                       if action.material_id in zone.card_ids), None)
        if (not self.skills.has(state, action.player_id, 'qixi')
                or state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY
                or source is None or source.player_id != action.player_id
                or source.zone_type not in (ZoneType.HAND, ZoneType.EQUIPMENT)
                or effective_color(state, action.material_id, action.player_id) is not Color.BLACK
                or not self.targets(state, action.player_id, action.material_id)):
            raise InvalidCardUse('奇袭不可用')

    def step(self, state, frame):
        from .military_tricks import TrickAction
        action = frame.action
        if frame.step_index in (0, 1):
            from .card_limits import validate_view_as_limits
            validate_view_as_limits(state, action.player_id, (action.material_id,), 'trick.dismantlement', skills=self.skills, skill_id='qixi')
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '奇袭：选择【过河拆桥】目标', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, action.player_id,
                                                                  action.material_id)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            self.validate_start(state, action)
            self.trick_rule.validate_targets(state, action.player_id, (target,))
            if target not in self.targets(state, action.player_id, action.material_id):
                raise InvalidCardUse('帷幕阻止该奇袭目标')
            source = next(ref for ref, zone in state.zones.items()
                          if action.material_id in zone.card_ids)
            self.moves.move(state, CardMove(action.action_id + ':processing', (action.material_id,),
                source, ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.USE, action.player_id, action.action_id))
            state.play_usage.record('trick.dismantlement')
            self.recorder.record(CardUsedEvent(action.action_id + ':used', action.player_id,
                action.material_id, (target,), 'trick.dismantlement'))
            frame.step_index = 2
            return StepResult.push(TrickAction(action.action_id + ':trick', action.player_id,
                action.material_id, 'trick.dismantlement', (target,)))
        if action.material_id in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
            self.moves.move(state, CardMove(action.action_id + ':discard', (action.material_id,),
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.USE, action.player_id, action.action_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class GuoseUse(Action):
    player_id: str
    material_id: str


class GuoseUseHandler:
    def __init__(self, skills, moves, recorder, trick_rule):
        self.skills, self.moves, self.recorder, self.trick_rule = skills, moves, recorder, trick_rule

    def validate_start(self, state, action):
        source = next((ref for ref, zone in state.zones.items()
                       if action.material_id in zone.card_ids), None)
        if (not self.skills.has(state, action.player_id, 'guose')
                or state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY
                or source is None or source.player_id != action.player_id
                or source.zone_type not in (ZoneType.HAND, ZoneType.EQUIPMENT)
                or effective_suit(state, action.material_id, action.player_id) is not Suit.DIAMOND
                or not self.trick_rule.target_candidates(state, action.player_id)):
            raise InvalidCardUse('国色不可用')

    def step(self, state, frame):
        from .military_tricks import TrickAction
        action = frame.action
        if frame.step_index in (0, 1):
            from .card_limits import validate_view_as_limits
            validate_view_as_limits(state, action.player_id, (action.material_id,), 'delayed.indulgence', skills=self.skills, skill_id='guose')
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '国色：选择【乐不思蜀】目标', action.action_id,
                frame.frame_id, allowed_player_ids=self.trick_rule.target_candidates(state, action.player_id)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            self.validate_start(state, action)
            self.trick_rule.validate_targets(state, action.player_id, (target,))
            source = next(ref for ref, zone in state.zones.items()
                          if action.material_id in zone.card_ids)
            self.moves.move(state, CardMove(action.action_id + ':processing', (action.material_id,),
                source, ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.USE, action.player_id, action.action_id))
            state.metadata.setdefault('virtual_delayed_cards', {})[action.material_id] = 'delayed.indulgence'
            state.play_usage.record('delayed.indulgence')
            self.recorder.record(CardUsedEvent(action.action_id + ':used', action.player_id,
                action.material_id, (target,), 'delayed.indulgence'))
            frame.step_index = 2
            return StepResult.push(TrickAction(action.action_id + ':trick', action.player_id,
                action.material_id, 'delayed.indulgence', (target,)))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class LongdanUse(Action):
    player_id: str
    material_id: str


class LongdanUseHandler:
    def __init__(self, skills, moves, recorder, slash_rule):
        self.skills, self.moves, self.recorder, self.slash_rule = skills, moves, recorder, slash_rule

    def step(self, state, frame):
        action = frame.action
        if frame.step_index in (0, 1):
            from .card_limits import validate_view_as_limits
            validate_view_as_limits(state, action.player_id, (action.material_id,), 'basic.slash', skills=self.skills, skill_id='longdan')
        hand = ZoneRef(ZoneType.HAND, action.player_id)
        if frame.step_index == 0:
            limit = self.slash_rule.usage_limit(state, action.player_id)
            if (not self.skills.has(state, action.player_id, 'longdan')
                    or state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY
                    or action.material_id not in state.cards_in(hand)
                    or state.cards[action.material_id].definition_id != 'basic.dodge'
                    or limit is not None and state.play_usage.count('basic.slash') >= limit):
                raise InvalidCardUse('龙胆不可用')
            targets = self.slash_rule.target_candidates(state, action.player_id)
            if not targets:
                raise InvalidCardUse('龙胆没有合法杀目标')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '龙胆：选择杀目标', action.action_id,
                frame.frame_id, allowed_player_ids=targets))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            self.slash_rule.validate_targets(state, action.player_id, (target,))
            card = state.cards[action.material_id]
            virtual = VirtualCard('basic.slash', (action.material_id,),
                                  effective_suit(state, action.material_id, action.player_id),
                                  effective_color(state, action.material_id, action.player_id))
            self.moves.move(state, CardMove(action.action_id + ':processing', (action.material_id,),
                hand, ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE,
                action.player_id, action.action_id))
            from .yj2011_tier3 import record_slash_use
            counted=record_slash_use(state, action.player_id, (target,))
            self.recorder.record(CardUsedEvent(action.action_id + ':used', action.player_id,
                action.material_id, (target,), 'basic.slash',counted,virtual))
            frame.step_index = 2
            return StepResult.push(SlashSequence(action.action_id + ':slash', action.player_id,
                action.material_id, (target,), virtual))
        if action.material_id in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
            self.moves.move(state, CardMove(action.action_id + ':discard', (action.material_id,),
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.USE, action.player_id, action.action_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class FanjianAction(Action):
    player_id: str


class FanjianHandler:
    def __init__(self, skills, moves, rng):
        self.skills, self.moves, self.rng = skills, moves, rng

    def validate_start(self, state, action):
        if (not self.skills.has(state, action.player_id, 'fanjian')
                or state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY
                or state.play_usage is None or state.play_usage.count('skill.fanjian')
                or not state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))
                or not any(pid != action.player_id and state.players[pid].is_alive for pid in state.seat_order)):
            raise InvalidCardUse('反间不可用')

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '反间：选择猜花色的角色', action.action_id,
                frame.frame_id, allowed_player_ids=tuple(pid for pid in state.seat_order
                    if pid != action.player_id and state.players[pid].is_alive)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            frame.local['target'] = target
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':guess', target,
                RequestType.CHOOSE_OPTION, '反间：猜测即将获得的牌的花色',
                action.action_id, frame.frame_id,
                choices=tuple(suit.value for suit in Suit)))
        if frame.step_index == 2:
            guess = frame.decision
            frame.decision = None
            target = frame.local['target']
            hand = ZoneRef(ZoneType.HAND, action.player_id)
            cards = state.cards_in(hand)
            if not cards or not state.players[target].is_alive:
                return StepResult.complete()
            material = self.rng.choice(cards)
            state.play_usage.record('skill.fanjian')
            self.moves.move(state, CardMove(action.action_id + ':give', (material,), hand,
                ZoneRef(ZoneType.HAND, target), CardMoveReason.SYSTEM,
                action.player_id, action.action_id))
            if effective_suit(state, material, action.player_id).value != guess:
                from .military_basics import MilitaryDamageAction
                frame.step_index = 3
                return StepResult.push(MilitaryDamageAction(action.action_id + ':damage',
                    action.player_id, target, 1))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class LijianAction(Action):
    player_id: str


class LijianHandler:
    def __init__(self, skills, moves, recorder):
        self.skills, self.moves, self.recorder = skills, moves, recorder

    def materials(self, state, actor):
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == actor and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                     for cid in zone.card_ids)

    def targets(self, state, actor):
        return tuple(pid for pid in state.seat_order if pid != actor and state.players[pid].is_alive
                     and self.skills.gender(state, pid) is Gender.MALE)

    def validate_start(self, state, action):
        if (not self.skills.has(state, action.player_id, 'lijian')
                or state.current_player_id != action.player_id or state.current_phase is not Phase.PLAY
                or state.play_usage is None or state.play_usage.count('skill.lijian')
                or not self.materials(state, action.player_id) or len(self.targets(state, action.player_id)) < 2):
            raise InvalidCardUse('离间不可用')

    def step(self, state, frame):
        from .military_tricks import TargetTrick
        from .events import Event
        action = frame.action
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':cost', action.player_id,
                RequestType.CHOOSE_CARD, '离间：选择弃置一张牌', action.action_id,
                frame.frame_id, eligible_card_ids=self.materials(state, action.player_id)))
        if frame.step_index == 1:
            frame.local['card'] = frame.decision
            frame.decision = None
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':targets', action.player_id,
                RequestType.CHOOSE_PLAYERS, '离间：选择两名男性角色进行决斗', action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, action.player_id),
                min_count=2, max_count=2))
        if frame.step_index == 2:
            targets = tuple(frame.decision)
            frame.decision = None
            card = frame.local['card']
            if (len(targets) != 2 or targets[0] == targets[1]
                    or any(pid not in self.targets(state, action.player_id) for pid in targets)
                    or card not in self.materials(state, action.player_id)):
                raise InvalidCardUse('离间材料或目标已失效')
            source = next(ref for ref, zone in state.zones.items() if card in zone.card_ids)
            self.moves.move(state, CardMove(action.action_id + ':discard', (card,), source,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, action.player_id))
            state.play_usage.record('skill.lijian')
            self.recorder.record(Event(action.action_id + ':used', 'skill_lijian', action.player_id,
                                       target_ids=targets))
            frame.step_index = 3
            return StepResult.push(TargetTrick(action.action_id + ':duel', targets[0], targets[1],
                                                card, 'trick.duel'))
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

    def targets(self, state, player_id, material_id):
        source = next((ref for ref, zone in state.zones.items()
                       if ref.player_id == player_id and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                       and material_id in zone.card_ids), None)
        if source is None:
            return ()
        preview = state
        if source.zone_type is ZoneType.EQUIPMENT:
            # A detached zone snapshot checks legality after paying the card.
            # Never temporarily remove live equipment or publish preview events.
            preview = replace(state, zones={ref: CardZone(ref, list(zone.card_ids))
                                           for ref, zone in state.zones.items()})
            CardMoveService(EventRecorder()).move(preview, CardMove(
                'wusheng-target-preview', (material_id,), source,
                ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE, player_id))
        limit = self.slash_rule.usage_limit(preview, player_id)
        if (not self.slash_rule.can_use(preview, player_id) or preview.play_usage is None
                or limit is not None and preview.play_usage.count('basic.slash') >= limit):
            return ()
        return self.slash_rule.target_candidates(preview, player_id)

    def step(self, state, frame):
        action = frame.action
        if frame.step_index in (0, 1):
            from .card_limits import validate_view_as_limits
            validate_view_as_limits(state, action.player_id, (action.material_id,), 'basic.slash', skills=self.skills, skill_id='wusheng')
        if frame.step_index == 0:
            limit = self.slash_rule.usage_limit(state,action.player_id)
            if (state.current_phase is not Phase.PLAY or state.current_player_id != action.player_id or
                    action.material_id not in self.skills.red_slash_materials(state,action.player_id) or
                    limit is not None and state.play_usage.count('basic.slash') >= limit):
                raise InvalidCardUse('武圣不可用')
            targets = self.targets(state, action.player_id, action.material_id)
            if not targets:
                raise InvalidCardUse('武圣没有合法杀目标')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id+':target', action.player_id,
                RequestType.CHOOSE_PLAYER, '武圣：请选择杀目标', action.action_id, frame.frame_id,
                allowed_player_ids=targets))
        if frame.step_index == 1:
            target = frame.decision
            if (action.material_id not in self.skills.red_slash_materials(state, action.player_id)
                    or target not in self.targets(state, action.player_id, action.material_id)):
                raise InvalidCardUse('武圣材料或目标已失效')
            source = next(ref for ref, zone in state.zones.items() if action.material_id in zone.card_ids)
            card = state.cards[action.material_id]
            virtual = VirtualCard('basic.slash', (action.material_id,),
                                  effective_suit(state, action.material_id, action.player_id),
                                  effective_color(state, action.material_id, action.player_id))
            self.moves.move(state, CardMove(action.action_id+':processing', (action.material_id,),
                source, ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.USE, action.player_id))
            from .yj2011_tier3 import record_slash_use
            counted=record_slash_use(state, action.player_id, (target,))
            self.moves.recorder.record(CardUsedEvent(action.action_id+':used',action.player_id,action.material_id,(target,),'basic.slash',counted,virtual))
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
    def __init__(self, skills, slash_rule, recorder=None):
        self.skills, self.slash_rule, self.recorder = skills, slash_rule, recorder

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
            from .yj2011_tier3 import record_slash_use
            counted=record_slash_use(state, action.player_id, (frame.local['target'],))
            if self.recorder is not None:
                virtual=result if isinstance(result,VirtualCard) else VirtualCard('basic.slash',(material,),effective_suit(state,material,action.player_id),effective_color(state,material,action.player_id))
                self.recorder.record(CardUsedEvent(action.action_id+':used',action.player_id,material,(frame.local['target'],),'basic.slash',counted,virtual))
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
        from .yj2011_tier3 import play_options
        extra = play_options(state, pid, self.skills)
        from .remaining_gods import play_options as god_play_options
        extra.extend(god_play_options(state,pid,self.skills))
        from .fuhun import available as fuhun_available
        if fuhun_available(state,pid,self.skills,self.slash_rule):extra.append('skill:fuhun')
        from .card_limits import card_allowed
        limit=self.slash_rule.usage_limit(state,pid)
        if self.skills.has(state,pid,'lihuo') and self.slash_rule.can_use(state,pid) and (limit is None or state.play_usage.count('basic.slash')<limit) and self.slash_rule.target_candidates(state,pid) and any(state.cards[c].definition_id=='basic.slash' and card_allowed(state,pid,(c,)) for c in state.cards_in(ZoneRef(ZoneType.HAND,pid))):
            extra.append('skill:lihuo')
        from .yj2012 import play_options as yj2012_play_options
        extra.extend(yj2012_play_options(state, pid, self.skills))
        from .yj2013 import play_options as yj2013_play_options
        extra.extend(yj2013_play_options(state,pid,self.skills,self.validator.definitions))
        from .yj2013 import XiansiSlashHandler
        xiansi=XiansiSlashHandler(self.skills,None,self.validator.definitions,None)
        extra.extend('skill:xiansi_slash:'+q for q in state.seat_order if xiansi.available(state,pid,q))
        hand = state.cards_in(ZoneRef(ZoneType.HAND,pid))
        materials = tuple(cid for ref, zone in state.zones.items()
                          if ref.player_id == pid and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                          for cid in zone.card_ids)
        if self.skills.has(state,pid,'rende') and hand and any(state.players[q].is_alive for q in state.seat_order if q != pid):
            extra.append('skill:rende')
        if self.skills.has(state,pid,'zhiheng') and not state.play_usage.count('skill.zhiheng') and any(
                ref.player_id == pid and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT) and zone.card_ids
                for ref,zone in state.zones.items()):
            extra.append('skill:zhiheng')
        if self.skills.has(state, pid, 'jilue') and state.players[pid].marks.get('ren', 0) > 0:
            if not state.play_usage.count('skill.zhiheng') and materials:
                extra.append('skill:jilue-zhiheng')
            if not state.players[pid].marks.get('jilue_wansha'):
                extra.append('skill:jilue-wansha')
        if self.skills.has(state,pid,'kurou'):
            extra.append('skill:kurou')
        if self.skills.has(state,pid,'wuwei') and state.players[pid].marks.get('rage', 0) >= 2:
            extra.append('skill:wuwei')
        if (self.skills.has(state,pid,'shenfen') and state.players[pid].marks.get('rage', 0) >= 6
                and not state.play_usage.count('skill.shenfen')):
            extra.append('skill:shenfen')
        if (self.skills.has(state,pid,'qingnang') and not state.play_usage.count('skill.qingnang') and hand
                and any(p.is_alive and p.hp < p.max_hp for p in state.players.values())):
            extra.append('skill:qingnang')
        if (self.skills.has(state,pid,'jieyin') and not state.play_usage.count('skill.jieyin')
                and len(hand) >= 2 and any(q != pid and p.is_alive and p.hp < p.max_hp
                    and self.skills.gender(state,q) is Gender.MALE for q,p in state.players.items())):
            extra.append('skill:jieyin')
        if self.skills.has(state,pid,'qixi'):
            dismantlement = self.validator.rules.get('trick.dismantlement')
            if dismantlement.target_candidates(state,pid):
                from .forest import weimu_blocks
                extra.extend(f'virtual:qixi:{cid}' for cid in materials
                             if effective_color(state, cid, pid) is Color.BLACK
                             and any(not weimu_blocks(state, target, cid,
                                 'trick.dismantlement', pid, self.skills)
                                 for target in dismantlement.target_candidates(state, pid)))
        if self.skills.has(state,pid,'guose'):
            indulgence = self.validator.rules.get('delayed.indulgence')
            if indulgence.target_candidates(state,pid):
                extra.extend(f'virtual:guose:{cid}' for cid in materials
                             if effective_suit(state, cid, pid) is Suit.DIAMOND)
        if self.skills.has(state, pid, 'duanliang'):
            from .forest import DuanliangHandler
            shortage = self.validator.rules.get('delayed.supply_shortage')
            handler = DuanliangHandler(self.skills, None, None,
                                      self.validator.definitions, shortage)
            if handler.available(state, pid):
                extra.extend(f'virtual:duanliang:{cid}' for cid in handler.materials(state, pid))
        if self.skills.has(state, pid, 'jixi'):
            from .mountain import JixiHandler, field_zone
            handler = JixiHandler(self.skills, None, None, self.validator.rules.get('trick.snatch'))
            if handler.available(state, pid):
                extra.extend(f'virtual:jixi:{cid}' for cid in state.cards_in(field_zone(pid)))
        if self.skills.has(state, pid, 'wushen'):
            from .gods import WushenHandler
            handler = WushenHandler(self.skills, None, self.slash_rule)
            if handler.available(state, pid):
                extra.extend(f'virtual:wushen:{cid}' for cid in handler.materials(state, pid))
        if self.skills.has(state, pid, 'tiaoxin'):
            from .mountain import TiaoxinHandler
            handler = TiaoxinHandler(self.skills, None, self.slash_rule,
                                    self.validator.definitions)
            if handler.available(state, pid):
                extra.append('skill:tiaoxin')
        from .mountain import ZhibaHandler
        if ZhibaHandler(self.skills, None, None).available(state, pid):
            extra.append('skill:zhiba')
        from .mountain import ZhijianHandler
        if ZhijianHandler(self.skills, None, self.validator.definitions).available(state, pid):
            extra.append('skill:zhijian')
        from .gods import GongxinHandler
        if GongxinHandler(self.skills, None).available(state, pid):
            extra.append('skill:gongxin')
        from .gods import YeyanHandler
        if YeyanHandler(self.skills, None).available(state, pid):
            extra.append('skill:yeyan')
        if self.skills.has(state, pid, 'dimeng'):
            from .forest import DimengHandler
            if DimengHandler(self.skills).available(state, pid):
                extra.append('skill:dimeng')
        if self.skills.has(state, pid, 'luanwu'):
            from .forest import LuanwuHandler
            if LuanwuHandler(self.skills, self.slash_rule).available(state, pid):
                extra.append('skill:luanwu')
        if self.skills.has(state, pid, 'jiuchi'):
            from .forest import JiuchiHandler
            wine = self.validator.rules.get('basic.wine')
            handler = JiuchiHandler(self.skills, None, None, wine)
            if handler.available(state, pid):
                extra.extend(f'virtual:jiuchi:{cid}' for cid in handler.materials(state, pid))
        if (self.skills.has(state,pid,'fanjian') and not state.play_usage.count('skill.fanjian')
                and hand and any(q != pid and p.is_alive for q,p in state.players.items())):
            extra.append('skill:fanjian')
        if (self.skills.has(state,pid,'lijian') and not state.play_usage.count('skill.lijian')
                and any(ref.player_id == pid and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                        and zone.card_ids for ref,zone in state.zones.items())
                and sum(q != pid and p.is_alive and self.skills.gender(state,q) is Gender.MALE
                        for q,p in state.players.items()) >= 2):
            extra.append('skill:lijian')
        from .wind_lord import huangtian_lord
        lord = huangtian_lord(state, self.skills)
        if (lord is not None and lord != pid and self.skills.faction(state, pid) is Kingdom.QUN
                and not state.play_usage.count('skill.huangtian')
                and any(state.cards[cid].definition_id in ('basic.dodge', 'delayed.lightning')
                        for cid in hand)):
            extra.append('skill:huangtian')
        if self.skills.has(state, pid, 'guhuo') and hand:
            from .wind_guhuo import GuhuoHandler
            if GuhuoHandler(self.skills, self.validator.definitions,
                            self.validator.rules, None, None).available(state, pid):
                extra.append('skill:guhuo')
        from .fire import QiangxiHandler, QuhuHandler, LuanjiHandler
        if QiangxiHandler(self.skills, None, self.validator.definitions).available(state, pid):
            extra.append('skill:qiangxi')
        if QuhuHandler(self.skills, self.validator.definitions).available(state, pid):
            extra.append('skill:quhu')
        luanji = LuanjiHandler(self.skills, None, None)
        if self.skills.has(state, pid, 'luanji'):
            extra.extend(f'virtual:luanji:{a}:{b}' for a, b in luanji.pairs(state, pid))
        from .fire import TianyiHandler
        if TianyiHandler(self.skills).available(state, pid):
            extra.append('skill:tianyi')
        from .fire import FireViewAsTrickHandler
        fire_tricks = FireViewAsTrickHandler(self.skills, None, None, self.validator.rules)
        if fire_tricks.available(state, pid, 'lianhuan'):
            extra.extend(f'virtual:lianhuan:{cid}' for cid in fire_tricks.materials(state, pid, 'lianhuan'))
        if fire_tricks.available(state, pid, 'huoji'):
            extra.extend(f'virtual:huoji:{cid}' for cid in fire_tricks.materials(state, pid, 'huoji'))
        if fire_tricks.available(state, pid, 'shuangxiong'):
            extra.extend(f'virtual:shuangxiong:{cid}' for cid in fire_tricks.materials(state, pid, 'shuangxiong'))
        limit = self.slash_rule.usage_limit(state,pid)
        slash_available = self.slash_rule.can_use(state, pid) and (limit is None or state.play_usage.count('basic.slash') < limit) and bool(self.slash_rule.target_candidates(state,pid))
        if slash_available:
            extra.extend(f'virtual:wusheng:{cid}' for cid in self.skills.red_slash_materials(state,pid)
                         if WushengUseHandler(self.skills, None, self.slash_rule).targets(state, pid, cid))
            if self.skills.has(state,pid,'longdan'):
                extra.extend(f'virtual:longdan:{cid}' for cid in hand
                             if state.cards[cid].definition_id == 'basic.dodge')
            if self.skills.has(state,pid,'jijiang') and not state.play_usage.count('skill.jijiang.attempted') and self.skills.allies(state,pid,Kingdom.SHU):
                extra.append('skill:jijiang')
        if self.skills.has(state, pid, 'longhun'):
            from .gods import longhun_materials, LonghunUseHandler
            handler = LonghunUseHandler(self.skills, None, None, self.slash_rule)
            for kind, definition_id in (('peach', 'basic.peach'),
                                        ('fire_slash', 'basic.fire_slash')):
                for cards in longhun_materials(state, pid, definition_id):
                    if handler.available(state, pid, definition_id, cards):
                        extra.append('virtual:longhun:' + kind + ':' + ':'.join(cards))
        from .card_limits import card_allowed
        extra = [option for option in extra if not option.startswith('virtual:') or
                 card_allowed(state,pid,tuple(option.split(':')[3:] if option.startswith('virtual:longhun:')
                                             else option.split(':')[2:]))]
        return (*ordinary,*extra)

    def build_action(self, state, pid, option, aid):
        if option not in self.options(state,pid):
            raise InvalidCardUse('skill option is no longer legal')
        if option.startswith('skill:xiansi_slash:'):
            from .yj2013 import XiansiSlashAction
            return XiansiSlashAction(aid+':xiansi',pid,option.split(':',2)[2])
        if option in ('skill:zhanhuo','skill:poxi'):
            from .remaining_gods import RemainingGodAction
            return RemainingGodAction(aid+':god',pid,option.split(':')[1])
        if option=='skill:fuhun':
            from .fuhun import UseFuhun
            return UseFuhun(aid+':fuhun',pid)
        if option in ('skill:jiushi', 'skill:xinzhan', 'skill:ganlu', 'skill:mingce', 'skill:xianzhen'):
            from .yj2011_tier3 import YJSkillAction
            return YJSkillAction(aid + ':yj2011', pid, option.split(':')[1])
        if option in ('skill:junxing','skill:danshou','skill:fencheng','skill:mieji'):
            from .yj2013 import YJ2013Action
            return YJ2013Action(aid+':yj2013',pid,option.split(':')[1])
        if option in ('skill:paiyi', 'skill:anxu', 'skill:gongqi', 'skill:jiefan', 'skill:qice', 'skill:lihuo'):
            from .yj2012 import YJ2012Action
            return YJ2012Action(aid + ':yj2012', pid, option.split(':')[1])
        if option.startswith('skill:jilue-'):
            from .gods import JiluePlayAction
            return JiluePlayAction(aid + ':jilue', pid, option.split('-', 1)[1])
        if option.startswith('virtual:longhun:'):
            from .gods import LonghunUse
            parts = option.split(':')
            definition = ('basic.peach' if parts[2] == 'peach'
                          else 'basic.fire_slash')
            return LonghunUse(aid + ':longhun', pid, tuple(parts[3:]), definition)
        if option.startswith('virtual:lianhuan:'):
            from .fire import FireViewAsTrick
            return FireViewAsTrick(aid + ':lianhuan', pid, option.split(':', 2)[2], 'lianhuan')
        if option.startswith('virtual:huoji:'):
            from .fire import FireViewAsTrick
            return FireViewAsTrick(aid + ':huoji', pid, option.split(':', 2)[2], 'huoji')
        if option.startswith('virtual:shuangxiong:'):
            from .fire import FireViewAsTrick
            return FireViewAsTrick(aid + ':shuangxiong', pid, option.split(':', 2)[2], 'shuangxiong')
        if option == 'skill:qiangxi':
            from .fire import QiangxiAction
            return QiangxiAction(aid + ':qiangxi', pid)
        if option == 'skill:quhu':
            from .fire import QuhuAction
            return QuhuAction(aid + ':quhu', pid)
        if option.startswith('virtual:luanji:'):
            from .fire import LuanjiAction
            _, _, first, second = option.split(':', 3)
            return LuanjiAction(aid + ':luanji', pid, (first, second))
        if option == 'skill:tianyi':
            from .fire import TianyiAction
            return TianyiAction(aid + ':tianyi', pid)
        if option == 'skill:rende':
            return RendeAction(aid+':rende',pid)
        if option == 'skill:zhiheng':
            return ZhihengAction(aid+':zhiheng',pid)
        if option == 'skill:jijiang':
            return JijiangUse(aid+':jijiang',pid)
        if option == 'skill:kurou':
            return KurouAction(aid+':kurou', pid)
        if option == 'skill:wuwei':
            from .god_lvbu import WuqianAction
            return WuqianAction(aid+':wuwei', pid)
        if option == 'skill:shenfen':
            from .god_lvbu import ShenfenAction
            return ShenfenAction(aid+':shenfen', pid)
        if option == 'skill:qingnang':
            return QingnangAction(aid+':qingnang', pid)
        if option == 'skill:jieyin':
            return JieyinAction(aid+':jieyin', pid)
        if option == 'skill:fanjian':
            return FanjianAction(aid+':fanjian', pid)
        if option == 'skill:lijian':
            return LijianAction(aid+':lijian', pid)
        if option == 'skill:dimeng':
            from .forest import DimengAction
            return DimengAction(aid + ':dimeng', pid)
        if option == 'skill:luanwu':
            from .forest import LuanwuAction
            return LuanwuAction(aid + ':luanwu', pid)
        if option.startswith('virtual:jiuchi:'):
            from .forest import JiuchiUse
            return JiuchiUse(aid + ':jiuchi', pid, option.split(':', 2)[2])
        if option == 'skill:huangtian':
            from .wind_lord import HuangtianAction
            return HuangtianAction(aid+':huangtian', pid)
        if option == 'skill:guhuo':
            from .wind_guhuo import GuhuoAction
            return GuhuoAction(aid+':guhuo', pid)
        if option.startswith('virtual:wusheng:'):
            return WushengUse(aid+':wusheng',pid,option.split(':',2)[2])
        if option.startswith('virtual:qixi:'):
            return QixiUse(aid+':qixi',pid,option.split(':',2)[2])
        if option.startswith('virtual:guose:'):
            return GuoseUse(aid+':guose',pid,option.split(':',2)[2])
        if option.startswith('virtual:duanliang:'):
            from .forest import DuanliangUse
            return DuanliangUse(aid + ':duanliang', pid, option.split(':', 2)[2])
        if option.startswith('virtual:jixi:'):
            from .mountain import JixiUse
            return JixiUse(aid + ':jixi', pid, option.split(':', 2)[2])
        if option.startswith('virtual:wushen:'):
            from .gods import WushenUse
            return WushenUse(aid + ':wushen', pid, option.split(':', 2)[2])
        if option == 'skill:tiaoxin':
            from .mountain import TiaoxinAction
            return TiaoxinAction(aid + ':tiaoxin', pid)
        if option == 'skill:zhiba':
            from .mountain import ZhibaAction
            return ZhibaAction(aid + ':zhiba', pid)
        if option == 'skill:zhijian':
            from .mountain import ZhijianAction
            return ZhijianAction(aid + ':zhijian', pid)
        if option == 'skill:gongxin':
            from .gods import GongxinAction
            return GongxinAction(aid + ':gongxin', pid)
        if option == 'skill:yeyan':
            from .gods import YeyanAction
            return YeyanAction(aid + ':yeyan', pid)
        if option.startswith('virtual:longdan:'):
            return LongdanUse(aid+':longdan',pid,option.split(':',2)[2])
        return self.base.build_action(state,pid,option,aid)


