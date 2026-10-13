"""Mobile boundary Wei Yan, Zhu Ran and Fa Zheng on existing skill frames."""
from dataclasses import dataclass

from sanguosha.model.enums import Phase
from sanguosha.model.zones import ZoneRef, ZoneType
from .actions import StepResult
from .card_moves import CardMoveReason
from .card_rules import InvalidCardUse
from .deck import DrawCardsAction
from .events import CardUsedEvent, CardMovedEvent, Event, PhaseStartedEvent, TurnStartedEvent, TrickTargetsDeclaredEvent
from .hp import LoseHpAction
from .recovery import RecoverAction
from .requests import RequestType
from .yj2011_tier3 import YJSkillAction, YJSkillHandler, hand
from .military_equipment import discardable


@dataclass(frozen=True, slots=True)
class BoundaryTriggerAction(YJSkillAction):
    pass


class BoundaryTriggerHandler(YJSkillHandler):
    # This official mobile archive retains the classic Fa Zheng rule contract.
    jie_enyuan_gain = YJSkillHandler.enyuan_gain
    jie_enyuan_damage = YJSkillHandler.enyuan_damage
    def jie_xuanhuo(self, state, f):
        from .response import RespondWithCardAction
        from .events import CardUsedEvent, CardResolvedEvent
        from .military_basics import SlashSequence
        from sanguosha.model.virtual_card import VirtualCard
        a=f.action
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【眩惑】是否放弃正常摸牌并令另一角色摸两张？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete(False)
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【眩惑】选择摸牌角色',
                allowed_player_ids=tuple(q for q in state.seat_order if q!=a.player_id and state.players[q].is_alive))
        if f.step_index==2:
            f.local['recipient'],f.decision=f.decision,None
            f.step_index=3
            return StepResult.push(DrawCardsAction(a.action_id+':draw',f.local['recipient'],2))
        pid=f.local['recipient']
        if not state.players[pid].is_alive:return StepResult.complete(True)
        if f.step_index==3:
            targets=self.authorized.candidates(state,pid)
            if targets:
                f.step_index=4
                return self.ask(f,RequestType.CHOOSE_PLAYER,'【眩惑】选择其攻击范围内的杀目标',allowed_player_ids=targets)
            f.step_index=7
        if f.step_index==4:
            f.local['victim'],f.decision=f.decision,None
            f.step_index=5
            return StepResult.push(RespondWithCardAction(a.action_id+':jie-xuanhuo-response',pid,
                'basic.slash',a.action_id,'【眩惑】使用一张杀（可以转换），或让法正获得两张牌',
                f.local['victim'],use_card=True,validate_slash_target=True))
        if f.step_index==5:
            result=f.child_result
            if result is not None:
                virtual=result if isinstance(result,VirtualCard) else VirtualCard(state.cards[result].definition_id,(result,),
                    state.cards[result].suit,state.cards[result].color)
                f.local['materials']=virtual.material_ids
                card=virtual.material_ids[0] if virtual.material_ids else a.action_id
                self.moves.recorder.record(CardUsedEvent(a.action_id+':used',pid,card,(f.local['victim'],),
                    virtual.definition_id,virtual_card=virtual))
                f.step_index=6
                if state.players[f.local['victim']].is_alive:
                    return StepResult.push(SlashSequence(a.action_id+':forced',pid,card,(f.local['victim'],),virtual))
            else:f.step_index=7
        if f.step_index==6:
            materials=tuple(cid for cid in f.local['materials'] if cid in state.cards_in(ZoneRef(ZoneType.PROCESSING)))
            if materials:self.transfer(state,a,materials,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.USE,actor=pid)
            card=f.local['materials'][0] if f.local['materials'] else a.action_id
            self.moves.recorder.record(CardResolvedEvent(a.action_id+':resolved',pid,card))
            return StepResult.complete(True)
        if f.step_index==7:
            selected=f.local.setdefault('selected',[])
            cards=tuple(cid for cid in discardable(state,pid) if cid not in selected)
            if f.cursor>=2 or not cards:
                if selected:self.transfer(state,a,tuple(selected),ZoneRef(ZoneType.HAND,a.player_id))
                return StepResult.complete(True)
            f.step_index=8
            return self.ask(f,RequestType.CHOOSE_CARD,'【眩惑】获得该角色一张牌',eligible_card_ids=cards,subject_player_id=pid)
        cid,f.decision=f.decision,None
        if cid not in discardable(state,pid) or cid in f.local['selected']:raise InvalidCardUse('眩惑取得牌已不可用')
        f.local['selected'].append(cid);f.cursor+=1;f.step_index=7
        return StepResult.continue_()


    def step(self, state, frame):
        actor = frame.action.player_id
        skill = frame.action.skill
        required = 'jie_enyuan' if skill.startswith('jie_enyuan_') else skill
        if not state.players[actor].is_alive or not self.skills.has(state, actor, required):
            return StepResult.complete()
        return super().step(state, frame)

    def jie_kuanggu(self, state, f):
        a = f.action
        p = state.players[a.player_id]
        if f.cursor >= a.amount:
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index = 1
            choices = ('draw', 'decline')
            if p.hp < p.max_hp:
                choices = ('recover', *choices)
            return self.ask(f, RequestType.CHOOSE_OPTION,
                f'【狂骨】第 {f.cursor + 1} 点伤害：回复一点体力、摸一张牌或不发动', choices=choices)
        if f.step_index == 1:
            choice, f.decision = f.decision, None
            f.step_index = 2
            if choice == 'recover':
                return StepResult.push(RecoverAction(a.action_id + f':recover:{f.cursor}', a.player_id, a.player_id, 1))
            if choice == 'draw':
                return StepResult.push(DrawCardsAction(a.action_id + f':draw:{f.cursor}', a.player_id, 1))
        f.cursor += 1
        f.step_index = 0
        return StepResult.continue_()

    def jie_qimou(self, state, f):
        a = f.action
        p = state.players[a.player_id]
        if f.step_index == 0:
            if (p.marks.get('jie_qimou_used') or state.current_player_id != a.player_id
                    or state.current_phase is not Phase.PLAY or state.play_usage is None or p.hp <= 0):
                raise InvalidCardUse('奇谋需要自己的出牌阶段且限定技未消耗')
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_OPTION, '【奇谋】选择失去体力的数量',
                            choices=tuple(str(n) for n in range(1, p.hp + 1)))
        if f.step_index == 1:
            amount, f.decision = int(f.decision), None
            if p.marks.get('jie_qimou_used') or not 1 <= amount <= p.hp:
                raise InvalidCardUse('奇谋数量或限定技状态已不可用')
            p.marks['jie_qimou_used'] = 1
            f.local['amount'] = amount
            f.step_index = 2
            return StepResult.push(LoseHpAction(a.action_id + ':lose-hp', a.player_id, amount))
        p.marks['jie_qimou_amount'] = f.local['amount']
        p.marks['jie_qimou_turn'] = state.turn_number
        return StepResult.complete()

    def jie_danshou(self, state, f):
        from .military_basics import MilitaryDamageAction
        a = f.action
        if a.target_id not in state.players or not state.players[a.target_id].is_alive:
            return StepResult.complete()
        count = a.amount
        if count == 0:
            if f.step_index == 0:
                f.step_index = 1
                return StepResult.push(DrawCardsAction(a.action_id + ':draw', a.player_id, 1))
            return StepResult.complete()
        cards = discardable(state, a.player_id)
        if f.step_index == 0:
            if len(cards) < count:
                return StepResult.complete()
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, f'【胆守】是否弃置 {count} 张牌，对结束阶段角色造成一点伤害？',
                            subject_player_id=a.target_id)
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted or len(cards) < count:
                return StepResult.complete()
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_CARDS, f'【胆守】选择弃置 {count} 张牌',
                            eligible_card_ids=cards, min_count=count, max_count=count)
        if f.step_index == 2:
            costs, f.decision = tuple(f.decision), None
            if len(costs) != count or any(cid not in cards for cid in costs):
                raise InvalidCardUse('胆守弃牌已不可用')
            f.step_index = 3
            self.transfer(state, a, costs, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD)
            return StepResult.continue_()
        if f.step_index == 3:
            f.step_index = 4
            return StepResult.push(MilitaryDamageAction(a.action_id + ':damage', a.player_id, a.target_id, 1))
        return StepResult.complete()

