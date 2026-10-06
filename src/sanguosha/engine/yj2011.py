"""Locked YJ2011 skills. Development catalogue remains outside production draft."""
from dataclasses import dataclass

from sanguosha.model.enums import Color, EquipmentSlot, Phase, CardCategory
from sanguosha.model.zones import ZoneRef, ZoneType
from .actions import Action, StepResult
from .requests import PendingRequest, RequestType
from .deck import DrawCardsAction
from .turnover import TurnoverAction
from .hp import LoseHpAction
from .card_moves import CardMove, CardMoveReason
from .military_equipment import discardable


def slash_ineffective(state, skills, source, target, color):
    """Effect immunity, not target prohibition; Qinggang does not disable 毅重."""
    return (skills is not None and skills.has(state, target, 'yizhong')
            and not state.cards_in(ZoneRef(ZoneType.EQUIPMENT, target, EquipmentSlot.ARMOR))
            and color is Color.BLACK)


@dataclass(frozen=True, slots=True)
class PojunAction(Action):
    player_id: str
    target_id: str


class PojunHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        a = frame.action
        if (not self.skills.has(state, a.player_id, 'pojun')
                or not state.players[a.player_id].is_alive
                or not state.players[a.target_id].is_alive):
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                a.action_id + ':offer', a.player_id, RequestType.YES_NO,
                '【破军】是否令目标摸至多五张牌并翻面？', a.action_id,
                frame.frame_id, subject_player_id=a.target_id,
                choices=(f'draw:{max(0, min(state.players[a.target_id].hp, 5))}',)))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(
                a.action_id + ':draw', a.target_id,
                max(0, min(state.players[a.target_id].hp, 5))))
        if frame.step_index == 2:
            frame.step_index = 3
            return StepResult.push(TurnoverAction(a.action_id + ':turn', a.target_id))
        return StepResult.complete()


def after_damage(state, frame, skills):
    a = frame.action
    if (frame.step_index == 1 and not frame.local.get('yj2011_pojun')
            and skills is not None and a.source_id is not None
            and getattr(a, 'card_kind', '') == 'slash'
            and not getattr(a, 'propagated', False)
            and state.players[a.source_id].is_alive
            and state.players[a.target_id].is_alive
            and skills.has(state, a.source_id, 'pojun')):
        frame.local['yj2011_pojun'] = True
        return StepResult.push(PojunAction(a.action_id + ':pojun', a.source_id, a.target_id))
    return None


def register_yj2011(registry, skills, moves, definitions):
    registry.register(PojunAction, PojunHandler(skills))
    registry.register(ShangshiAction, ShangshiHandler(skills))
    registry.register(XuanfengAction, XuanfengHandler(skills, moves))
    registry.register(JujianAction, JujianHandler(skills, moves, definitions))


def replace_damage(state, frame, skills, events):
    """Replace damage before any target damage prevention or elemental copy."""
    if frame.step_index == 90:
        return StepResult.complete(0)  # No damage was dealt; child handled HP/dying.
    if frame.step_index != 0 or skills is None:
        return None
    from .damage_cards import damage_definition
    a = frame.action
    if a.source_id is not None and skills.has(state, a.source_id, 'jueqing'):
        from .events import Event
        amount = a.amount
        source = state.players[a.source_id]
        if (state.current_player_id == a.source_id and source.marks.get('luoyi')
                and not getattr(a, 'propagated', False)
                and damage_definition(state, a) in
                    ('basic.slash','basic.fire_slash','basic.thunder_slash','trick.duel')):
            amount += 1
        events.record(Event(a.action_id + ':jueqing', 'damage_replaced_by_hp_loss',
                            a.source_id, (a.target_id,), {'amount':amount,'skill_id':'jueqing'}))
        frame.step_index = 90
        return StepResult.push(LoseHpAction(a.action_id + ':hp-loss', a.target_id, amount))
    # The locked 无言 archive says trick damage, including delayed tricks.
    is_trick = damage_definition(state, a).startswith(('trick.', 'delayed.'))
    if is_trick and (skills.has(state,a.target_id,'wuyan')
                     or a.source_id is not None and skills.has(state,a.source_id,'wuyan')):
        return StepResult.complete(0)
    return None


@dataclass(frozen=True, slots=True)
class ShangshiAction(Action):
    player_id: str


class ShangshiHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self,state,frame):
        a=frame.action; player=state.players[a.player_id]
        missing=max(0,player.max_hp-player.hp)-len(state.cards_in(ZoneRef(ZoneType.HAND,a.player_id)))
        if not player.is_alive or not self.skills.has(state,a.player_id,'shangshi') or missing<=0:
            return StepResult.complete()
        if frame.step_index==0:
            frame.step_index=1
            return StepResult.ask(PendingRequest(a.action_id+':offer',a.player_id,RequestType.YES_NO,
                '【伤逝】是否将手牌补至已损失体力值？',a.action_id,frame.frame_id,choices=(f'draw:{missing}',)))
        if frame.step_index==1:
            wanted=frame.decision is True; frame.decision=None
            if not wanted: return StepResult.complete()
            frame.step_index=2
            return StepResult.push(DrawCardsAction(a.action_id+':draw',a.player_id,missing))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class XuanfengAction(Action):
    player_id: str


class XuanfengHandler:
    def __init__(self,skills,moves): self.skills,self.moves=skills,moves

    def step(self,state,frame):
        a=frame.action
        if not state.players[a.player_id].is_alive or not self.skills.has(state,a.player_id,'xuanfeng'):
            return StepResult.complete()
        targets=tuple(pid for pid in state.seat_order if pid!=a.player_id
                      and state.players[pid].is_alive and discardable(state,pid))
        if not targets or frame.cursor>=2: return StepResult.complete()
        if frame.step_index==0:
            frame.step_index=1
            return StepResult.ask(PendingRequest(f'{a.action_id}:offer:{frame.cursor}',a.player_id,
                RequestType.YES_NO,'【旋风】是否弃置其他角色的一张牌？',a.action_id,frame.frame_id))
        if frame.step_index==1:
            wanted=frame.decision is True; frame.decision=None
            if not wanted: return StepResult.complete()
            frame.step_index=2
            return StepResult.ask(PendingRequest(f'{a.action_id}:target:{frame.cursor}',a.player_id,
                RequestType.CHOOSE_PLAYER,'【旋风】选择弃牌目标',a.action_id,frame.frame_id,allowed_player_ids=targets))
        if frame.step_index==2:
            target=frame.decision; frame.decision=None; frame.local['target']=target; frame.step_index=3
            return StepResult.ask(PendingRequest(f'{a.action_id}:card:{frame.cursor}',a.player_id,
                RequestType.CHOOSE_CARD,'【旋风】选择弃置目标的一张牌',a.action_id,frame.frame_id,
                eligible_card_ids=discardable(state,target),subject_player_id=target))
        cid=frame.decision; frame.decision=None; target=frame.local['target']
        if cid in discardable(state,target):
            ref=next(ref for ref,z in state.zones.items() if cid in z.card_ids)
            self.moves.move(state,CardMove(f'{a.action_id}:discard:{frame.cursor}',(cid,),ref,
                ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,a.player_id,a.action_id))
        frame.cursor+=1; frame.step_index=0
        return StepResult.continue_()


def event_reactions(state,event,skills,recorder):
    """Only event-authorized owners are inspected; no catalogue-wide dispatch."""
    from .events import CardMovedEvent, AfterDamageEvent, HpRecoveredEvent, Event, PhaseEndedEvent, phase_rule_discards
    dirty=[]; reactions=[]
    if isinstance(event,CardMovedEvent):
        dirty=[ref.player_id for ref in (event.from_zone,event.to_zone)
               if ref.zone_type is ZoneType.HAND and ref.player_id is not None]
        owner=event.from_zone.player_id
        if (event.from_zone.zone_type is ZoneType.EQUIPMENT and owner is not None
                and not (event.related_action_id or '').startswith('equipment-exchange:')
                and state.players[owner].is_alive and skills.has(state,owner,'xuanfeng')):
            reactions.append(XuanfengAction(event.event_id+':xuanfeng',owner))
    elif isinstance(event,Event) and event.event_type == 'equipment_departure_batch':
        owner=event.source_id
        if state.players[owner].is_alive and skills.has(state,owner,'xuanfeng'):
            reactions.append(XuanfengAction(event.event_id+':xuanfeng',owner))
    elif isinstance(event,(AfterDamageEvent,HpRecoveredEvent)):
        dirty=[event.target_id]
    elif isinstance(event,Event) and event.event_type in ('hp_lost','max_hp_lost','max_hp_gained'):
        dirty=[event.source_id]
    elif isinstance(event,PhaseEndedEvent) and event.phase is Phase.DISCARD:
        owner=event.player_id
        phase_id=event.event_id.removesuffix(':end')
        cards=phase_rule_discards(recorder.events,phase_id,owner)
        if len(cards)>=2 and state.players[owner].is_alive and skills.has(state,owner,'xuanfeng'):
            reactions.append(XuanfengAction(event.event_id+':xuanfeng',owner))
    for owner in dict.fromkeys(dirty):
        if owner is not None and state.players[owner].is_alive and skills.has(state,owner,'shangshi'):
            p=state.players[owner]
            if len(state.cards_in(ZoneRef(ZoneType.HAND,owner)))<max(0,p.max_hp-p.hp):
                reactions.append(ShangshiAction(event.event_id+':shangshi:'+owner,owner))
    return reactions


