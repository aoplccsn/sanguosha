"""YJ2013 actions on the shared resumable resolution stack."""
from dataclasses import dataclass
from .actions import Action, StepResult
from .deck import DrawCardsAction
from .events import CardUsedEvent, TurnStartedEvent
from .requests import RequestType
from .yj2011_tier3 import YJSkillHandler
from sanguosha.model.virtual_card import VirtualCard

@dataclass(frozen=True, slots=True)
class YJ2013Action(Action):
    player_id: str
    skill: str
    opponent_id: str | None = None
    card_id: str | None = None
    event_id: str = ''
    slash_counted: bool = False
    virtual_card: VirtualCard | None = None

def cards_used_this_turn(events, player_id):
    count = 0
    for event in reversed(events):
        if isinstance(event, TurnStartedEvent):
            break
        if isinstance(event, CardUsedEvent) and event.player_id == player_id:
            count += 1
    return count

class YJ2013Handler(YJSkillHandler):
    def step(self, state, frame):
        action = frame.action
        if action.skill=='fencheng' and frame.step_index>0:
            from sanguosha.model.state import GameStatus
            return StepResult.complete() if state.status is GameStatus.FINISHED else self.fencheng(state,frame)
        if action.skill in ('junxing','mieji') and frame.step_index==0:
            self.validate_active(state,action)
        if not state.players[action.player_id].is_alive or not self.skills.has(state, action.player_id, action.skill):
            return StepResult.complete()
        return super().step(state,frame)

    def qiaoshui(self,state,f):
        from .yj2011_tier3 import hand
        from .pindian import PindianAction
        a=f.action;pid=a.player_id
        targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive and hand(state,q))
        if f.step_index==0:
            if not hand(state,pid) or not targets:return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【巧说】是否与另一名角色拼点？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【巧说】选择拼点目标',allowed_player_ids=targets)
        if f.step_index==2:
            target,f.decision=f.decision,None;f.step_index=3
            return StepResult.push(PindianAction(a.action_id+':pindian',pid,target))
        key='qiaoshui_success' if f.child_result is True else 'qiaoshui_trick_lock'
        state.players[pid].marks[key]=state.turn_number
        return StepResult.complete()

    def zhuikong(self,state,f):
        from .yj2011_tier3 import hand
        from .pindian import PindianAction
        a=f.action;pid=a.player_id;target=a.opponent_id;p=state.players[pid]
        if target not in state.players or not state.players[target].is_alive or pid==target:return StepResult.complete()
        if f.step_index==0:
            if p.hp>=p.max_hp or not hand(state,pid) or not hand(state,target):return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【惴恐】是否与回合角色拼点？',subject_player_id=target)
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return StepResult.push(PindianAction(a.action_id+':pindian',pid,target))
        if f.child_result is True:
            state.players[target].marks['zhuikong_self_only']=state.turn_number
        else:
            state.metadata.setdefault('zhuikong_distance',{})[target+':'+pid]={'source':target,'target':pid,'turn':state.turn_number}
        return StepResult.complete()

    def qiuyuan(self,state,f):
        from .yj2011_tier3 import hand,canonical_definition
        from .fuhuanghou import add_slash_target,slash_window
        from .events import Event
        a=f.action;pid=a.player_id;source=a.opponent_id
        targets=tuple(q for q in state.seat_order if q not in (pid,source) and state.players[q].is_alive)
        if f.step_index==0:
            if not targets:return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【求援】是否令另一名角色交给你闪，否则成为此杀的目标？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【求援】选择除杀使用者和你以外的一名角色',allowed_player_ids=targets,min_count=1,max_count=1)
        if f.step_index==2:
            target,f.decision=f.decision,None;f.local['asked']=target
            from .response import dodge_gift_options
            cards=tuple(dodge_gift_options(state,self.skills,target))
            f.step_index=3
            if cards:return self.ask(f,RequestType.CHOOSE_CARDS,'【求援】交出一张闪，或空选成为杀的目标',player=target,subject_player_id=pid,eligible_card_ids=cards,min_count=0,max_count=1)
            f.decision=()
        target=f.local['asked'];cards,f.decision=tuple(f.decision),None
        if cards:
            from sanguosha.model.zones import ZoneRef,ZoneType
            from .response import dodge_gift_options
            options=dodge_gift_options(state,self.skills,target)
            if cards[0] not in options:raise ValueError('求援的闪材料已不可用')
            self.transfer(state,a,options[cards[0]],ZoneRef(ZoneType.HAND,pid),actor=target)
        elif add_slash_target(state,a.event_id,source,target,self.skills):
            w=slash_window(state,a.event_id)
            self.moves.recorder.record(Event(a.action_id+':added','slash_target_added',pid,(target,),metadata={'skill_id':'qiuyuan','root_action_id':a.event_id}))
        return StepResult.complete()

    def xiansi(self,state,f):
        from .military_equipment import discardable
        from sanguosha.model.zones import ZoneRef,ZoneType
        a=f.action;pid=a.player_id
        if f.step_index==0:
            targets=tuple(q for q in state.seat_order if state.players[q].is_alive and discardable(state,q))
            if not targets:return StepResult.complete()
            f.local['targets']=targets;f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【陷嗣】是否将一至两名角色的牌置为逆？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYERS,'【陷嗣】选择一至两名有手牌或装备的角色',allowed_player_ids=f.local['targets'],min_count=1,max_count=2)
        if f.step_index==2:
            chosen,f.decision=tuple(f.decision),None
            f.local['chosen']=tuple(q for q in state.seat_order if q in chosen);f.step_index=3
        if f.step_index==4:
            card,f.decision=f.decision,None
            self.transfer(state,a,(card,),counter_zone(pid))
            f.cursor+=1;f.step_index=3
            return StepResult.continue_()
        while f.cursor<len(f.local['chosen']):
            target=f.local['chosen'][f.cursor];cards=discardable(state,target)
            if not state.players[target].is_alive or not cards:f.cursor+=1;continue
            f.step_index=4
            return self.ask(f,RequestType.CHOOSE_CARD,'【陷嗣】选择一张牌置为逆',eligible_card_ids=cards,subject_player_id=target)
        return StepResult.complete()

    def mieji(self,state,f):
        from itertools import combinations
        from sanguosha.model.enums import CardCategory,Color
        from sanguosha.model.zones import ZoneRef,ZoneType
        from .yj2011_tier3 import hand
        from .suits import effective_color
        from .military_equipment import discardable
        from .card_moves import CardMove,CardMoveReason
        from .card_rules import InvalidCardUse
        a=f.action;pid=a.player_id
        if f.step_index==0:
            cards=tuple(c for c in hand(state,pid) if self.category(state,c) is CardCategory.TRICK and effective_color(state,c,pid) is Color.BLACK)
            if not cards:raise InvalidCardUse('灭计需要黑色锦囊手牌')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_CARD,'【灭计】将一张黑色锦囊置于牌堆顶',eligible_card_ids=cards)
        if f.step_index==1:
            f.local['card'],f.decision=f.decision,None
            targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive and hand(state,q))
            if not targets:raise InvalidCardUse('灭计没有合法目标')
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【灭计】选择有手牌的其他角色',allowed_player_ids=targets,min_count=1,max_count=1)
        if f.step_index==2:
            target,f.decision=f.decision,None;f.local['target']=target
            card=f.local['card'];state.play_usage.record('skill.mieji')
            self.moves.move(state,CardMove(a.action_id+':top',(card,),ZoneRef(ZoneType.HAND,pid),ZoneRef(ZoneType.DRAW_PILE),CardMoveReason.SYSTEM,pid,a.action_id,to_top=True))
            f.step_index=3
            return StepResult.continue_()
        if f.step_index==3:
            target=f.local['target'];cards=discardable(state,target)
            tricks=tuple(c for c in cards if self.category(state,c) is CardCategory.TRICK)
            other=tuple(c for c in cards if c not in tricks)
            legal=tuple((c,) for c in tricks)+tuple(combinations(other,2))
            if not legal and len(other)==1:legal=(other,)
            if not legal:return StepResult.complete()
            f.step_index=4
            return self.ask(f,RequestType.CHOOSE_CARDS,'【灭计】弃一张锦囊或两张非锦囊',player=target,eligible_card_ids=cards,min_count=1,max_count=2,legal_card_sets=legal)
        cards,f.decision=tuple(f.decision),None
        self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,actor=f.local['target'])
        return StepResult.complete()

    def zhiyan(self,state,f):
        from sanguosha.model.enums import CardCategory
        from .events import Event
        from .recovery import RecoverAction
        from .card_use import UseCardAction
        from .card_limits import card_allowed
        from .yj2011_tier3 import hand
        from sanguosha.model.zones import ZoneRef,ZoneType
        a=f.action;pid=a.player_id
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【直言】是否令一名角色摸牌并展示？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【直言】选择摸牌的角色',allowed_player_ids=tuple(q for q in state.seat_order if state.players[q].is_alive),min_count=1,max_count=1)
        if f.step_index==2:
            target,f.decision=f.decision,None;f.local['target']=target
            if not self.deck.ensure_draw(state,a.action_id+':ensure'):return StepResult.complete()
            f.local['card']=state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
            f.step_index=3
            return StepResult.push(DrawCardsAction(a.action_id+':draw',target,1))
        target=f.local['target'];card=f.local['card']
        if not state.players[target].is_alive:return StepResult.complete()
        if f.step_index==3:
            if card not in hand(state,target):return StepResult.complete()
            self.moves.recorder.record(Event(a.action_id+':reveal','card_revealed',target,metadata={'card_id':card}))
            if self.category(state,card) is not CardCategory.EQUIPMENT:return StepResult.complete()
            f.step_index=4
            return StepResult.push(RecoverAction(a.action_id+':recover',pid,target,1))
        if f.step_index==4:
            f.step_index=5
            if card in hand(state,target) and card_allowed(state,target,(card,)):
                return StepResult.push(UseCardAction(a.action_id+':equip',target,card,forced=True))
        return StepResult.complete()

    def danshou(self,state,f):
        from copy import deepcopy
        from sanguosha.model.enums import Phase
        from sanguosha.model.zones import ZoneRef,ZoneType
        from .military_equipment import discardable
        from .card_moves import CardMoveReason
        from .military_basics import MilitaryDamageAction
        from .card_rules import InvalidCardUse
        a=f.action;pid=a.player_id
        if f.step_index==0:
            if state.current_player_id!=pid or state.current_phase is not Phase.PLAY:raise InvalidCardUse('胆守仅出牌阶段发动')
            n=state.play_usage.count('skill.danshou')+1;cards,groups=danshou_cost_choices(state,pid,self.definitions)
            if len(cards)-sum(len(group)-1 for group in groups)<n:raise InvalidCardUse('胆守无合法成本或目标')
            f.local['n']=n;f.step_index=1
            return self.ask(f,RequestType.CHOOSE_CARDS,f'【胆守】弃置{n}张手牌或装备',eligible_card_ids=cards,min_count=n,max_count=n,exclusive_card_groups=groups)
        if f.step_index==1:
            cards,f.decision=tuple(f.decision),None;f.local['cards']=cards
            after=deepcopy(state)
            for zone in after.zones.values():zone.card_ids[:]=[c for c in zone.card_ids if c not in cards]
            targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive and self.authorized.distance.can_reach_with_slash(after,pid,q))
            if not targets:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【胆守】选择支付成本后仍在攻击范围内的角色',allowed_player_ids=targets,min_count=1,max_count=1)
        if f.step_index==2:
            target,f.decision=f.decision,None;f.local['target']=target
            self.transfer(state,a,f.local['cards'],ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            state.play_usage.record('skill.danshou');f.step_index=3
            return StepResult.continue_()
        target=f.local['target'];n=f.local['n']
        if f.step_index==3:
            if not state.players[target].is_alive:return StepResult.complete()
            f.step_index=4
            if n<=2:
                cards=discardable(state,target)
                if not cards:return StepResult.complete()
                return self.ask(f,RequestType.CHOOSE_CARD,'【胆守】'+('弃置目标一张牌' if n==1 else '交给技能来源一张牌'),player=pid if n==1 else target,eligible_card_ids=cards,subject_player_id=target)
            if n==3:return StepResult.push(MilitaryDamageAction(a.action_id+':damage',pid,target,1))
            return StepResult.push(DrawCardsAction(a.action_id+':draw-self',pid,2))
        if f.step_index==4 and n<=2:
            card,f.decision=f.decision,None
            self.transfer(state,a,(card,),ZoneRef(ZoneType.DISCARD_PILE) if n==1 else ZoneRef(ZoneType.HAND,pid),CardMoveReason.DISCARD if n==1 else CardMoveReason.SYSTEM,actor=target if n==2 else pid)
            return StepResult.complete()
        if f.step_index==4 and n>=4 and state.players[target].is_alive:
            f.step_index=5
            return StepResult.push(DrawCardsAction(a.action_id+':draw-target',target,2))
        return StepResult.complete()

    def fencheng(self,state,f):
        from sanguosha.model.enums import Phase,DamageNature
        from sanguosha.model.zones import ZoneRef,ZoneType
        from .military_equipment import discardable
        from .card_moves import CardMoveReason
        from .military_basics import MilitaryDamageAction
        from .card_rules import InvalidCardUse
        a=f.action;pid=a.player_id
        if f.step_index==0:
            if state.current_player_id!=pid or state.current_phase is not Phase.PLAY or state.players[pid].marks.get('fencheng_used'):raise InvalidCardUse('焚城不可用')
            state.players[pid].marks['fencheng_used']=1
            start=state.seat_order.index(pid)
            f.local['targets']=state.seat_order[start+1:]+state.seat_order[:start]
            f.local['threshold']=1;f.step_index=1
        targets=f.local['targets']
        if f.step_index==2:
            paid,f.decision=tuple(f.decision),None
            target=targets[f.cursor]
            if paid:
                self.transfer(state,a,paid,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,actor=target)
                f.local['threshold']=len(paid)+1;f.cursor+=1;f.step_index=1
                return StepResult.continue_()
            f.local['threshold']=1;f.cursor+=1;f.step_index=1
            return StepResult.push(MilitaryDamageAction(a.action_id+':damage:'+target,pid,target,2,DamageNature.FIRE))
        while f.cursor<len(targets) and not state.players[targets[f.cursor]].is_alive:f.cursor+=1
        if f.cursor>=len(targets):return StepResult.complete()
        target=targets[f.cursor];cards=discardable(state,target);threshold=f.local['threshold']
        if len(cards)<threshold:
            f.local['threshold']=1;f.cursor+=1
            return StepResult.push(MilitaryDamageAction(a.action_id+':damage:'+target,pid,target,2,DamageNature.FIRE))
        f.step_index=2
        # Empty tuple means decline. Intermediate undersized payments are illegal.
        return self.ask(f,RequestType.CHOOSE_CARDS,f'【焚城】弃置至少{threshold}张牌，否则受到两点火焰伤害',player=target,eligible_card_ids=cards,min_count=0,max_count=len(cards),minimum_nonempty_count=threshold)

    def longyin(self,state,f):
        from sanguosha.model.enums import Phase,Color
        from sanguosha.model.zones import ZoneRef,ZoneType
        from .military_equipment import discardable
        from .card_moves import CardMoveReason
        from .suits import effective_color
        a=f.action;pid=a.player_id;source=a.opponent_id
        if state.current_phase is not Phase.PLAY:return StepResult.complete()
        if f.step_index==0:
            if not discardable(state,pid):return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【龙吟】是否弃一张牌令此杀不计次数？红色杀可摸一张牌',subject_player_id=source)
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted or not discardable(state,pid):return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_CARD,'【龙吟】选择弃牌成本',eligible_card_ids=discardable(state,pid))
        if f.step_index==2:
            cost,f.decision=f.decision,None
            color=a.virtual_card.color if a.virtual_card else effective_color(state,a.card_id,source) if a.card_id in state.cards else None
            self.transfer(state,a,(cost,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            ignored=state.metadata.setdefault('longyin_ignored_events',[])
            usage=state.play_usage
            if a.event_id not in ignored:
                ignored.append(a.event_id)
                if a.slash_counted and usage is not None and usage.player_id==source:
                    usage.counts['basic.slash']=max(0,usage.count('basic.slash')-1)
            f.step_index=3
            if color is Color.RED:return StepResult.push(DrawCardsAction(a.action_id+':draw',pid,1))
        return StepResult.complete()

    def category(self,state,cid):
        from sanguosha.model.enums import CardCategory
        c=self.definitions.get(state.cards[cid].definition_id).category
        return CardCategory.TRICK if c is CardCategory.DELAYED_TRICK else c

    def junxing(self,state,f):
        from sanguosha.model.zones import ZoneRef,ZoneType
        from .yj2011_tier3 import hand
        from .card_moves import CardMoveReason
        from .card_rules import InvalidCardUse
        from .turnover import TurnoverAction
        a=f.action;pid=a.player_id
        if f.step_index==0:
            self.validate_active(state,a)
            if not hand(state,pid):raise InvalidCardUse('junxing requires hand cost')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_CARDS,'【峻刑】选择弃置的手牌',eligible_card_ids=hand(state,pid),min_count=1,max_count=len(hand(state,pid)))
        if f.step_index==1:
            costs,f.decision=tuple(f.decision),None
            f.local['costs']=costs;f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【峻刑】选择其他角色',allowed_player_ids=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive))
        if f.step_index==2:
            target,f.decision=f.decision,None;costs=f.local['costs']
            self.validate_active(state,a)
            if not costs or any(c not in hand(state,pid) for c in costs):raise InvalidCardUse('junxing cost became unavailable')
            f.local.update(target=target,types=tuple(set(self.category(state,c) for c in costs)))
            state.play_usage.record('skill.junxing')
            self.transfer(state,a,costs,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            f.step_index=3
            return StepResult.continue_()
        target=f.local['target']
        if not state.players[target].is_alive:return StepResult.complete()
        if f.step_index==3:
            eligible=tuple(c for c in hand(state,target) if self.category(state,c) not in f.local['types'])
            f.step_index=4
            if eligible:return self.ask(f,RequestType.CHOOSE_CARDS,'【峻刑】弃一张不同类别手牌，或翻面摸牌',player=target,eligible_card_ids=eligible,min_count=0,max_count=1,subject_player_id=pid)
            f.decision=()
        if f.step_index==4:
            cards,f.decision=tuple(f.decision),None
            if cards:
                self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,actor=target)
                return StepResult.complete()
            f.step_index=5
            return StepResult.push(TurnoverAction(a.action_id+':turnover',target))
        if f.step_index==5:
            f.step_index=6
            return StepResult.push(DrawCardsAction(a.action_id+':draw',target,len(f.local['costs'])))
        return StepResult.complete()

    def yuce(self,state,f):
        from sanguosha.model.zones import ZoneRef,ZoneType
        from .yj2011_tier3 import hand
        from .card_moves import CardMoveReason
        from .events import Event
        from .recovery import RecoverAction
        a=f.action;pid=a.player_id;source=a.opponent_id
        if f.step_index==0:
            if not hand(state,pid):return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【御策】是否展示一张手牌？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted or not hand(state,pid):return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_CARD,'【御策】选择展示的手牌',eligible_card_ids=hand(state,pid))
        if f.step_index==2:
            card,f.decision=f.decision,None
            self.moves.recorder.record(Event(a.action_id+':reveal','card_revealed',pid,metadata={'card_id':card}))
            category=self.category(state,card);f.step_index=3
            eligible=tuple(c for c in hand(state,source) if self.category(state,c)!=category) if source in state.players and state.players[source].is_alive else ()
            if eligible:return self.ask(f,RequestType.CHOOSE_CARDS,'【御策】弃一张不同类别手牌，或令受伤角色回复',player=source,eligible_card_ids=eligible,min_count=0,max_count=1,subject_player_id=pid)
            f.decision=()
        if f.step_index==3:
            cards,f.decision=tuple(f.decision),None;f.step_index=4
            if cards:
                self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,actor=source)
                return StepResult.complete()
            return StepResult.push(RecoverAction(a.action_id+':recover',pid,pid,1))
        return StepResult.complete()

    def renxin(self,state,f):
        from sanguosha.model.enums import EquipmentSlot
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMoveReason
        from .military_equipment import discardable
        from .turnover import TurnoverAction
        a=f.action;pid=a.player_id;target=a.opponent_id
        def costs():
            return tuple(c for c in discardable(state,pid) if self.definitions.get(state.cards[c].definition_id).equipment_slot is not None)
        if target not in state.players or not state.players[target].is_alive or state.players[target].hp!=1:
            return StepResult.complete(False)
        if f.step_index==0:
            if target==pid or not costs():return StepResult.complete(False)
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【仁心】是否保护体力为一的其他角色？',subject_player_id=target)
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted or not costs():return StepResult.complete(False)
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_CARD,'【仁心】弃置一张装备牌',eligible_card_ids=costs())
        if f.step_index==2:
            cost,f.decision=f.decision,None
            if cost not in costs():raise ValueError('renxin cost became unavailable')
            self.transfer(state,a,(cost,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            f.step_index=3
            return StepResult.push(TurnoverAction(a.action_id+':turnover',pid))
        return StepResult.complete(True)

    def chengxiang(self,state,f):
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .deck import RevealTopCardsAction
        from .card_moves import CardMoveReason
        a=f.action;pid=a.player_id
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【称象】是否亮出四张牌并获得点数和不超过十三的牌？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return StepResult.push(RevealTopCardsAction(a.action_id+':reveal',pid,4))
        if f.step_index==2:
            f.local['revealed']=tuple(f.child_result);f.local['selected']=();f.step_index=3
        if f.step_index==4:
            card,f.decision=f.decision,None
            f.local['selected']=(*f.local['selected'],card);f.cursor+=1;f.step_index=5
        if f.step_index==6:
            choice,f.decision=f.decision,None
            f.step_index=3 if choice=='continue' else 7
        selected=f.local['selected'];remaining=13-sum(state.cards[c].rank for c in selected)
        eligible=tuple(c for c in f.local['revealed'] if c not in selected and state.cards[c].rank<=remaining)
        if f.step_index==3:
            if eligible:
                f.step_index=4
                return self.ask(f,RequestType.CHOOSE_CARD,'【称象】选择一张点数合法的牌',eligible_card_ids=eligible)
            f.step_index=7
        if f.step_index==5:
            if eligible:
                f.step_index=6
                return self.ask(f,RequestType.CHOOSE_OPTION,'【称象】继续选牌或结束',choices=('continue','finish'))
            f.step_index=7
        if selected:self.transfer(state,a,selected,ZoneRef(ZoneType.HAND,pid))
        rest=tuple(c for c in f.local['revealed'] if c not in selected)
        if rest:self.transfer(state,a,rest,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM)
        return StepResult.complete()

    def juece(self,state,f):
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .military_basics import MilitaryDamageAction
        a=f.action; pid=a.player_id
        targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive
            and not state.cards_in(ZoneRef(ZoneType.HAND,q)))
        if f.step_index==0:
            if not targets: return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【绝策】是否对无手牌角色造成一点伤害？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted or not targets:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【绝策】选择无手牌目标',allowed_player_ids=targets)
        if f.step_index==2:
            target,f.decision=f.decision,None
            if target not in targets: return StepResult.complete()
            f.step_index=3
            return StepResult.push(MilitaryDamageAction(a.action_id+':damage',pid,target,1))
        return StepResult.complete()

    def duodao(self,state,f):
        from sanguosha.model.enums import EquipmentSlot
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMoveReason
        from .military_equipment import discardable
        a=f.action; pid=a.player_id; source=a.opponent_id
        def weapon():
            return state.cards_in(ZoneRef(ZoneType.EQUIPMENT,source,EquipmentSlot.WEAPON)) if source in state.players and state.players[source].is_alive else ()
        if f.step_index==0:
            costs=discardable(state,pid)
            if not costs: return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【夺刀】是否弃一张牌获得伤害来源的武器？',subject_player_id=source)
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted or not discardable(state,pid): return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_CARD,'【夺刀】选择弃牌成本',eligible_card_ids=discardable(state,pid))
        if f.step_index==2:
            cost,f.decision=f.decision,None
            self.transfer(state,a,(cost,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            f.step_index=3
            return StepResult.continue_()
        cards=weapon()
        if cards: self.transfer(state,a,cards,ZoneRef(ZoneType.HAND,pid))
        return StepResult.complete()

    def jingce(self,state,frame):
        action=frame.action
        if frame.step_index == 0:
            if cards_used_this_turn(self.moves.recorder.events, action.player_id) < state.players[action.player_id].hp:
                return StepResult.complete()
            frame.step_index = 1
            return self.ask(frame, RequestType.YES_NO, '【精策】是否摸两张牌？')
        if frame.step_index == 1:
            wanted, frame.decision = frame.decision is True, None
            frame.step_index = 2
            if wanted:
                return StepResult.push(DrawCardsAction(action.action_id + ':draw', action.player_id, 2))
        return StepResult.complete()

@dataclass(frozen=True,slots=True)
class LongyinWindow(Action):
    player_id: str
    event: CardUsedEvent
    owners: tuple[str,...]

class LongyinWindowHandler:
    def step(self,state,f):
        a=f.action;e=a.event
        if f.cursor>=len(a.owners):return StepResult.complete()
        owner=a.owners[f.cursor];f.cursor+=1
        if not state.players[owner].is_alive:return StepResult.continue_()
        return StepResult.push(YJ2013Action(a.action_id+':'+owner,owner,'longyin',e.player_id,e.card_id,
            e.event_id,e.slash_counted,e.virtual_card))

def register(registry, skills, moves, definitions, deck):
    from .zongxuan import PendingDiscard,PendingDiscardHandler
    registry.register(PendingDiscard,PendingDiscardHandler(moves,skills))
    from .qiaoshui import QiaoshuiTargets,QiaoshuiTargetsHandler
    registry.register(QiaoshuiTargets,QiaoshuiTargetsHandler(skills,definitions,moves.recorder))
    registry.register(YJ2013Action, YJ2013Handler(skills, moves, definitions, deck))
    registry.register(LongyinWindow,LongyinWindowHandler())
    registry.register(XiansiSlashAction,XiansiSlashHandler(skills,moves,definitions,deck))


def damage_reaction(state,frame,skills):
    a=frame.action
    if (frame.step_index==1 and not frame.local.get('yj2013_yuce') and skills is not None
            and state.players[a.target_id].is_alive and skills.has(state,a.target_id,'yuce')):
        frame.local['yj2013_yuce']=True
        return StepResult.push(YJ2013Action(a.action_id+':yuce',a.target_id,'yuce',a.source_id))
    if (frame.step_index==1 and not frame.local.get('yj2013_chengxiang') and skills is not None
            and state.players[a.target_id].is_alive and skills.has(state,a.target_id,'chengxiang')):
        frame.local['yj2013_chengxiang']=True
        return StepResult.push(YJ2013Action(a.action_id+':chengxiang',a.target_id,'chengxiang'))
    if (frame.step_index==1 and not frame.local.get('yj2013_duodao') and skills is not None
            and state.players[a.target_id].is_alive and getattr(a,'card_kind','')=='slash'
            and skills.has(state,a.target_id,'duodao')):
        frame.local['yj2013_duodao']=True
        return StepResult.push(YJ2013Action(a.action_id+':duodao',a.target_id,'duodao',a.source_id))
    return None



def danshou_cost_choices(state,pid,definitions):
    """Cost choices must leave a living target in the post-cost attack range."""
    from copy import copy
    from .distance import DistanceSystem
    from .military_equipment import discardable
    from sanguosha.model.enums import EquipmentSlot
    from sanguosha.model.zones import ZoneType
    distance=DistanceSystem(definitions)
    cards=discardable(state,pid)
    relevant=tuple(c for ref,zone in state.zones.items() if ref.player_id==pid and ref.zone_type is ZoneType.EQUIPMENT
        and ref.equipment_slot in (EquipmentSlot.WEAPON,EquipmentSlot.OFFENSIVE_HORSE) for c in zone.card_ids if c in cards)
    def reachable(removed):
        after=copy(state);after.zones=dict(state.zones)
        for ref,zone in state.zones.items():
            if ref.player_id==pid and ref.zone_type is ZoneType.EQUIPMENT and any(c in removed for c in zone.card_ids):
                after.zones[ref]=copy(zone);after.zones[ref].card_ids=[c for c in zone.card_ids if c not in removed]
        return any(q!=pid and state.players[q].is_alive and distance.can_reach_with_slash(after,pid,q) for q in state.seat_order)
    if not reachable(()):return (),()
    protected={c for c in relevant if not reachable((c,))}
    cards=tuple(c for c in cards if c not in protected)
    optional=tuple(c for c in relevant if c not in protected)
    groups=(optional,) if len(optional)>1 and not reachable(optional) else ()
    return cards,groups

def play_options(state,pid,skills,definitions=None):
    from .yj2011_tier3 import hand
    from .military_equipment import discardable
    options=[]
    from sanguosha.model.enums import Color
    from .suits import effective_color
    if skills.has(state,pid,'mieji') and not state.play_usage.count('skill.mieji') and any(q!=pid and state.players[q].is_alive and hand(state,q) for q in state.seat_order) and any(state.cards[c].definition_id.startswith(('trick.','delayed.')) and effective_color(state,c,pid) is Color.BLACK for c in hand(state,pid)):options.append('skill:mieji')
    if skills.has(state,pid,'fencheng') and not state.players[pid].marks.get('fencheng_used'):options.append('skill:fencheng')
    if skills.has(state,pid,'danshou'):
        cards,groups=danshou_cost_choices(state,pid,definitions)
        capacity=len(cards)-sum(len(group)-1 for group in groups)
        if capacity>=state.play_usage.count('skill.danshou')+1:options.append('skill:danshou')
    return options + (['skill:junxing'] if (skills.has(state,pid,'junxing') and state.play_usage is not None
        and not state.play_usage.count('skill.junxing') and hand(state,pid)
        and any(q!=pid and state.players[q].is_alive for q in state.seat_order)) else [])


def event_reactions(state,event,skills):
    from sanguosha.model.enums import Phase
    if (not isinstance(event,CardUsedEvent) or state.current_phase is not Phase.PLAY
            or state.current_player_id!=event.player_id):return ()
    definition=event.virtual_definition_id or (state.cards[event.card_id].definition_id if event.card_id in state.cards else '')
    if definition not in ('basic.slash','basic.fire_slash','basic.thunder_slash'):return ()
    owners=tuple(q for q in state.seat_order if state.players[q].is_alive and skills.has(state,q,'longyin'))
    return (LongyinWindow(event.event_id+':longyin-window',event.player_id,event,owners),) if owners else ()


def counter_zone(pid):
    from sanguosha.model.zones import ZoneRef,ZoneType
    return ZoneRef(ZoneType.SPECIAL,pid,special_key='counter')

@dataclass(frozen=True,slots=True)
class XiansiSlashAction(Action):
    player_id: str
    opponent_id: str

class XiansiSlashHandler(YJSkillHandler):
    def __init__(self,skills,moves,definitions,deck):
        from .yj2011_tier3 import AuthorizedVirtualUseHandler
        self.skills,self.moves,self.definitions,self.deck=skills,moves,definitions,deck
        self.authorized=AuthorizedVirtualUseHandler(skills,definitions,moves.recorder if moves is not None else None)

    def rule(self):
        from .military_basics import MilitarySlashRule
        return MilitarySlashRule(self.authorized.distance,self.skills)

    def available(self,state,pid,target):
        from sanguosha.model.enums import Phase
        return (state.players[pid].is_alive and state.current_player_id==pid and state.current_phase is Phase.PLAY
            and state.play_usage is not None and target!=pid and state.players[target].is_alive
            and self.skills.has(state,target,'xiansi') and len(state.cards_in(counter_zone(target)))>=2
            and target in self.rule().target_candidates(state,pid))

    def validate_start(self,state,a):
        from .card_rules import InvalidCardUse
        if not self.available(state,a.player_id,a.opponent_id):raise InvalidCardUse('陷嗣杀不可用')

    def step(self,state,f):
        from .card_rules import InvalidCardUse
        from .card_moves import CardMoveReason
        from sanguosha.model.zones import ZoneRef,ZoneType
        from .military_basics import SlashSequence
        from .yj2011_tier3 import record_slash_use
        a=f.action;pid=a.player_id;target=a.opponent_id
        if f.step_index==0:
            self.validate_start(state,a);f.step_index=1
            return self.ask(f,RequestType.CHOOSE_CARDS,'【陷嗣】移去两张逆，视为对其使用杀',eligible_card_ids=state.cards_in(counter_zone(target)),subject_player_id=target,min_count=2,max_count=2)
        if f.step_index==1:
            f.local['cards'],f.decision=tuple(f.decision),None
            # The counter cards are costs, not virtual Slash materials. Halberd and Lihuo do not add targets.
            extra=max(0,state.players[pid].marks.get('slash_extra_targets',0))
            candidates=tuple(q for q in self.rule().target_candidates(state,pid) if q!=target)
            f.step_index=2
            if extra and candidates:
                return self.ask(f,RequestType.CHOOSE_PLAYERS,'【陷嗣】选择杀的额外目标（可不选）',allowed_player_ids=candidates,min_count=0,max_count=min(extra,len(candidates)))
            f.decision=()
        if f.step_index==2:
            if not self.available(state,pid,target):raise InvalidCardUse('陷嗣杀目标已失效')
            cards=f.local['cards']
            if any(c not in state.cards_in(counter_zone(target)) for c in cards):raise InvalidCardUse('逆已失效')
            additional,f.decision=tuple(f.decision),None
            targets=tuple(q for q in state.seat_order if q==target or q in additional)
            self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM)
            virtual=VirtualCard('basic.slash',(),None,None,'xiansi')
            counted=record_slash_use(state,pid,targets)
            self.moves.recorder.record(CardUsedEvent(a.action_id+':used',pid,a.action_id,targets,'basic.slash',slash_counted=counted,virtual_card=virtual))
            f.step_index=3
            return StepResult.push(SlashSequence(a.action_id+':slash',pid,a.action_id,targets,virtual))
        return StepResult.complete(f.child_result)
