"""Military basic cards built on the existing explicit action stack.

Distance, equipment storage, judgment and dying resolution are reused.
"""
from dataclasses import dataclass

from sanguosha.content.cards.basic import SlashRule, ReachableOpponent, EquipmentSlashLimit
from sanguosha.content.cards.classic_military import register_additional_definitions
from sanguosha.model.enums import DamageNature, Color, EquipmentSlot, Phase, Kingdom, Suit, Gender, Identity
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from .actions import Action, StepKind, StepResult
from .card_effects import SlashEffectAction
from .card_rules import InvalidCardUse
from .card_moves import CardMove, CardMoveReason
from .damage import DamageAction, DamageActionHandler
from .distance import DistanceSystem
from .dying import DyingAction
from .events import BeforeDamageEvent, DamageDealtEvent, AfterDamageEvent, DyingRequiredEvent, Event, VirtualResponseEvent
from .judgment import JudgmentAction, JudgmentPattern, JudgmentHandler
from .response import RespondWithCardAction, RespondWithCardHandler
from .recovery import RecoverAction
from .turnover import TurnoverAction
from .deck import DrawCardsAction
from .suits import effective_color, effective_suit
from .requests import PendingRequest, RequestType
from .equipment import EquipCardAction, EquipCardHandler, register_equipment_rules
from sanguosha.model.virtual_card import VirtualCard

SLASH_IDS = frozenset(('basic.slash', 'basic.fire_slash', 'basic.thunder_slash'))


def required_dodge_count(state, source_id, target_id, skills):
    if skills is None:
        return 1
    doubled = skills.has(state, source_id, 'wushuang')
    doubled = doubled or (skills.has(state, source_id, 'roulin')
                         and skills.gender(state, target_id) is Gender.FEMALE)
    doubled = doubled or (skills.has(state, target_id, 'roulin')
                         and skills.gender(state, source_id) is Gender.FEMALE)
    return 2 if doubled else 1

def equipped(state, player, slot):
    cards = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, player, slot))
    return state.cards[cards[0]].definition_id if cards else None

@dataclass(frozen=True, slots=True)
class MilitaryDamageAction(DamageAction):
    propagated: bool = False
    ignore_armor: bool = False
    material_card_ids: tuple[str, ...] = ()
    redirected: bool = False
    card_kind: str = ''
    wine_enhanced: bool = False
    virtual_card: VirtualCard | None = None