def qimou_amount(state, pid):
    marks = state.players[pid].marks
    return marks.get('jie_qimou_amount', 0) if marks.get('jie_qimou_turn') == state.turn_number else 0


def prepare_damage(state, frame, skills, distance):
    a = frame.action
    source = a.source_id
    if 'jie_kuanggu_in_range' not in frame.local:
        frame.local['jie_kuanggu_in_range'] = bool(source is not None and source != a.target_id
            and state.players[source].is_alive and skills is not None and skills.has(state, source, 'jie_kuanggu')
            and distance.distance_between(state, source, a.target_id) <= 1)


def damage_reaction(state, frame, skills):
    if frame.step_index != 1 or skills is None:
        return None
    a = frame.action
    if not frame.local.get('jie_kuanggu_done'):
        frame.local['jie_kuanggu_done'] = True
        if frame.local.get('jie_kuanggu_in_range') and a.source_id is not None and state.players[a.source_id].is_alive:
            return StepResult.push(BoundaryTriggerAction(a.action_id + ':jie-kuanggu', a.source_id,
                'jie_kuanggu', amount=int(frame.local['amount'])))
    if not frame.local.get('jie_enyuan_done'):
        frame.local['jie_enyuan_done'] = True
        if (state.players[a.target_id].is_alive and a.source_id is not None and a.source_id != a.target_id
                and state.players[a.source_id].is_alive and skills.has(state, a.target_id, 'jie_enyuan')):
            return StepResult.push(BoundaryTriggerAction(a.action_id + ':jie-enyuan', a.target_id,
                'jie_enyuan_damage', a.source_id, amount=int(frame.local['amount'])))
    return None