@dataclass(frozen=True, slots=True)
class JujianAction(Action):
    player_id: str


class JujianHandler:
    def __init__(self,skills,moves,definitions): self.skills,self.moves,self.definitions=skills,moves,definitions

    def materials(self,state,pid):
        return tuple(cid for cid in discardable(state,pid)
                     if self.definitions.get(state.cards[cid].definition_id).category is not CardCategory.BASIC)

    def step(self,state,frame):
        a=frame.action
        if not state.players[a.player_id].is_alive or not self.skills.has(state,a.player_id,'jujian'):
            return StepResult.complete()
        if frame.step_index==0:
            if not self.materials(state,a.player_id): return StepResult.complete()
            frame.step_index=1
            return StepResult.ask(PendingRequest(a.action_id+':offer',a.player_id,RequestType.YES_NO,
                '【举荐】是否弃一张非基本牌帮助另一名角色？',a.action_id,frame.frame_id))
        if frame.step_index==1:
            wanted=frame.decision is True; frame.decision=None
            if not wanted: return StepResult.complete()
            frame.step_index=2
            return StepResult.ask(PendingRequest(a.action_id+':cost',a.player_id,RequestType.CHOOSE_CARD,
                '【举荐】选择弃置一张非基本牌',a.action_id,frame.frame_id,
                eligible_card_ids=self.materials(state,a.player_id)))
        if frame.step_index==2:
            cid=frame.decision; frame.decision=None
            if cid not in self.materials(state,a.player_id): return StepResult.complete()
            frame.local['material']=cid
            targets=tuple(pid for pid in state.seat_order if pid!=a.player_id and state.players[pid].is_alive)
            if not targets: return StepResult.complete()
            frame.step_index=3
            return StepResult.ask(PendingRequest(a.action_id+':target',a.player_id,RequestType.CHOOSE_PLAYER,
                '【举荐】选择受益角色',a.action_id,frame.frame_id,allowed_player_ids=targets))
        if frame.step_index==3:
            target=frame.decision; frame.decision=None; frame.local['target']=target
            cid=frame.local['material']
            if cid not in self.materials(state,a.player_id): return StepResult.complete()
            ref=next(ref for ref,z in state.zones.items() if cid in z.card_ids)
            self.moves.move(state,CardMove(a.action_id+':discard',(cid,),ref,ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.DISCARD,a.player_id,a.action_id))
            frame.step_index=4
            return StepResult.continue_()
        target=frame.local['target']; p=state.players[target]
        if not p.is_alive: return StepResult.complete()
        if frame.step_index==4:
            choices=('draw',)+ (('recover',) if p.hp<p.max_hp else ()) + (('reset',) if p.chained or not p.face_up else ())
            frame.step_index=5
            return StepResult.ask(PendingRequest(a.action_id+':benefit',target,RequestType.CHOOSE_OPTION,
                '【举荐】选择摸两张牌、回复体力或解除连环并翻正',a.action_id,frame.frame_id,choices=choices))
        if frame.step_index==5:
            choice=frame.decision; frame.decision=None; frame.step_index=6
            if choice=='draw': return StepResult.push(DrawCardsAction(a.action_id+':draw',target,2))
            if choice=='recover':
                from .recovery import RecoverAction
                return StepResult.push(RecoverAction(a.action_id+':recover',a.player_id,target,1))
            from .chaining import set_chained
            set_chained(state,target,False,self.skills)
            if not p.face_up: return StepResult.push(TurnoverAction(a.action_id+':reset',target))
        return StepResult.complete()