class MilitaryDamageHandler(DamageActionHandler):
    """The first recipient completes dying before the chain cursor advances."""
    def __init__(self, recorder, moves=None, skills=None, definitions=None):
        super().__init__(recorder)
        self.moves, self.skills = moves, skills
        self.distance = DistanceSystem(definitions)

    def validate_start(self, state, action):
        if action.amount <= 0 or action.target_id not in state.players or not state.players[action.target_id].is_alive:
            raise InvalidCardUse('damage must have positive amount and a living target')

    def step(self, state, frame):
        action = frame.action
        target = state.players[action.target_id]
        from .yj2011 import replace_damage
        replacement = replace_damage(state, frame, self.skills, self.recorder)
        if replacement is not None:
            return replacement
        if frame.step_index == 0:
            self.validate_start(state, action)
            if (action.nature is not DamageNature.THUNDER
                    and any(key.startswith('fog:') for key in target.marks)):
                self.recorder.record(Event(action.action_id + ':fog', 'damage_prevented',
                    action.target_id, metadata={'skill_id': 'dawu'}))
                return StepResult.complete(0)
            if (not frame.local.get('tianxiang_offered') and not getattr(action, 'redirected', False)
                    and self.skills is not None and self.skills.has(state, action.target_id, 'tianxiang')):
                hand = state.cards_in(ZoneRef(ZoneType.HAND, action.target_id))
                materials = tuple(cid for cid in hand
                                  if effective_suit(state, cid, action.target_id) is Suit.HEART)
                others = tuple(pid for pid in state.seat_order if pid != action.target_id
                               and state.players[pid].is_alive)
                frame.local['tianxiang_offered'] = True
                if materials and others:
                    frame.step_index = 9
                    return StepResult.ask(PendingRequest(action.action_id + ':tianxiang', action.target_id,
                        RequestType.YES_NO, '是否发动【天香】弃红桃手牌转移伤害？',
                        action.action_id, frame.frame_id,
                        choices=(f'damage:{action.amount}',), subject_player_id=action.source_id))
            if self.skills is not None and target.hp == 1:
                owners=tuple(q for q in state.seat_order if q!=action.target_id and state.players[q].is_alive
                    and self.skills.has(state,q,'renxin'))
                index=frame.local.get('renxin_cursor',0)
                if index<len(owners):
                    frame.local['renxin_cursor']=index+1
                    frame.step_index=31
                    from .yj2013 import YJ2013Action
                    return StepResult.push(YJ2013Action(action.action_id+':renxin:'+owners[index],owners[index],'renxin',action.target_id))
            amount = action.amount
            if (action.nature is DamageNature.FIRE
                    and any(key.startswith('wind:') for key in target.marks)):
                amount += 1
            armor = equipped(state, action.target_id, EquipmentSlot.ARMOR)
            if (action.source_id is not None and state.current_player_id == action.source_id
                    and state.players[action.source_id].marks.get('luoyi')
                    and not getattr(action, 'propagated', False)
                    and (getattr(action,'card_kind','')=='slash' or (action.card_id in state.cards
                         and state.cards[action.card_id].definition_id in (*SLASH_IDS, 'trick.duel')))):
                amount += 1
            if (self.skills is not None and action.source_id is not None
                    and action.source_id != action.target_id and not getattr(action, 'propagated', False)
                    and not getattr(action,'redirected',False)
                    and getattr(action,'card_kind','') == 'slash'
                    and self.skills.has(state,action.source_id,'anjian')
                    and not self.distance.can_reach_with_slash(state,action.target_id,action.source_id)):
                amount += 1
            from .yj2011_tier3 import scoped_target
            ignores_armor = getattr(action, 'ignore_armor', False) or (
                action.source_id is not None and scoped_target(state, action.source_id, action.target_id))
            if not ignores_armor:
                if armor == 'equipment.armor.vine' and action.nature is DamageNature.FIRE:
                    amount += 1
                if armor == 'equipment.armor.silver_lion':
                    amount = min(amount, 1)
            frame.local['amount'] = amount
            chain = ()
            if action.nature is not DamageNature.NORMAL and target.chained:
                from .chaining import set_chained
                set_chained(state,action.target_id,False,self.skills)
                if not getattr(action, 'propagated', False):
                    start = state.seat_order.index(action.target_id)
                    order = state.seat_order[start + 1:] + state.seat_order[:start]
                    chain = tuple(pid for pid in order if state.players[pid].is_alive and state.players[pid].chained)
            frame.local['chain'] = '|'.join(chain)
            self.recorder.record(BeforeDamageEvent(action.action_id + ':before', action.source_id, action.target_id, amount))
            frame.local['yj_face_down_before'] = not target.face_up
            target.hp -= amount
            if (self.skills is not None and self.skills.has(state, action.target_id, 'zhichi')
                    and state.current_player_id != action.target_id):
                target.marks['yj_zhichi'] = state.turn_number
            if self.skills is not None and self.skills.has(state, action.target_id, 'renjie'):
                target.marks['ren'] = target.marks.get('ren', 0) + amount
            from .fuhun import grant_after_damage
            grant_after_damage(state,action,self.skills)
            from .remaining_gods import gain_junlve
            gain_junlve(state,action.source_id,action.target_id,amount,self.skills)
            virtual=getattr(action,"virtual_card",None)
            if virtual is not None and virtual.skill_id=="lihuo" and virtual.material_ids:
                state.metadata.setdefault("lihuo_hits",{})[str(action.source_id)+":"+virtual.material_ids[0]]=True
            self.recorder.record(DamageDealtEvent(action.action_id + ':dealt', action.source_id, action.target_id, amount, target.hp))
            from .god_lvbu import grant_rage_on_damage
            grant_rage_on_damage(state, action.source_id, action.target_id, amount)
            self.recorder.record(AfterDamageEvent(action.action_id + ':after', action.source_id,
                                                  action.target_id, amount,
                                                  getattr(action, 'card_kind', '')))
            self.recorder.record(Event(action.action_id + ':nature', 'damage_nature', action.target_id,
                                       metadata={'nature': action.nature.value, 'amount': amount}))
            source = action.source_id
            frame.local['kuanggu_remaining'] = (amount if source is not None and source != action.target_id
                and state.players[source].is_alive and self.skills is not None
                and self.skills.has(state, source, 'kuanggu')
                and self.distance.distance_between(state, source, action.target_id) <= 1 else 0)
            if frame.local['kuanggu_remaining']:
                frame.step_index = 8
                return StepResult.push(RecoverAction(action.action_id + ':kuanggu:0',
                    source, source, 1))
            frame.step_index = 1
            if target.hp <= 0:
                self.recorder.record(DyingRequiredEvent(action.action_id + ':dying', action.target_id, target.hp))
                return StepResult.push(DyingAction(action.action_id + ':rescue', action.target_id, action.source_id))
            return StepResult.continue_()
        if frame.step_index == 31:
            if frame.child_result is True:
                self.recorder.record(Event(action.action_id+':renxin-prevented','damage_prevented',action.target_id,
                    metadata={'skill_id':'renxin'}))
                return StepResult.complete(0)
            frame.step_index=0
            return StepResult.continue_()
        if frame.step_index == 9:
            wanted = frame.decision is True
            frame.decision = None
            frame.step_index = 0
            if not wanted:
                return StepResult.continue_()
            eligible = tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, action.target_id))
                             if effective_suit(state, cid, action.target_id) is Suit.HEART)
            if not eligible:
                return StepResult.continue_()
            frame.step_index = 10
            return StepResult.ask(PendingRequest(action.action_id + ':tianxiang-cost', action.target_id,
                RequestType.CHOOSE_CARD, '天香：选择一张红桃手牌弃置', action.action_id,
                frame.frame_id, eligible_card_ids=eligible))
        if frame.step_index == 10:
            cost = frame.decision
            frame.decision = None
            if (cost not in state.cards_in(ZoneRef(ZoneType.HAND, action.target_id))
                    or effective_suit(state, cost, action.target_id) is not Suit.HEART):
                raise InvalidCardUse('天香只能弃置红桃手牌')
            frame.local['tianxiang_cost'] = cost
            others = tuple(pid for pid in state.seat_order if pid != action.target_id
                           and state.players[pid].is_alive)
            frame.step_index = 11
            return StepResult.ask(PendingRequest(action.action_id + ':tianxiang-target', action.target_id,
                RequestType.CHOOSE_PLAYER, '天香：选择承受伤害的其他角色',
                action.action_id, frame.frame_id, allowed_player_ids=others))
        if frame.step_index == 11:
            redirected_to = frame.decision
            frame.decision = None
            cost = frame.local['tianxiang_cost']
            if (redirected_to == action.target_id or not state.players[redirected_to].is_alive
                    or cost not in state.cards_in(ZoneRef(ZoneType.HAND, action.target_id))):
                raise InvalidCardUse('天香目标或代价已不可用')
            self.moves.move(state, CardMove(action.action_id + ':tianxiang-discard', (cost,),
                ZoneRef(ZoneType.HAND, action.target_id), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.DISCARD, action.target_id, action.action_id))
            frame.local['tianxiang_target'] = redirected_to
            frame.step_index = 12
            return StepResult.push(MilitaryDamageAction(action.action_id + ':tianxiang-damage',
                action.source_id, redirected_to, action.amount, action.nature, action.card_id,
                action.related_action_id, getattr(action, 'propagated', False),
                getattr(action, 'ignore_armor', False),
                getattr(action, 'material_card_ids', ()), True,
                getattr(action, 'card_kind', ''), getattr(action, 'wine_enhanced', False),
                getattr(action, 'virtual_card', None)))
        if frame.step_index == 12:
            redirected_to = frame.local['tianxiang_target']
            if (state.status is not GameStatus.FINISHED and state.players[redirected_to].is_alive):
                missing = max(0, state.players[redirected_to].max_hp - state.players[redirected_to].hp)
                if missing:
                    frame.step_index = 13
                    return StepResult.push(DrawCardsAction(action.action_id + ':tianxiang-draw',
                        redirected_to, missing))
            return StepResult.complete(frame.child_result)
        if frame.step_index == 13:
            return StepResult.complete()
        if frame.step_index == 8:
            remaining = int(frame.local['kuanggu_remaining']) - 1
            frame.local['kuanggu_remaining'] = remaining
            source = action.source_id
            if remaining and source is not None and state.players[source].is_alive:
                return StepResult.push(RecoverAction(
                    f'{action.action_id}:kuanggu:{int(frame.local["amount"]) - remaining}', source, source, 1))
            frame.step_index = 1
            if target.hp <= 0:
                self.recorder.record(DyingRequiredEvent(action.action_id + ':dying', action.target_id, target.hp))
                return StepResult.push(DyingAction(action.action_id + ':rescue', action.target_id, source))
            return StepResult.continue_()
        if frame.step_index == 5:
            requested = frame.decision is True
            frame.decision = None
            frame.step_index = 1
            frame.local['jianxiong_offered'] = True
            if requested:
                materials = getattr(action,'material_card_ids',()) or ((action.card_id,) if action.card_id else ())
                for index, cid in enumerate(dict.fromkeys(materials)):
                    ref = next((ref for ref, zone in state.zones.items() if cid in zone.card_ids), None)
                    if ref is not None and ref.zone_type in (ZoneType.PROCESSING, ZoneType.DISCARD_PILE):
                        self.moves.move(state,CardMove(f'{action.action_id}:jianxiong:{index}',(cid,),ref,
                            ZoneRef(ZoneType.HAND,action.target_id),CardMoveReason.SYSTEM,action.target_id))
        if frame.step_index == 6:
            wanted = frame.decision is True
            frame.decision = None
            frame.local['fankui_offered'] = True
            frame.step_index = 1
            if wanted:
                source = action.source_id
                from .military_equipment import discardable
                cards = discardable(state, source) if source is not None and state.players[source].is_alive else ()
                if cards:
                    frame.step_index = 7
                    return StepResult.ask(PendingRequest(action.action_id+':fankui-card',action.target_id,
                        RequestType.CHOOSE_CARD,'【反馈】选择获得伤害来源的一张牌',action.action_id,frame.frame_id,
                        eligible_card_ids=cards,subject_player_id=source))
        if frame.step_index == 7:
            cid = frame.decision
            frame.decision = None
            source = action.source_id
            from .military_equipment import discardable
            if source is not None and cid in discardable(state, source):
                ref = next(ref for ref, zone in state.zones.items() if cid in zone.card_ids)
                destination = ZoneRef(ZoneType.HAND, action.target_id)
                if ref != destination:
                    self.moves.move(state,CardMove(action.action_id+':fankui-gain',(cid,),ref,
                        destination,CardMoveReason.SYSTEM,action.target_id))
            frame.step_index = 1
        if frame.step_index == 1 and not frame.local.get('jianxiong_offered') and self.skills is not None and self.skills.has(state,action.target_id,'jianxiong') and target.is_alive:
            materials = getattr(action,'material_card_ids',()) or ((action.card_id,) if action.card_id else ())
            obtainable = tuple(cid for cid in dict.fromkeys(materials) if any(cid in zone.card_ids and ref.zone_type in
                (ZoneType.PROCESSING,ZoneType.DISCARD_PILE) for ref,zone in state.zones.items()))
            frame.local['jianxiong_offered'] = True
            if obtainable:
                frame.step_index = 5
                return StepResult.ask(PendingRequest(action.action_id+':jianxiong',action.target_id,
                    RequestType.YES_NO,'【奸雄】是否获得造成伤害的牌？',action.action_id,frame.frame_id))
        if (frame.step_index == 1 and not frame.local.get('fankui_offered') and self.skills is not None
                and self.skills.has(state,action.target_id,'fankui') and target.is_alive
                and action.source_id is not None and state.players[action.source_id].is_alive):
            from .military_equipment import discardable
            frame.local['fankui_offered'] = True
            if discardable(state,action.source_id):
                frame.step_index = 6
                return StepResult.ask(PendingRequest(action.action_id+':fankui',action.target_id,
                    RequestType.YES_NO,'受到伤害，是否发动【反馈】？',action.action_id,frame.frame_id))
        if (frame.step_index == 1 and not frame.local.get('ganglie_offered') and self.skills is not None
                and self.skills.has(state,action.target_id,'ganglie') and target.is_alive
                and action.source_id is not None and action.source_id != action.target_id
                and state.players[action.source_id].is_alive):
            from .skills import GanglieAction
            frame.local['ganglie_offered'] = True
            return StepResult.push(GanglieAction(action.action_id+':ganglie',action.target_id,action.source_id))
        if (frame.step_index == 1 and not frame.local.get('yiji_offered') and self.skills is not None
                and self.skills.has(state,action.target_id,'yiji') and target.is_alive):
            from .skills import YijiAction
            frame.local['yiji_offered'] = True
            return StepResult.push(YijiAction(action.action_id+':yiji',action.target_id,
                                              int(frame.local['amount'])))
        if (frame.step_index == 1 and not frame.local.get('jieming_offered') and self.skills is not None
                and self.skills.has(state, action.target_id, 'jieming') and target.is_alive):
            from .fire import JiemingAction
            frame.local['jieming_offered'] = True
            return StepResult.push(JiemingAction(action.action_id + ':jieming',
                action.target_id, int(frame.local['amount'])))
        if (frame.step_index == 1 and not frame.local.get('fangzhu_offered')
                and self.skills is not None and target.is_alive
                and self.skills.has(state, action.target_id, 'fangzhu')):
            from .forest import FangzhuAction
            frame.local['fangzhu_offered'] = True
            return StepResult.push(FangzhuAction(action.action_id + ':fangzhu', action.target_id))
        if frame.step_index == 14:
            wanted = frame.decision is True
            frame.decision = None
            frame.step_index = 1
            if wanted and target.marks.get('ren', 0) > 0:
                target.marks['ren'] -= 1
                from .forest import FangzhuAction
                return StepResult.push(FangzhuAction(
                    action.action_id + ':jilue-fangzhu', action.target_id))
        if (frame.step_index == 1 and self.skills is not None and target.is_alive
                and not frame.local.get('jilue_fangzhu_offered')
                and self.skills.has(state, action.target_id, 'jilue')
                and not self.skills.has(state, action.target_id, 'fangzhu')
                and target.marks.get('ren', 0) > 0):
            frame.local['jilue_fangzhu_offered'] = True
            frame.step_index = 14
            return StepResult.ask(PendingRequest(
                action.action_id + ':jilue-fangzhu', action.target_id,
                RequestType.YES_NO, '是否弃一枚忍标记发动【极略·放逐】？',
                action.action_id, frame.frame_id))
        if (frame.step_index == 1 and self.skills is not None and target.is_alive
                and self.skills.has(state, action.target_id, 'guixin')
                and frame.local.get('guixin_count', 0) < int(frame.local['amount'])):
            from .gods import GuixinAction
            index = frame.local.get('guixin_count', 0)
            frame.local['guixin_count'] = index + 1
            return StepResult.push(GuixinAction(
                action.action_id + f':guixin:{index}', action.target_id))
        if frame.step_index == 1 and not frame.local.get('baonue_offered'):
            frame.local['baonue_offered'] = True
            source = action.source_id
            if (self.skills is not None and source is not None
                    and state.players[source].is_alive
                    and self.skills.faction(state, source) is Kingdom.QUN):
                lord = next((pid for pid in state.seat_order if pid != source
                             and state.players[pid].is_alive
                             and state.players[pid].identity is Identity.LORD
                             and self.skills.has(state, pid, 'baonue')), None)
                if lord is not None:
                    from .forest import BaonueAction
                    return StepResult.push(BaonueAction(action.action_id + ':baonue', source, lord))
        from .yj2011 import after_damage
        reaction = after_damage(state, frame, self.skills)
        if reaction is not None:
            return reaction
        from .yj2011_tier3 import damage_reaction
        reaction = damage_reaction(state, frame, self.skills)
        if reaction is not None:
            return reaction
        from .yj2013 import damage_reaction as yj2013_damage_reaction
        reaction = yj2013_damage_reaction(state, frame, self.skills)
        if reaction is not None:
            return reaction
        from .yj2012 import damage_reaction as yj2012_damage_reaction
        reaction = yj2012_damage_reaction(state, frame, self.skills)
        if reaction is not None:
            return reaction
        from .zhangliao import damage_reaction as zhangliao_damage_reaction
        god_reaction=zhangliao_damage_reaction(state,frame,self.skills,self.distance.definitions)
        if god_reaction is not None:return StepResult.push(god_reaction)
        chain = str(frame.local['chain']).split('|') if frame.local['chain'] else []
        if state.status is GameStatus.FINISHED or frame.cursor >= len(chain):
            return StepResult.complete(int(frame.local['amount']))
        pid = PlayerId(chain[frame.cursor])
        frame.cursor += 1
        if not state.players[pid].is_alive or not state.players[pid].chained:
            return StepResult.continue_()
        return StepResult.push(MilitaryDamageAction(
            f'{action.action_id}:chain:{frame.cursor}', action.source_id, pid,
            int(frame.local['amount']), action.nature, action.card_id, action.related_action_id,
            propagated=True, card_kind=getattr(action,'card_kind',''),
            wine_enhanced=getattr(action,'wine_enhanced',False), virtual_card=getattr(action,'virtual_card',None)))