def event_reactions(state, event, skills, recorder=None):
    if skills is None:
        return ()
    result = []
    if isinstance(event, TurnStartedEvent):
        state.metadata['boundary_target_counts'] = {}
    elif isinstance(event, (CardUsedEvent, TrickTargetsDeclaredEvent)):
        if state.current_player_id == event.player_id:
            counts = state.metadata.setdefault('boundary_target_counts', {})
            for target in set(event.target_ids):
                counts[target] = counts.get(target, 0) + 1
    elif isinstance(event, PhaseStartedEvent) and event.phase is Phase.FINISH:
        for pid in state.seat_order:
            if pid != event.player_id and state.players[pid].is_alive and skills.has(state, pid, 'jie_danshou'):
                count = state.metadata.get('boundary_target_counts', {}).get(pid, 0)
                result.append(BoundaryTriggerAction(event.event_id + ':jie-danshou:' + pid, pid,
                    'jie_danshou', event.player_id, amount=count))
    source = recipient = None
    count = 0
    if isinstance(event, CardMovedEvent):
        source, recipient = event.from_zone.player_id, event.to_zone.player_id
        if event.to_zone.zone_type is ZoneType.HAND and not (event.related_action_id or '').startswith('acquisition:'):
            count = len(event.card_ids)
    elif isinstance(event, Event) and event.event_type == 'cards_obtained':
        source, recipient = event.metadata['from_player_id'], event.source_id
        count = event.metadata['count']
    if (source is not None and recipient is not None and source != recipient and count >= 2
            and state.players[recipient].is_alive and skills.has(state, recipient, 'jie_enyuan')):
        result.append(BoundaryTriggerAction(event.event_id + ':jie-enyuan', recipient, 'jie_enyuan_gain', source))
    return tuple(result)


def play_options(state, pid, skills):
    p = state.players[pid]
    return ['skill:jie_qimou'] if (skills.has(state, pid, 'jie_qimou') and p.hp > 0
        and not p.marks.get('jie_qimou_used')) else []


def clear_turn(state):
    state.metadata.pop('boundary_target_counts', None)
    for player in state.players.values():
        player.marks.pop('jie_qimou_amount', None)
        player.marks.pop('jie_qimou_turn', None)


def register(registry, skills, moves, definitions, deck):
    registry.register(BoundaryTriggerAction, BoundaryTriggerHandler(skills, moves, definitions, deck))

def forced_slash_option_allowed(state, action, option, skills, definitions):
    """Check the declared target after paying known equipment view-as material."""
    from dataclasses import replace
    from sanguosha.model.zones import CardZone
    from .distance import DistanceSystem
    if action.subject_player_id not in state.players or not state.players[action.subject_player_id].is_alive:
        return False
    cards = tuple(cid for cid in option.split(':') if cid in state.cards)
    if option in state.cards:cards=(option,)
    suffix=option.split(':',2)[-1]
    if suffix in state.cards:cards=(suffix,)
    preview=replace(state,zones={ref:CardZone(ref,list(zone.card_ids))
        for ref,zone in state.zones.items()})
    if cards:
        from .card_moves import CardMoveService
        from .events import EventRecorder
        CardMoveService(EventRecorder()).move_owned_materials(preview,cards,action.player_id,
            ZoneRef(ZoneType.PROCESSING),CardMoveReason.USE,'forced-slash-preview')
    from .gods import wushen_applies
    if any(wushen_applies(state,skills,action.player_id,cid) for cid in cards):
        return True
    return DistanceSystem(definitions).can_reach_with_slash(preview,action.player_id,action.subject_player_id)