@dataclass(frozen=True, slots=True)
class WineAction(Action):
    player_id: PlayerId

class WineHandler:
    def step(self, state, frame):
        state.players[frame.action.player_id].marks['wine'] = 1
        return StepResult.complete()

class WineRule:
    requires_target_selection = False
    def can_use(self, state, user):
        return True
    def target_candidates(self, state, user):
        return ()
    def validate_targets(self, state, user, targets):
        if targets:
            raise InvalidCardUse('wine does not choose a target')
    def usage_limit(self, state, user):
        return 1
    def effect_action(self, action_id, user, card, targets):
        return WineAction(action_id, user)

class SkillSlashLimit:
    def __init__(self, skills):
        self.skills = skills
        self.equipment = EquipmentSlashLimit()

    def limit(self, state, user):
        if self.skills is not None and self.skills.has(state, user, 'paoxiao'):
            return None
        base = self.equipment.limit(state, user)
        from .remaining_gods import camp_bonus
        return None if base is None else base + camp_bonus(state,user,self.skills) + max(0, state.players[user].marks.get('slash_quota_bonus', 0))


class MilitarySlashRule(SlashRule):
    usage_key = 'basic.slash'
    def __init__(self, distance, skills=None):
        super().__init__(ReachableOpponent(distance), SkillSlashLimit(skills))
        self.skills = skills
    def can_use(self, state, user):
        return (state.players[user].marks.get('yj_zishou') != state.turn_number
                and not state.players[user].marks.get('slash_prohibited')
                and state.players[user].marks.get('yj_xianzhen_loss') != state.turn_number)
    def usage_limit(self, state, user):
        from .yj2011_tier3 import scoped_target
        if any(pid != user and state.players[pid].is_alive and scoped_target(state, user, pid)
               for pid in state.seat_order):
            return None
        return super().usage_limit(state, user)
    def target_candidates(self, state, user):
        from .yj2011_tier3 import scoped_target
        marks = state.players[user].marks
        if not self.can_use(state, user):
            return ()
        candidates = (tuple(pid for pid in state.seat_order if pid != user
                           and state.players[pid].is_alive)
                      if marks.get('slash_ignore_distance') else
                      super().target_candidates(state, user))
        scoped = tuple(pid for pid in state.seat_order if pid != user and state.players[pid].is_alive
                       and scoped_target(state, user, pid))
        candidates = tuple(dict.fromkeys((*candidates, *scoped)))
        ordinary_limit = self.limit_provider.limit(state, user)
        if (state.current_player_id == user and state.current_phase is Phase.PLAY and state.play_usage is not None
                and ordinary_limit is not None and state.play_usage.count('basic.slash') >= ordinary_limit):
            candidates = scoped
        if self.skills is None:
            return candidates
        return tuple(pid for pid in candidates if not (
            self.skills.has(state, pid, 'kongcheng') and
            not state.cards_in(ZoneRef(ZoneType.HAND, pid))))
    def target_bounds(self,state,user,card):
        from .yj2011_tier3 import canonical_definition
        maximum = 3 if equipped(state,user,EquipmentSlot.WEAPON)=='equipment.weapon.halberd' and len(state.cards_in(ZoneRef(ZoneType.HAND,user)))==1 else 1
        extra_fire = int(self.skills is not None and self.skills.has(state,user,'lihuo')
                         and (card is None or canonical_definition(state,self.skills,user,state.cards[card].definition_id,card)=='basic.fire_slash'))
        return 1,maximum + extra_fire + max(0, state.players[user].marks.get('slash_extra_targets', 0))
    def validate_targets(self,state,user,targets):
        low,high=self.target_bounds(state,user,None)
        if not low<=len(targets)<=high or len(set(targets))!=len(targets) or any(pid not in self.target_candidates(state,user) for pid in targets):
            raise InvalidCardUse('invalid Slash targets')
    def effect_action(self,aid,user,card,targets):
        return SlashSequence(aid,user,card,targets)

@dataclass(frozen=True,slots=True)
class MilitaryStrike(SlashEffectAction):
    wine_bonus: int = 0
    virtual_card: VirtualCard | None = None

@dataclass(frozen=True,slots=True)
class SlashSequence(Action):
    source_id: str
    card_id: str
    targets: tuple[str,...]
    virtual_card: VirtualCard | None = None

class SlashSequenceHandler:
    def step(self,state,f):
        a=f.action
        if f.step_index==0:
            f.local['wine']=state.players[a.source_id].marks.pop('wine',0)
            f.step_index=1
        if f.cursor>=len(a.targets) or state.status is GameStatus.FINISHED:
            return StepResult.complete()
        target=a.targets[f.cursor]
        f.cursor+=1
        if not state.players[target].is_alive:
            return StepResult.continue_()
        return StepResult.push(MilitaryStrike(f'{a.action_id}:target:{f.cursor}',a.source_id,target,a.card_id,
            'basic.dodge',int(f.local['wine']),a.virtual_card))

class MilitarySlashHandler:
    def liuli_targets(self, state, action, cost):
        owner = action.target_id
        loses_weapon = cost in state.cards_in(ZoneRef(ZoneType.EQUIPMENT, owner, EquipmentSlot.WEAPON))
        loses_horse = cost in state.cards_in(ZoneRef(ZoneType.EQUIPMENT, owner, EquipmentSlot.OFFENSIVE_HORSE))
        reach = 1 if loses_weapon else self.distance.attack_range(state, owner)
        return tuple(pid for pid in state.seat_order
                     if pid not in (action.source_id, owner) and state.players[pid].is_alive
                     and self.distance.distance_between(state, owner, pid) + int(loses_horse) <= reach)

    def step(self, state, frame):
        action = frame.action
        if state.status is GameStatus.FINISHED or not state.players[action.target_id].is_alive:
            return StepResult.complete('prevented')
        from .fire import effective_armor
        armor = effective_armor(state, action.target_id, self.skills)
        weapon = equipped(state, action.source_id, EquipmentSlot.WEAPON)
        card = state.cards.get(action.card_id)
        virtual=getattr(action,'virtual_card',None)
        from .yj2011_tier3 import canonical_definition
        definition=virtual.definition_id if virtual else canonical_definition(
            state, self.skills, action.source_id, card.definition_id,action.card_id)
        color=virtual.color if virtual else effective_color(state, action.card_id, action.source_id)
        nature = DamageNature.FIRE if frame.local.get('fan_fire') else {'basic.fire_slash': DamageNature.FIRE, 'basic.thunder_slash': DamageNature.THUNDER}.get(definition, DamageNature.NORMAL)
        ignore = weapon == 'equipment.weapon.qinggang_sword' or bool(
            state.players[action.source_id].marks.get('wuwei') and
            state.players[action.target_id].marks.get('wuwei_target_' + action.source_id))
        from .yj2011_tier3 import scoped_target, protected
        ignore = ignore or scoped_target(state, action.source_id, action.target_id)
        if frame.step_index == 0:
            if protected(state, action.target_id):
                return StepResult.complete('prevented')
            from .yj2011 import slash_ineffective
            if slash_ineffective(state, self.skills, action.source_id, action.target_id, color):
                return StepResult.complete('prevented')
            if 'amount' not in frame.local:
                wine = action.wine_bonus if isinstance(action,MilitaryStrike) else state.players[action.source_id].marks.pop('wine', 0)
                frame.local['amount'] = 1 + wine
                frame.local['wine_enhanced'] = bool(wine)
            if (self.skills is not None and self.skills.has(state, action.target_id, 'liuli')
                    and not frame.local.get('liuli_offered')):
                from .military_equipment import discardable
                if any(self.liuli_targets(state, action, cid)
                       for cid in discardable(state, action.target_id)):
                    frame.local['liuli_offered'] = True
                    frame.step_index = 21
                    return StepResult.ask(PendingRequest(action.action_id+':liuli', action.target_id,
                        RequestType.YES_NO, '是否发动【流离】弃一张牌，转移【杀】的目标？',
                        action.action_id, frame.frame_id))
            if (self.skills is not None and action.source_id!=action.target_id
                    and not frame.local.get('zhenlie_offered')
                    and self.skills.has(state,action.target_id,'zhenlie')):
                frame.local['zhenlie_offered']=True;frame.step_index=32
                from .yj2012 import YJ2012Action
                return StepResult.push(YJ2012Action(action.action_id+':zhenlie',action.target_id,'zhenlie',action.source_id,
                    card_ids=(action.card_id,),definition_id=definition))
            if (self.skills is not None and self.skills.has(state, action.target_id, 'xiangle')
                    and action.source_id != action.target_id
                    and not frame.local.get('xiangle_handled')):
                from sanguosha.model.enums import CardCategory
                basic = tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, action.source_id))
                              if self.distance.definitions.get(state.cards[cid].definition_id).category
                              is CardCategory.BASIC)
                frame.local['xiangle_handled'] = True
                if not basic:
                    return StepResult.complete('prevented')
                frame.step_index = 28
                return StepResult.ask(PendingRequest(
                    action.action_id + ':xiangle', action.source_id, RequestType.CHOOSE_OPTION,
                    '享乐：弃置一张基本牌，否则此【杀】无效', action.action_id,
                    frame.frame_id, choices=(*basic, 'decline')))
            if not frame.local.get('fan_handled') and weapon=='equipment.weapon.vermilion_fan' and nature is DamageNature.NORMAL:
                frame.local['fan_handled']=True
                frame.step_index=9
                return StepResult.ask(PendingRequest(action.action_id+':fan',action.source_id,RequestType.YES_NO,
                    '是否发动朱雀羽扇，将普通杀转为火杀？',action.action_id,frame.frame_id))
            if self.skills is not None:
                source_gender = self.skills.gender(state, action.source_id)
                target_gender = self.skills.gender(state, action.target_id)
            else:
                genders = state.metadata.get('genders', {})
                source_gender = genders.get(action.source_id, 'male')
                target_gender = genders.get(action.target_id, 'male')
            if (not frame.local.get('double_handled') and weapon=='equipment.weapon.double_sword'
                    and source_gender is not None and target_gender is not None
                    and source_gender != target_gender):
                frame.local['double_handled']=True
                frame.step_index=10
                return StepResult.ask(PendingRequest(action.action_id+':double',action.source_id,RequestType.YES_NO,
                    '是否发动雌雄双股剑？',action.action_id,frame.frame_id))
            if not ignore and (armor == 'equipment.armor.renwang_shield' and color is Color.BLACK
                               or armor == 'equipment.armor.vine' and nature is DamageNature.NORMAL):
                return StepResult.complete('prevented')
            if (self.skills is not None and self.skills.has(state, action.source_id, 'liegong')
                    and state.current_player_id == action.source_id and state.current_phase is Phase.PLAY
                    and not frame.local.get('liegong_offered')):
                hand_count = len(state.cards_in(ZoneRef(ZoneType.HAND, action.target_id)))
                source_hp = state.players[action.source_id].hp
                attack_range = self.distance.attack_range(state, action.source_id)
                frame.local['liegong_offered'] = True
                if hand_count >= source_hp or hand_count <= attack_range:
                    frame.step_index = 25
                    return StepResult.ask(PendingRequest(action.action_id + ':liegong', action.source_id,
                        RequestType.YES_NO, '是否发动【烈弓】令此目标不能使用【闪】？',
                        action.action_id, frame.frame_id, subject_player_id=action.target_id))
            if (self.skills is not None and self.skills.has(state,action.source_id,'tieqi')
                    and not frame.local.get('tieqi_offered')):
                frame.local['tieqi_offered'] = True
                frame.step_index = 19
                return StepResult.ask(PendingRequest(action.action_id+':tieqi',action.source_id,
                    RequestType.YES_NO,'是否发动【铁骑】判定，使目标可能无法闪避？',
                    action.action_id,frame.frame_id))
            if frame.local.get('tieqi_unavoidable') or frame.local.get('no_dodge'):
                frame.child_result = None
                frame.step_index = 3
                return StepResult.continue_()
            frame.step_index = 1
            if armor == 'equipment.armor.eight_trigrams' and not ignore:
                return StepResult.ask(PendingRequest(action.action_id + ':eight-trigrams', action.target_id,
                    RequestType.YES_NO, '是否发动八卦阵判定？', action.action_id, frame.frame_id))
            return StepResult.continue_()
        if frame.step_index == 1:
            use_armor = frame.decision is True
            frame.decision = None
            if use_armor:
                frame.step_index = 2
                return StepResult.push(JudgmentAction(action.action_id + ':judgment', action.target_id,
                    JudgmentPattern(color=Color.RED)))
            frame.step_index = 3
            return StepResult.push(RespondWithCardAction(action.action_id + ':response', action.target_id,
                action.dodge_definition_id, action.action_id, '请打出闪响应杀', action.target_id, False,
                response_total=required_dodge_count(state, action.source_id, action.target_id, self.skills)))
        if frame.step_index == 19:
            wanted = frame.decision is True
            frame.decision = None
            if wanted:
                frame.step_index = 20
                return StepResult.push(JudgmentAction(action.action_id+':tieqi-judge',action.source_id,
                    JudgmentPattern(color=Color.RED)))
            frame.step_index = 0
            return StepResult.continue_()
        if frame.step_index == 25:
            frame.local['no_dodge'] = frame.decision is True
            frame.decision = None
            frame.step_index = 0
            return StepResult.continue_()
        if frame.step_index == 28:
            choice = frame.decision
            frame.decision = None
            if choice == 'decline':
                return StepResult.complete('prevented')
            from sanguosha.model.enums import CardCategory
            if (choice not in state.cards_in(ZoneRef(ZoneType.HAND, action.source_id))
                    or self.distance.definitions.get(state.cards[choice].definition_id).category
                    is not CardCategory.BASIC):
                raise InvalidCardUse('享乐代价不是合法基本牌')
            self.moves.move(state, CardMove(action.action_id + ':xiangle-cost', (choice,),
                ZoneRef(ZoneType.HAND, action.source_id), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.DISCARD, action.source_id, action.action_id))
            frame.step_index = 0
            return StepResult.continue_()
        if frame.step_index == 21:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                frame.step_index = 0
                return StepResult.continue_()
            from .military_equipment import discardable
            frame.step_index = 22
            eligible = tuple(cid for cid in discardable(state, action.target_id)
                             if self.liuli_targets(state, action, cid))
            return StepResult.ask(PendingRequest(action.action_id+':liuli-cost', action.target_id,
                RequestType.CHOOSE_CARD, '流离：选择要弃置的牌', action.action_id,
                frame.frame_id, eligible_card_ids=eligible))
        if frame.step_index == 22:
            card_id = frame.decision
            frame.decision = None
            from .military_equipment import discardable
            if card_id not in discardable(state, action.target_id):
                raise InvalidCardUse('流离弃牌已不可用')
            frame.local['liuli_cost'] = card_id
            targets = self.liuli_targets(state, action, card_id)
            frame.step_index = 23
            return StepResult.ask(PendingRequest(action.action_id+':liuli-target', action.target_id,
                RequestType.CHOOSE_PLAYER, '流离：选择【杀】的新目标', action.action_id,
                frame.frame_id, allowed_player_ids=targets))
        if frame.step_index == 23:
            target = frame.decision
            frame.decision = None
            if target not in self.liuli_targets(state, action, frame.local['liuli_cost']):
                raise InvalidCardUse('流离新目标已不可用')
            cost = frame.local['liuli_cost']
            source = next(ref for ref, zone in state.zones.items() if cost in zone.card_ids)
            self.moves.move(state, CardMove(action.action_id+':liuli-cost', (cost,), source,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, action.target_id))
            frame.step_index = 24
            return StepResult.push(MilitaryStrike(action.action_id+':liuli-strike', action.source_id,
                target, action.card_id, action.dodge_definition_id,
                int(frame.local['amount'])-1, virtual))
        if frame.step_index == 24:
            return StepResult.complete(frame.child_result)
        if frame.step_index == 20:
            frame.local['tieqi_unavoidable'] = frame.child_result is True
            frame.child_result = None
            frame.step_index = 0
            return StepResult.continue_()
        if frame.step_index == 2:
            if frame.child_result is True:
                self.recorder.record(VirtualResponseEvent(action.action_id+':armor-dodge',
                    action.target_id, action.action_id, 'basic.dodge', 1,
                    required_dodge_count(state, action.source_id, action.target_id, self.skills)))
                if required_dodge_count(state, action.source_id, action.target_id, self.skills) == 1:
                    return StepResult.complete('avoided')
                frame.child_result = VirtualCard('basic.dodge',(),None,None)
                frame.step_index = 3
                return StepResult.continue_()
            frame.step_index = 3
            return StepResult.push(RespondWithCardAction(action.action_id + ':response', action.target_id,
                action.dodge_definition_id, action.action_id, '八卦阵未生效，请打出闪', action.target_id, False,
                response_total=required_dodge_count(state, action.source_id, action.target_id, self.skills)))
        if frame.step_index == 3:
            if frame.child_result is not None:
                if required_dodge_count(state, action.source_id, action.target_id, self.skills) > 1 and not frame.local.get('dodge_complete'):
                    frame.local['dodge_complete'] = True
                    frame.step_index = 18
                    return StepResult.push(RespondWithCardAction(action.action_id+':second-dodge',action.target_id,
                        action.dodge_definition_id,action.action_id,'第一张闪已响应，还需第二张闪',
                        action.target_id,not ignore,2,2))
                if (not frame.local.get('mengjin_offered') and self.skills is not None
                        and state.players[action.source_id].is_alive
                        and state.players[action.target_id].is_alive
                        and self.skills.has(state, action.source_id, 'mengjin')):
                    from .fire import MengjinAction, mengjin_choices
                    if mengjin_choices(state, action.target_id):
                        frame.local['mengjin_offered'] = True
                        frame.step_index = 26
                        return StepResult.push(MengjinAction(action.action_id + ':mengjin',
                            action.source_id, action.target_id))
                if weapon=='equipment.weapon.green_dragon_blade':
                    frame.step_index=14
                    return StepResult.push(RespondWithCardAction(action.action_id+':green-dragon',action.source_id,
                        'basic.slash',action.action_id,'青龙偃月刀：继续对同一目标出杀，或放弃',action.target_id))
                if weapon=='equipment.weapon.rock_cleaving_axe':
                    from .military_equipment import discardable
                    costs=discardable(state,action.source_id)
                    if len(costs)>=2:
                        frame.step_index=12
                        return StepResult.ask(PendingRequest(action.action_id+':axe-option',action.source_id,RequestType.YES_NO,
                            '是否发动贯石斧，弃两张牌令杀生效？',action.action_id,frame.frame_id))
                return StepResult.complete('avoided')
            if weapon=='equipment.weapon.ice_sword':
                from .military_equipment import discardable
                if discardable(state,action.target_id):
                    frame.step_index=13
                    return StepResult.ask(PendingRequest(action.action_id+':ice',action.source_id,RequestType.YES_NO,
                        '是否发动寒冰剑，防止伤害并弃置目标两张牌？',action.action_id,frame.frame_id))
            if weapon=='equipment.weapon.ancient_blade' and not state.cards_in(ZoneRef(ZoneType.HAND,action.target_id)):
                frame.local['amount']+=1
            frame.step_index = 4
            return StepResult.push(MilitaryDamageAction(action.action_id + ':damage', action.source_id,
                action.target_id, int(frame.local['amount']), nature, action.card_id, action.action_id,
                ignore_armor=ignore, material_card_ids=virtual.material_ids if virtual else (),
                card_kind='slash', wine_enhanced=bool(frame.local.get('wine_enhanced')), virtual_card=virtual))
        if frame.step_index==32:
            if frame.child_result is True:return StepResult.complete('prevented')
            frame.step_index=0
            return StepResult.continue_()
        if frame.step_index == 26:
            frame.child_result = 'dodged'
            frame.step_index = 3
            return StepResult.continue_()
        if frame.step_index == 18:
            frame.step_index = 3
            return StepResult.continue_()
        if frame.step_index==4:
            if (not frame.local.get('lieren_offered') and self.skills is not None
                    and self.skills.has(state, action.source_id, 'lieren')
                    and state.players[action.source_id].is_alive
                    and state.players[action.target_id].is_alive
                    and isinstance(frame.child_result, int) and frame.child_result > 0
                    and state.cards_in(ZoneRef(ZoneType.HAND, action.source_id))
                    and state.cards_in(ZoneRef(ZoneType.HAND, action.target_id))):
                from .forest import LierenAction
                frame.local['lieren_offered'] = True
                frame.step_index = 27
                return StepResult.push(LierenAction(action.action_id + ':lieren',
                                                    action.source_id, action.target_id))
            horses=any(state.cards_in(ZoneRef(ZoneType.EQUIPMENT,action.target_id,slot)) for slot in (EquipmentSlot.OFFENSIVE_HORSE,EquipmentSlot.DEFENSIVE_HORSE))
            if weapon=='equipment.weapon.kylin_bow' and horses and state.players[action.target_id].is_alive and state.status is not GameStatus.FINISHED:
                frame.step_index=15
                return StepResult.ask(PendingRequest(action.action_id+':kylin',action.source_id,RequestType.YES_NO,
                    '是否发动麒麟弓，弃置目标一张马？',action.action_id,frame.frame_id))
        if frame.step_index == 27:
            frame.step_index = 4
            return StepResult.continue_()
        if frame.step_index==9:
            frame.local['fan_fire']=frame.decision is True
            frame.decision=None
            frame.step_index=0
            return StepResult.continue_()
        if frame.step_index in (10,13,15):
            from .military_equipment import WeaponChoice
            stage=frame.step_index
            yes=frame.decision is True
            frame.decision=None
            if stage==10:
                frame.step_index=11 if yes else 0
            elif stage==13:
                frame.step_index=16 if yes else 3
                if not yes:
                    # Avoid offering the same optional replacement again.
                    frame.step_index=4
                    return StepResult.push(MilitaryDamageAction(action.action_id+':damage',action.source_id,
                        action.target_id,int(frame.local['amount']),nature,action.card_id,action.action_id,
                        card_kind='slash', wine_enhanced=bool(frame.local.get('wine_enhanced')), virtual_card=virtual))
            else:
                frame.step_index=16
            if yes:
                return StepResult.push(WeaponChoice(action.action_id+':weapon-choice',action.source_id,action.target_id,
                    {10:'double_sword',13:'ice_sword',15:'kylin_bow'}[stage]))
            return StepResult.continue_()
        if frame.step_index==11:
            frame.step_index=0
            return StepResult.continue_()
        if frame.step_index==12:
            if frame.decision is not True:
                return StepResult.complete('avoided')
            frame.decision=None
            from .military_equipment import discardable
            frame.step_index=17
            return StepResult.ask(PendingRequest(action.action_id+':axe-cost',action.source_id,RequestType.CHOOSE_CARDS,
                '贯石斧：选择弃置两张牌',action.action_id,frame.frame_id,eligible_card_ids=discardable(state,action.source_id),min_count=2,max_count=2))
        if frame.step_index==17:
            for cid in frame.decision:
                ref=next(ref for ref,z in state.zones.items() if cid in z.card_ids)
                self.moves.move(state,CardMove(action.action_id+':axe:'+cid,(cid,),ref,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,action.source_id))
            frame.decision=None
            frame.step_index=4
            return StepResult.push(MilitaryDamageAction(action.action_id+':forced-damage',action.source_id,action.target_id,int(frame.local['amount']),nature,action.card_id,action.action_id,card_kind='slash', wine_enhanced=bool(frame.local.get('wine_enhanced')), virtual_card=virtual))
        if frame.step_index==14:
            if frame.child_result is None:
                return StepResult.complete('avoided')
            result=frame.child_result
            cid=result.material_ids[0] if isinstance(result,VirtualCard) else str(result)
            frame.step_index=16
            return StepResult.push(MilitaryStrike(action.action_id+':green-dragon-strike',action.source_id,action.target_id,cid,action.dodge_definition_id,virtual_card=result if isinstance(result,VirtualCard) else None))
        return StepResult.complete('hit')

    def __init__(self,moves, skills=None, distance=None, recorder=None):
        self.moves=moves
        self.skills=skills
        self.distance=distance
        self.recorder=recorder

class MilitaryResponseHandler(RespondWithCardHandler):
    """All Slash prints respond as Slash; Wine only saves its own dying owner."""
    def __init__(self, moves, recorder, skills=None):
        super().__init__(moves, recorder)
        self.skills = skills

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 30:
            return StepResult.complete(frame.local['leiji_response'])
        result = self._step_response(state, frame)
        if (result.kind is StepKind.COMPLETE and result.value is not None
                and action.required_definition_id == 'basic.dodge'
                and self.skills is not None and self.skills.has(state, action.player_id, 'leiji')
                and any(pid != action.player_id and state.players[pid].is_alive
                        for pid in state.seat_order)):
            from .wind import LeijiAction
            frame.local['leiji_response'] = (result.value if isinstance(result.value, str)
                                             else 'virtual:leiji-dodge')
            frame.step_index = 30
            return StepResult.push(LeijiAction(action.action_id + ':leiji', action.player_id))
        return result

    def _step_response(self, state, frame):
        action = frame.action
        if frame.step_index == 41:
            return StepResult.complete(VirtualCard('basic.wine', (), None, None))
        if frame.step_index == 12:
            return StepResult.complete(frame.child_result)
        if frame.step_index == 11:
            return StepResult.complete(frame.child_result)
        from .fire import effective_armor
        if frame.step_index == 0 and not frame.local.get('armor_offered') and action.allow_armor and action.required_definition_id=='basic.dodge' and effective_armor(state,action.player_id,self.skills)=='equipment.armor.eight_trigrams':
            frame.local['armor_offered']=True
            frame.step_index=8
            return StepResult.ask(PendingRequest(action.action_id+':armor',action.player_id,RequestType.YES_NO,
                '是否发动八卦阵判定？',action.action_id,frame.frame_id))
        if frame.step_index==8:
            yes=frame.decision is True
            frame.decision=None
            frame.step_index=9 if yes else 0
            if yes:
                return StepResult.push(JudgmentAction(action.action_id+':judgment',action.player_id,JudgmentPattern(color=Color.RED)))
        if frame.step_index==9:
            if frame.child_result is True:
                self.recorder.record(VirtualResponseEvent(action.action_id+':armor-dodge',
                    action.player_id, action.source_action_id, 'basic.dodge',
                    action.response_number, action.response_total))
                return StepResult.complete(VirtualCard('basic.dodge',(),None,None))
            frame.step_index=0
        if frame.step_index == 0:
            hand = state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))
            from .yj2011_tier3 import canonical_definition
            def identity(cid):return canonical_definition(state,self.skills,action.player_id,state.cards[cid].definition_id,cid)
            eligible = tuple(cid for cid in hand if
                identity(cid) == action.required_definition_id
                or action.required_definition_id == 'basic.slash' and identity(cid) in SLASH_IDS
                or action.required_definition_id == 'basic.peach' and action.subject_player_id == action.player_id
                and state.players[action.player_id].hp <= 0 and identity(cid) == 'basic.wine'
                and not (self.skills is not None and self.skills.has(state, action.player_id, 'jinjiu')))
            if self.skills is not None and self.skills.has(state, action.player_id, 'jinjiu') and action.required_definition_id == 'basic.slash':
                eligible += tuple(cid for cid in hand if identity(cid) == 'basic.wine')
            frame.local['eligible'] = '|'.join(eligible)
            if action.required_definition_id=='basic.slash' and equipped(state,action.player_id,EquipmentSlot.WEAPON)=='equipment.weapon.serpent_spear' and len(hand)>=2:
                from .card_limits import legal_pairs
                if legal_pairs(state,action.player_id,hand):eligible=(*eligible,'virtual:spear')
            if self.skills is not None:
                if action.required_definition_id=='basic.slash' and self.skills.has(state,action.player_id,'fuhun'):
                    from .card_limits import legal_pairs
                    if legal_pairs(state,action.player_id,hand):eligible+=('virtual:fuhun',)
                if action.required_definition_id == 'basic.slash':
                    eligible += tuple(f'virtual:wusheng:{cid}' for cid in self.skills.red_slash_materials(state,action.player_id))
                    if self.skills.has(state, action.player_id, 'wushen'):
                        eligible += tuple(f'virtual:wushen:{cid}' for cid in hand
                            if effective_suit(state, cid, action.player_id) is Suit.HEART)
                    if self.skills.has(state,action.player_id,'jijiang') and self.skills.allies(state,action.player_id,Kingdom.SHU):
                        eligible += ('virtual:jijiang',)
                if action.required_definition_id == 'basic.dodge' and self.skills.has(state,action.player_id,'hujia') and self.skills.allies(state,action.player_id,Kingdom.WEI):
                    eligible += ('virtual:hujia',)
                if action.required_definition_id == 'basic.dodge' and self.skills.has(state,action.player_id,'qingguo'):
                    eligible += tuple(f'virtual:qingguo:{cid}' for cid in hand
                                      if effective_color(state, cid, action.player_id) is Color.BLACK)
                if action.required_definition_id == 'basic.peach':
                    wine=state.cards_in(ZoneRef(ZoneType.SPECIAL,action.player_id,special_key='wine'))
                    if self.skills.has(state,action.player_id,'chunlao') and wine:
                        eligible+=tuple('virtual:chunlao:'+cid for cid in wine)
                    if (action.subject_player_id == action.player_id and state.players[action.player_id].hp <= 0
                            and state.players[action.player_id].face_up
                            and self.skills.has(state, action.player_id, 'jiushi')
                            and not self.skills.has(state, action.player_id, 'jinjiu')):
                        eligible += ('virtual:jiushi',)
                    eligible += tuple(f'virtual:jijiu:{cid}' for cid in self.skills.emergency_peach_materials(state,action.player_id))
                    if (action.subject_player_id == action.player_id
                            and state.players[action.player_id].hp <= 0
                            and self.skills.has(state, action.player_id, 'jiuchi')):
                        eligible += tuple(f'virtual:jiuchi:{cid}' for cid in hand
                            if effective_suit(state, cid, action.player_id) is Suit.SPADE)
                if self.skills.has(state,action.player_id,'longdan'):
                    opposite = ('basic.slash' if action.required_definition_id == 'basic.dodge' else
                                'basic.dodge' if action.required_definition_id == 'basic.slash' else None)
                    if opposite:
                        eligible += tuple(f'virtual:longdan:{cid}' for cid in hand
                                          if state.cards[cid].definition_id == opposite)
                if self.skills.has(state, action.player_id, 'guhuo') and hand:
                    from .wind_guhuo import GuhuoAction, GuhuoHandler
                    if GuhuoHandler(self.skills, None, None, None, None).response_definitions_for(
                            state, action.required_definition_id, action.player_id,
                            action.subject_player_id):
                        eligible += ('virtual:guhuo',)
                if (action.required_definition_id == 'trick.nullification'
                        and self.skills.has(state, action.player_id, 'kanpo')):
                    eligible += tuple(f'virtual:kanpo:{cid}' for cid in hand
                        if effective_color(state, cid, action.player_id) is Color.BLACK)
                if self.skills.has(state, action.player_id, 'longhun'):
                    from .gods import longhun_materials, longhun_option
                    transformed = ('basic.fire_slash' if action.required_definition_id == 'basic.slash'
                                   else action.required_definition_id)
                    if transformed in ('basic.fire_slash', 'basic.dodge',
                                       'basic.peach', 'trick.nullification'):
                        eligible += tuple(longhun_option(cards) for cards in
                                          longhun_materials(state, action.player_id, transformed))
            from .card_limits import card_allowed
            def allowed(option):
                if not option.startswith('virtual:'):return card_allowed(state,action.player_id,(option,))
                if option in ('virtual:spear','virtual:fuhun','virtual:jijiang','virtual:hujia','virtual:jiushi'):return True
                if option=='virtual:guhuo':return any(card_allowed(state,action.player_id,(cid,)) for cid in hand)
                materials=tuple(option.split(':')[2:])
                return card_allowed(state,action.player_id,materials)
            eligible=tuple(option for option in eligible if allowed(option))
            frame.local['eligible']='|'.join(option for option in eligible if not option.startswith('virtual:'))
            frame.step_index = 1
            if action.required_definition_id == 'basic.slash' and state.players[action.player_id].marks.get('slash_prohibited'):
                eligible = ()
                frame.local['eligible'] = ''
            return StepResult.ask(PendingRequest(action.action_id + ':request', action.player_id,
                RequestType.RESPOND_WITH_CARD, action.prompt, action.action_id, frame.frame_id,
                required_definition_id=action.required_definition_id, eligible_card_ids=eligible,
                allow_pass=True, subject_player_id=action.subject_player_id))
        # Validate against the same immutable eligibility list, then reuse the
        # physical movement/event contract without changing any card definition.
        from .requests import PASS_RESPONSE
        from .card_moves import CardMove, CardMoveReason
        from .events import CardRespondedEvent
        choice = frame.decision
        frame.decision = None
        if frame.step_index==2:
            if not frame.local.get('fuhun') and equipped(state,action.player_id,EquipmentSlot.WEAPON)!='equipment.weapon.serpent_spear':
                raise InvalidCardUse('spear no longer equipped')
            materials=tuple(choice)
            from dataclasses import replace
            virtual=replace(VirtualCard.spear(state,materials,effective_suit),skill_id=
                            "fuhun" if frame.local.get("fuhun") else "")
            for cid in materials:
                self.moves.move(state,CardMove(action.action_id+':virtual:'+cid,(cid,),ZoneRef(ZoneType.HAND,action.player_id),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.RESPONSE,action.player_id))
                self.recorder.record(CardRespondedEvent(action.action_id+':virtual-responded:'+cid,action.player_id,cid,
                                                        action.source_action_id,'basic.slash'))
            return StepResult.complete(virtual)
        if isinstance(choice,str) and choice.startswith('virtual:chunlao:'):
            cid=choice.split(':',2)[2];wine=ZoneRef(ZoneType.SPECIAL,action.player_id,special_key='wine')
            target=action.subject_player_id
            if cid not in state.cards_in(wine) or not self.skills.has(state,action.player_id,'chunlao') or target not in state.players or state.players[target].hp>0:raise InvalidCardUse('醇醪救援不可用')
            self.moves.move(state,CardMove(action.action_id+':chunlao',(cid,),wine,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM,action.player_id))
            from .events import CardUsedEvent
            virtual=VirtualCard('basic.wine',(),None,None,'chunlao')
            self.recorder.record(CardUsedEvent(action.action_id+':wine-used',target,action.action_id,(target,),'basic.wine',virtual_card=virtual))
            return StepResult.complete(virtual)
        if choice == 'virtual:jiushi':
            if (self.skills is None or not self.skills.has(state, action.player_id, 'jiushi')
                    or not state.players[action.player_id].face_up
                    or action.required_definition_id != 'basic.peach'
                    or action.subject_player_id != action.player_id or state.players[action.player_id].hp > 0):
                raise InvalidCardUse('酒诗自救不可用')
            frame.step_index = 41
            self.recorder.record(VirtualResponseEvent(action.action_id + ':jiushi-response',
                action.player_id, action.source_action_id, 'basic.wine'))
            return StepResult.push(TurnoverAction(action.action_id + ':jiushi-turn', action.player_id))
        if choice in ('virtual:spear','virtual:fuhun'):
            frame.local['fuhun']=choice=='virtual:fuhun'
            from .card_limits import legal_pairs
            frame.step_index=2
            return StepResult.ask(PendingRequest(action.action_id+':spear-cost',action.player_id,RequestType.CHOOSE_CARDS,
                ('【伏魂】' if frame.local['fuhun'] else '丈八蛇矛')+'：选择两张手牌当杀',action.action_id,frame.frame_id,
                eligible_card_ids=state.cards_in(ZoneRef(ZoneType.HAND,action.player_id)),min_count=2,max_count=2,
                legal_card_sets=legal_pairs(state,action.player_id,state.cards_in(ZoneRef(ZoneType.HAND,action.player_id)))))
        if choice == 'virtual:guhuo':
            if (self.skills is None or not self.skills.has(state, action.player_id, 'guhuo')
                    or not state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))):
                raise InvalidCardUse('蛊惑响应不可用')
            from .wind_guhuo import GuhuoAction
            frame.step_index = 12
            return StepResult.push(GuhuoAction(action.action_id + ':guhuo', action.player_id,
                action.required_definition_id, action.source_action_id,
                action.subject_player_id, action.response_number, action.response_total))
        if isinstance(choice,str) and choice.startswith('virtual:wusheng:'):
            material=choice.split(':',2)[2]
            if self.skills is None or material not in self.skills.red_slash_materials(state,action.player_id):
                raise InvalidCardUse('武圣材料不合法')
            card=state.cards[material]
            virtual=VirtualCard('basic.slash',(material,),
                                effective_suit(state, material, action.player_id),
                                effective_color(state, material, action.player_id))
            self.moves.move(state,CardMove(action.action_id+':wusheng-processing',(material,),
                ZoneRef(ZoneType.HAND,action.player_id),ZoneRef(ZoneType.PROCESSING),CardMoveReason.RESPONSE,action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id+':wusheng-responded',action.player_id,material,
                                                    action.source_action_id,'basic.slash'))
            self.moves.move(state,CardMove(action.action_id+':wusheng-discard',(material,),
                ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.RESPONSE,action.player_id))
            return StepResult.complete(virtual)
        if isinstance(choice,str) and choice.startswith('virtual:qingguo:'):
            material=choice.split(':',2)[2]
            if (self.skills is None or not self.skills.has(state,action.player_id,'qingguo')
                    or action.required_definition_id!='basic.dodge' or material not in
                    state.cards_in(ZoneRef(ZoneType.HAND,action.player_id))
                    or effective_color(state, material, action.player_id) is not Color.BLACK):
                raise InvalidCardUse('倾国材料不合法')
            card=state.cards[material]
            virtual=VirtualCard('basic.dodge',(material,),
                                effective_suit(state, material, action.player_id),
                                effective_color(state, material, action.player_id))
            self.moves.move(state,CardMove(action.action_id+':qingguo-processing',(material,),
                ZoneRef(ZoneType.HAND,action.player_id),ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.RESPONSE,action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id+':qingguo-responded',action.player_id,
                material,action.source_action_id,'basic.dodge',action.response_number,action.response_total))
            self.moves.move(state,CardMove(action.action_id+':qingguo-discard',(material,),
                ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.RESPONSE,action.player_id))
            return StepResult.complete(virtual)
        if isinstance(choice,str) and choice.startswith('virtual:kanpo:'):
            material = choice.split(':', 2)[2]
            if (self.skills is None or not self.skills.has(state, action.player_id, 'kanpo')
                    or action.required_definition_id != 'trick.nullification'
                    or material not in state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))
                    or effective_color(state, material, action.player_id) is not Color.BLACK):
                raise InvalidCardUse('看破材料不合法')
            virtual = VirtualCard('trick.nullification', (material,),
                effective_suit(state, material, action.player_id),
                effective_color(state, material, action.player_id))
            self.moves.move(state, CardMove(action.action_id + ':kanpo-processing', (material,),
                ZoneRef(ZoneType.HAND, action.player_id), ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.RESPONSE, action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id + ':kanpo-responded',
                action.player_id, material, action.source_action_id,
                'trick.nullification', action.response_number, action.response_total))
            self.moves.move(state, CardMove(action.action_id + ':kanpo-discard', (material,),
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.RESPONSE, action.player_id))
            return StepResult.complete(virtual)
        if isinstance(choice, str) and choice.startswith('virtual:wushen:'):
            material = choice.split(':', 2)[2]
            if (self.skills is None or not self.skills.has(state, action.player_id, 'wushen')
                    or action.required_definition_id != 'basic.slash'
                    or material not in state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))
                    or effective_suit(state, material, action.player_id) is not Suit.HEART):
                raise InvalidCardUse('武神响应材料不合法')
            virtual = VirtualCard('basic.slash', (material,),
                effective_suit(state, material, action.player_id),
                effective_color(state, material, action.player_id))
            self.moves.move(state, CardMove(action.action_id + ':wushen-processing', (material,),
                ZoneRef(ZoneType.HAND, action.player_id), ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.RESPONSE, action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id + ':wushen-responded',
                action.player_id, material, action.source_action_id, 'basic.slash',
                action.response_number, action.response_total))
            self.moves.move(state, CardMove(action.action_id + ':wushen-discard', (material,),
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.RESPONSE, action.player_id))
            return StepResult.complete(virtual)
        if isinstance(choice, str) and choice.startswith('virtual:longhun:'):
            from .gods import longhun_materials
            materials = tuple(choice.split(':')[2:])
            transformed = ('basic.fire_slash' if action.required_definition_id == 'basic.slash'
                           else action.required_definition_id)
            if (self.skills is None or not self.skills.has(state, action.player_id, 'longhun')
                    or transformed not in ('basic.fire_slash', 'basic.dodge',
                                           'basic.peach', 'trick.nullification')
                    or materials not in longhun_materials(state, action.player_id, transformed)):
                raise InvalidCardUse('龙魂材料不合法')
            virtual = VirtualCard(transformed, materials,
                effective_suit(state, materials[0], action.player_id),
                effective_color(state, materials[0], action.player_id))
            self.moves.move(state, CardMove(action.action_id + ':longhun-processing', materials,
                ZoneRef(ZoneType.HAND, action.player_id), ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.RESPONSE, action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id + ':longhun-responded',
                action.player_id, materials[0], action.source_action_id,
                str(transformed), action.response_number, action.response_total))
            self.moves.move(state, CardMove(action.action_id + ':longhun-discard', materials,
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.RESPONSE, action.player_id))
            return StepResult.complete(virtual)
        if isinstance(choice,str) and choice.startswith('virtual:jijiu:'):
            material=choice.split(':',2)[2]
            if (self.skills is None or action.required_definition_id!='basic.peach'
                    or material not in self.skills.emergency_peach_materials(state,action.player_id)):
                raise InvalidCardUse('急救材料不合法')
            card=state.cards[material]
            virtual=VirtualCard('basic.peach',(material,),
                                effective_suit(state, material, action.player_id),
                                effective_color(state, material, action.player_id))
            source=next(ref for ref,zone in state.zones.items() if material in zone.card_ids)
            self.moves.move(state,CardMove(action.action_id+':jijiu-processing',(material,),
                source,ZoneRef(ZoneType.PROCESSING),CardMoveReason.RESPONSE,action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id+':jijiu-responded',action.player_id,
                material,action.source_action_id,'basic.peach'))
            self.moves.move(state,CardMove(action.action_id+':jijiu-discard',(material,),
                ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.RESPONSE,action.player_id))
            return StepResult.complete(virtual)
        if isinstance(choice, str) and choice.startswith('virtual:jiuchi:'):
            material = choice.split(':', 2)[2]
            if (self.skills is None or not self.skills.has(state, action.player_id, 'jiuchi')
                    or action.required_definition_id != 'basic.peach'
                    or action.subject_player_id != action.player_id
                    or state.players[action.player_id].hp > 0
                    or material not in state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))
                    or effective_suit(state, material, action.player_id) is not Suit.SPADE):
                raise InvalidCardUse('酒池自救材料不合法')
            virtual = VirtualCard('basic.wine', (material,),
                effective_suit(state, material, action.player_id),
                effective_color(state, material, action.player_id))
            self.moves.move(state, CardMove(action.action_id + ':jiuchi-processing',
                (material,), ZoneRef(ZoneType.HAND, action.player_id),
                ZoneRef(ZoneType.PROCESSING), CardMoveReason.RESPONSE, action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id + ':jiuchi-responded',
                action.player_id, material, action.source_action_id, 'basic.wine',
                action.response_number, action.response_total))
            self.moves.move(state, CardMove(action.action_id + ':jiuchi-discard',
                (material,), ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.RESPONSE, action.player_id))
            return StepResult.complete(virtual)
        if isinstance(choice,str) and choice.startswith('virtual:longdan:'):
            material=choice.split(':',2)[2]
            opposite = ('basic.slash' if action.required_definition_id == 'basic.dodge' else
                        'basic.dodge' if action.required_definition_id == 'basic.slash' else None)
            if (self.skills is None or not self.skills.has(state,action.player_id,'longdan')
                    or opposite is None or material not in state.cards_in(ZoneRef(ZoneType.HAND,action.player_id))
                    or state.cards[material].definition_id != opposite):
                raise InvalidCardUse('龙胆材料不合法')
            card=state.cards[material]
            virtual=VirtualCard(action.required_definition_id,(material,),
                                effective_suit(state, material, action.player_id),
                                effective_color(state, material, action.player_id))
            self.moves.move(state,CardMove(action.action_id+':longdan-processing',(material,),
                ZoneRef(ZoneType.HAND,action.player_id),ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.RESPONSE,action.player_id))
            self.recorder.record(CardRespondedEvent(action.action_id+':longdan-responded',action.player_id,
                material,action.source_action_id,action.required_definition_id,
                action.response_number,action.response_total))
            self.moves.move(state,CardMove(action.action_id+':longdan-discard',(material,),
                ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.RESPONSE,action.player_id))
            return StepResult.complete(virtual)
        if choice in ('virtual:hujia','virtual:jijiang'):
            from .skills import AllianceResponse
            faction=Kingdom.WEI if choice=='virtual:hujia' else Kingdom.SHU
            if self.skills is None or not self.skills.has(state,action.player_id,choice.split(':')[1]) or not self.skills.allies(state,action.player_id,faction):
                raise InvalidCardUse('主公技响应不合法')
            frame.step_index=11
            return StepResult.push(AllianceResponse(action.action_id+':alliance',action.player_id,
                action.required_definition_id,action.source_action_id,faction))
        if choice is PASS_RESPONSE:
            return StepResult.complete()
        if choice not in str(frame.local['eligible']).split('|') or choice not in state.cards_in(ZoneRef(ZoneType.HAND, action.player_id)):
            raise InvalidCardUse('response no longer eligible')
        card = CardInstanceId(choice)
        processing = ZoneRef(ZoneType.PROCESSING)
        self.moves.move(state, CardMove(action.action_id + ':processing', (card,),
            ZoneRef(ZoneType.HAND, action.player_id), processing, CardMoveReason.RESPONSE, action.player_id))
        from .yj2011_tier3 import canonical_definition
        self.recorder.record(CardRespondedEvent(action.action_id + ':responded', action.player_id, card,
                                                action.source_action_id,
                                                canonical_definition(state, self.skills, action.player_id, state.cards[card].definition_id,card),
                                                action.response_number, action.response_total))
        self.moves.move(state, CardMove(action.action_id + ':discard', (card,), processing,
            ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.RESPONSE, action.player_id))
        return StepResult.complete(str(card))

class MilitaryFinishBody:
    def step(self, state, frame):
        state.players[frame.action.player_id].marks.pop('wine', None)
        state.players[frame.action.player_id].marks.pop('luoyi', None)
        return StepResult.complete()

def register_military_basics(definitions, rules, registry, moves, events, bodies, skills=None):
    register_additional_definitions(definitions)
    distance = DistanceSystem(definitions)
    for definition in SLASH_IDS:
        rule = MilitarySlashRule(distance, skills)
        if definition == 'basic.slash':
            rules.replace(definition, rule)
        else:
            rules.register(definition, rule)
    rules.register('basic.wine', WineRule())
    register_equipment_rules(definitions, rules)
    registry.register(WineAction, WineHandler())
    registry.register(SlashEffectAction, MilitarySlashHandler(moves, skills, distance, events))
    registry.register(MilitaryStrike, MilitarySlashHandler(moves, skills, distance, events))
    registry.register(SlashSequence, SlashSequenceHandler())
    from .military_equipment import WeaponChoice,WeaponChoiceHandler
    registry.register(WeaponChoice,WeaponChoiceHandler(moves))
    handler = MilitaryDamageHandler(events, moves, skills, definitions)
    registry.register(DamageAction, handler)
    registry.register(MilitaryDamageAction, handler)
    registry.register(RespondWithCardAction, MilitaryResponseHandler(moves, events, skills))
    registry.register(JudgmentAction, JudgmentHandler(moves, events))
    registry.register(EquipCardAction, EquipCardHandler(moves, definitions))
    bodies.register(Phase.FINISH, MilitaryFinishBody())
