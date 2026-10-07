"""Current mobile god skills on the shared resolution stack."""
from dataclasses import dataclass
from .actions import Action, StepResult
from .requests import PendingRequest, RequestType
from .skill_grants import add_grant
from .deck import DrawCardsAction

JILUE_SKILLS = ('guicai', 'fangzhu', 'jizhi', 'zhiheng', 'wansha')
JILUE_FACTION = {'wei': 'fangzhu', 'shu': 'jizhi', 'wu': 'zhiheng', 'qun': 'wansha'}


def initialize_jilue(state, pid, skills):
    """Acquisition grants persist even if the originating Jilue is later lost."""
    acquisitions = state.metadata.setdefault('mobile_jilue_initialized', {})
    if not skills.has(state, pid, 'jilue'):
        acquisitions.pop(pid, None)
        return
    if acquisitions.get(pid):
        return
    acquisitions[pid] = True
    add_grant(state, pid, 'guicai', 'jilue.permanent')
    faction = skills.faction(state, pid)
    if faction in JILUE_FACTION:
        add_grant(state, pid, JILUE_FACTION[faction], 'jilue.permanent')


@dataclass(frozen=True, slots=True)
class MobileGodAction(Action):
    player_id: str
    mode: str
    target_id: str | None = None


class MobileGodHandler:
    def __init__(self, skills, moves, rng):
        self.skills = skills
        self.moves = moves
        self.rng = rng

    def step(self, state, frame):
        action = frame.action
        pid = action.player_id
        player = state.players[pid]
        if not player.is_alive:
            return StepResult.complete()
        if action.mode == 'faction':
            from sanguosha.model.enums import Kingdom
            if frame.step_index == 0:
                frame.step_index = 1
                return StepResult.ask(PendingRequest(action.action_id + ':choice',pid,RequestType.CHOOSE_OPTION,
                    '神将：选择本局势力',action.action_id,frame.frame_id,choices=('wei','shu','wu','qun')))
            state.metadata.setdefault('kingdom_overrides',{})[pid] = Kingdom(frame.decision)
            frame.decision = None
            return StepResult.complete()
        if action.mode in ('huishi', 'tianyi_guojia', 'huishi_guojia', 'zuoxing'):
            return self.guojia(state, frame)
        if action.mode in ('dinghan', 'qizheng'):
            return self.xunyu(state, frame)
        if action.mode in ('powei_start', 'powei_fail', 'shenzhu'):
            return self.taishici(state, frame)
        if action.mode in ('yingba', 'pinghe', 'fuhai_draw', 'fuhai_death'):
            return self.sunce(state, frame)
        if action.mode in ('tamo', 'dingzhou', 'zhimeng'):
            return self.lusu(state, frame)
        if action.mode == 'lianpo':
            return self.lianpo(state, frame)
        if action.mode != 'jilue':
            raise ValueError('unsupported mobile god action')
        if frame.step_index == 0:
            initialize_jilue(state, pid, self.skills)
            if not self.skills.has(state, pid, 'jilue'):
                return StepResult.complete()
            cost = max(2, player.marks.get('jilue_learning_uses', 0) + 1)
            choices = ['cancel']
            if player.marks.get('ren', 0) >= cost:
                choices.extend('learn:' + skill for skill in JILUE_SKILLS
                               if not self.skills.has(state, pid, skill))
            choices.extend('draw:' + str(n) for n in range(1, min(2, player.marks.get('ren', 0)) + 1))
            if len(choices) == 1:
                return StepResult.complete()
            frame.local['cost'] = cost
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':choice', pid, RequestType.CHOOSE_OPTION,
                '极略：永久学习技能或移去至多两枚忍摸牌', action.action_id,
                frame.frame_id, choices=tuple(choices)))
        if frame.step_index == 1:
            choice = frame.decision
            frame.decision = None
            if choice == 'cancel':
                return StepResult.complete()
            if choice.startswith('learn:'):
                skill = choice.split(':', 1)[1]
                cost = frame.local['cost']
                if skill not in JILUE_SKILLS or self.skills.has(state, pid, skill) or player.marks.get('ren', 0) < cost:
                    raise ValueError('illegal Jilue learning')
                player.marks['ren'] -= cost
                player.marks['jilue_learning_uses'] = player.marks.get('jilue_learning_uses', 0) + 1
                add_grant(state, pid, skill, 'jilue.permanent')
                return StepResult.complete()
            count = int(choice.split(':', 1)[1])
            if count not in (1, 2) or player.marks.get('ren', 0) < count:
                raise ValueError('illegal Jilue draw')
            player.marks['ren'] -= count
            frame.step_index = 2
            return StepResult.push(DrawCardsAction(action.action_id + ':draw', pid, count))
        return StepResult.complete()

    def guojia(self, state, frame):
        from .hp import LoseMaxHpAction, GainMaxHpAction
        from .judgment import JudgmentAction, JudgmentPattern
        from .recovery import RecoverAction
        from .suits import effective_suit
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMove, CardMoveReason
        action = frame.action; pid = action.player_id; player = state.players[pid]; mode = action.mode
        living = tuple(q for q in state.seat_order if state.players[q].is_alive)
        if mode == 'huishi':
            if frame.step_index == 0:
                if player.max_hp >= 10 or state.play_usage.count('skill.huishi'): return StepResult.complete()
                state.play_usage.record('skill.huishi'); frame.local.update(cards=[], suits=[])
                frame.step_index = 1
                return StepResult.push(JudgmentAction(action.action_id + ':judge:0', pid, JudgmentPattern(), return_card_id=True, retain_result=True))
            if frame.step_index == 1:
                card = frame.child_result
                if card and card in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
                    frame.local['cards'].append(card)
                    suit = effective_suit(state, card, pid)
                    unique = suit not in frame.local['suits']; frame.local['suits'].append(suit)
                    if unique and player.max_hp < 10:
                        frame.step_index = 2
                        return StepResult.ask(PendingRequest(action.action_id + ':continue:' + str(len(frame.local['cards'])),pid,
                            RequestType.YES_NO,'慧识：增加一点体力上限并继续判定？',action.action_id,frame.frame_id))
                frame.step_index = 4
            if frame.step_index == 2:
                wanted = frame.decision is True; frame.decision = None
                if wanted:
                    frame.step_index = 3
                    return StepResult.push(GainMaxHpAction(action.action_id + ':max:' + str(len(frame.local['cards'])),pid,1))
                frame.step_index = 4
            if frame.step_index == 3:
                frame.step_index = 1
                return StepResult.push(JudgmentAction(action.action_id + ':judge:' + str(len(frame.local['cards'])),pid,JudgmentPattern(),return_card_id=True,retain_result=True))
            if frame.step_index == 4:
                frame.step_index = 5
                return StepResult.ask(PendingRequest(action.action_id + ':give-offer',pid,RequestType.YES_NO,
                    '慧识：将仍在处理区的判定牌交给一名角色？',action.action_id,frame.frame_id))
            if frame.step_index == 5:
                wanted = frame.decision is True; frame.decision = None
                if wanted:
                    frame.step_index = 6
                    return StepResult.ask(PendingRequest(action.action_id + ':recipient',pid,RequestType.CHOOSE_PLAYER,
                        '慧识：选择收牌角色',action.action_id,frame.frame_id,allowed_player_ids=living))
                cards = tuple(c for c in frame.local['cards'] if c in state.cards_in(ZoneRef(ZoneType.PROCESSING)))
                if cards: self.moves.move(state,CardMove(action.action_id + ':discard',cards,ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM,pid))
                return StepResult.complete()
            if frame.step_index == 6:
                target = frame.decision; frame.decision = None
                cards = tuple(c for c in frame.local['cards'] if c in state.cards_in(ZoneRef(ZoneType.PROCESSING)))
                if cards: self.moves.move(state,CardMove(action.action_id + ':give',cards,ZoneRef(ZoneType.PROCESSING),ZoneRef(ZoneType.HAND,target),CardMoveReason.SYSTEM,pid))
                frame.step_index = 7
                if all(len(state.cards_in(ZoneRef(ZoneType.HAND,target))) >= len(state.cards_in(ZoneRef(ZoneType.HAND,q))) for q in living):
                    return StepResult.push(LoseMaxHpAction(action.action_id + ':penalty',pid,1))
            return StepResult.complete()
        if mode == 'tianyi_guojia':
            if frame.step_index == 0:
                if player.marks.get('awakened_tianyi_guojia') or not all(state.players[q].marks.get('ever_damaged') for q in living):
                    if not player.marks.get('ignore_awakening:tianyi_guojia') or player.marks.get('awakened_tianyi_guojia'): return StepResult.complete()
                player.marks['awakened_tianyi_guojia'] = 1; frame.step_index = 1
                return StepResult.push(GainMaxHpAction(action.action_id + ':max',pid,2))
            if frame.step_index == 1:
                frame.step_index = 2
                return StepResult.push(RecoverAction(action.action_id + ':recover',pid,pid,1))
            if frame.step_index == 2:
                frame.step_index = 3
                return StepResult.ask(PendingRequest(action.action_id + ':grant',pid,RequestType.CHOOSE_PLAYER,
                    '天翊：选择永久获得佐幸的角色',action.action_id,frame.frame_id,allowed_player_ids=living))
            target = frame.decision; frame.decision = None
            add_grant(state,target,'zuoxing','tianyi:' + pid)
            state.metadata.setdefault('zuoxing_grantors',{}).setdefault(target,[]).append(pid)
            return StepResult.complete()
        if mode == 'huishi_guojia':
            if frame.step_index == 0:
                if player.marks.get('huishi_guojia_used'): return StepResult.complete()
                frame.step_index = 1
                return StepResult.ask(PendingRequest(action.action_id + ':target',pid,RequestType.CHOOSE_PLAYER,
                    '辉逝：选择角色',action.action_id,frame.frame_id,allowed_player_ids=living))
            if frame.step_index == 1:
                target = frame.decision; frame.decision = None; frame.local['target'] = target
                player.marks['huishi_guojia_used'] = 1
                choices = tuple(skill for skill in self.skills.skills if self.skills.has(state,target,skill)
                    and self.skills.skills[skill].metadata.get('awakening') and not awakening_done(state,target,skill))
                if player.max_hp >= len(living) and choices:
                    frame.step_index = 2
                    return StepResult.ask(PendingRequest(action.action_id + ':awakening',pid,RequestType.CHOOSE_OPTION,
                        '辉逝：选择无视条件的觉醒技',action.action_id,frame.frame_id,choices=choices))
                frame.step_index = 3
                return StepResult.push(DrawCardsAction(action.action_id + ':draw',target,4))
            if frame.step_index == 2:
                skill = frame.decision; frame.decision = None
                state.players[frame.local['target']].marks['ignore_awakening:' + skill] = 1
                frame.step_index = 3
            if frame.step_index == 3:
                frame.step_index = 4
                return StepResult.push(LoseMaxHpAction(action.action_id + ':cost',pid,2))
            return StepResult.complete()
        return self.zuoxing(state, frame)

    def zuoxing(self, state, frame):
        from .hp import LoseMaxHpAction
        from .military_tricks import MilitaryTrickRule, TrickAction
        from .distance import DistanceSystem
        from .events import CardUsedEvent
        from sanguosha.model.virtual_card import VirtualCard
        action = frame.action; pid = action.player_id
        definitions = self.moves.definitions; distance = DistanceSystem(definitions)
        def legal():
            return tuple(d for d in definitions._definitions if d.startswith('trick.')
                and MilitaryTrickRule(d,distance,self.skills).can_use(state,pid)
                and (not MilitaryTrickRule(d,distance,self.skills).requires_target_selection
                     or MilitaryTrickRule(d,distance,self.skills).target_candidates(state,pid)))
        if frame.step_index == 0:
            grantors = tuple(q for q in state.metadata.get('zuoxing_grantors',{}).get(pid,())
                if state.players[q].is_alive and state.players[q].max_hp > 1)
            if not grantors or state.play_usage.count('skill.zuoxing') or not legal(): return StepResult.complete()
            frame.local['grantor'] = grantors[0]; frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':trick',pid,RequestType.CHOOSE_OPTION,
                '佐幸：选择视为使用的普通锦囊',action.action_id,frame.frame_id,choices=('cancel',*legal())))
        if frame.step_index == 1:
            definition = frame.decision; frame.decision = None
            if definition == 'cancel': return StepResult.complete()
            frame.local['definition'] = definition; frame.step_index = 2
            rule = MilitaryTrickRule(definition,distance,self.skills)
            if rule.requires_target_selection:
                low, high = rule.target_bounds(state,pid,None)
                return StepResult.ask(PendingRequest(action.action_id + ':targets',pid,RequestType.CHOOSE_PLAYERS,
                    '佐幸：选择锦囊目标',action.action_id,frame.frame_id,allowed_player_ids=rule.target_candidates(state,pid),min_count=max(1,low),max_count=high))
            frame.decision = ()
        if frame.step_index == 2:
            frame.local['targets'] = tuple(frame.decision); frame.decision = None
            state.play_usage.record('skill.zuoxing'); frame.step_index = 3
            return StepResult.push(LoseMaxHpAction(action.action_id + ':cost',frame.local['grantor'],1))
        if frame.step_index == 3:
            definition = frame.local['definition']; targets = frame.local['targets']
            virtual = VirtualCard(definition,(),None,None,'zuoxing')
            self.moves.recorder.record(CardUsedEvent(action.action_id + ':used',pid,'virtual:zuoxing',targets,definition,virtual_card=virtual))
            frame.step_index = 4
            return StepResult.push(TrickAction(action.action_id + ':trick',pid,'virtual:zuoxing',definition,targets,virtual))
        return StepResult.complete()

    def xunyu(self, state, frame):
        from .response import RespondWithCardAction
        from .military_basics import MilitaryDamageAction
        from .military_tricks import personal_cards, locate
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMove, CardMoveReason
        action = frame.action; pid = action.player_id; target = action.target_id
        if action.mode == 'dinghan':
            if frame.step_index == 0:
                choices = ['cancel'] + [('remove:' if state.players[pid].marks.get('dinghan:' + d) else 'add:') + d
                    for d in self.moves.definitions._definitions if d.startswith(('trick.', 'delayed.'))]
                frame.step_index = 1
                return StepResult.ask(PendingRequest(action.action_id + ':choice', pid, RequestType.CHOOSE_OPTION,
                    '定汉：增加或移出一种锦囊牌名', action.action_id, frame.frame_id, choices=tuple(choices)))
            choice = frame.decision; frame.decision = None
            if choice != 'cancel':
                mode, definition = choice.split(':', 1)
                if mode == 'add': state.players[pid].marks['dinghan:' + definition] = 1
                else: state.players[pid].marks.pop('dinghan:' + definition, None)
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':secret', pid, RequestType.CHOOSE_OPTION,
                '奇正相生：秘密选择奇兵或正兵', action.action_id, frame.frame_id, choices=('qi', 'zheng')))
        if frame.step_index == 1:
            frame.local['secret'] = frame.decision; frame.decision = None; frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':response-type', target, RequestType.CHOOSE_OPTION,
                '奇正相生：可打出杀或闪（对方选择暂不公开）', action.action_id, frame.frame_id,
                choices=('slash', 'dodge', 'pass')))
        if frame.step_index == 2:
            choice = frame.decision; frame.decision = None; frame.local['response_type'] = choice; frame.step_index = 3
            if choice != 'pass':
                return StepResult.push(RespondWithCardAction(action.action_id + ':respond', target,
                    'basic.' + choice, action.action_id, '奇正相生：打出选择的牌或放弃', target,
                    allow_armor=False, card_source_id=pid))
            frame.child_result = None
        if frame.step_index == 3:
            answered = frame.child_result is not None
            required = 'slash' if frame.local['secret'] == 'qi' else 'dodge'
            if answered and frame.local['response_type'] == required:
                return StepResult.complete()
            frame.step_index = 4
            if required == 'slash':
                return StepResult.push(MilitaryDamageAction(action.action_id + ':damage', pid, target, 1))
            cards = personal_cards(state, target)
            if not cards: return StepResult.complete()
            return StepResult.ask(PendingRequest(action.action_id + ':take', pid, RequestType.CHOOSE_CARD,
                '奇正相生：获得目标一张牌', action.action_id, frame.frame_id,
                eligible_card_ids=cards, subject_player_id=target))
        if frame.decision is not None:
            card = frame.decision; frame.decision = None
            self.moves.move(state, CardMove(action.action_id + ':take-card', (card,), locate(state, card),
                ZoneRef(ZoneType.HAND, pid), CardMoveReason.SYSTEM, pid, action.action_id))
        return StepResult.complete()

    def taishici(self, state, frame):
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMove, CardMoveReason
        from .military_basics import MilitaryDamageAction
        from .recovery import RecoverAction
        action = frame.action; pid = action.player_id; player = state.players[pid]
        key = 'wei:' + pid
        if action.mode == 'shenzhu':
            if frame.step_index == 0:
                frame.step_index = 1
                return StepResult.ask(PendingRequest(action.action_id + ':choice', pid, RequestType.CHOOSE_OPTION,
                    '神著：摸一张增加杀上限，或摸三张本回合禁杀', action.action_id, frame.frame_id,
                    choices=('draw1_quota', 'draw3_stop')))
            if frame.step_index == 1:
                choice = frame.decision; frame.decision = None
                if state.current_player_id == pid:
                    if choice == 'draw1_quota':
                        player.marks['slash_quota_bonus'] = player.marks.get('slash_quota_bonus', 0) + 1
                    else:
                        player.marks['slash_prohibited'] = 1
                frame.step_index = 2
                return StepResult.push(DrawCardsAction(action.action_id + ':draw', pid, 1 if choice == 'draw1_quota' else 3))
            return StepResult.complete()
        if action.mode == 'powei_fail':
            if frame.step_index == 0:
                if player.marks.get('powei_success') or player.marks.get('powei_failed'):
                    return StepResult.complete()
                player.marks['powei_failed'] = 1
                for other in state.players.values():
                    other.marks.pop(key, None)
                frame.step_index = 1
                return StepResult.push(RecoverAction(action.action_id + ':recover', pid, pid, 1 - player.hp))
            for index, (ref, zone) in enumerate(tuple(state.zones.items())):
                if ref.player_id == pid and ref.zone_type is ZoneType.EQUIPMENT and zone.card_ids:
                    self.moves.move(state, CardMove(action.action_id + ':discard:' + str(index), tuple(zone.card_ids),
                        ref, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, pid, action.action_id))
            return StepResult.complete()
        target = action.target_id
        if frame.step_index == 0:
            if not self.skills.has(state, pid, 'powei') or player.marks.get('powei_failed') or player.marks.get('powei_success'):
                return StepResult.complete()
            if target == pid:
                counts = {q: state.players[q].marks.pop(key, 0) for q in state.seat_order}
                living = tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive)
                for q, count in counts.items():
                    if count and living:
                        index = state.seat_order.index(q)
                        dest = next(state.seat_order[(index + n) % len(state.seat_order)]
                                    for n in range(1, len(state.seat_order) + 1)
                                    if state.seat_order[(index + n) % len(state.seat_order)] in living)
                        state.players[dest].marks[key] = state.players[dest].marks.get(key, 0) + count
                if not any(p.marks.get(key) for p in state.players.values() if p.is_alive):
                    player.marks['powei_success'] = 1
                    add_grant(state, pid, 'shenzhu', 'powei.success')
                return StepResult.complete()
            if not state.players[target].marks.get(key, 0):
                return StepResult.complete()
            choices = ['cancel']
            hand = state.cards_in(ZoneRef(ZoneType.HAND, pid))
            if hand:
                choices.append('discard_damage')
            if state.players[target].hp <= player.hp and state.cards_in(ZoneRef(ZoneType.HAND, target)):
                choices.append('take_hand')
            if len(choices) == 1:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':choice', pid, RequestType.CHOOSE_OPTION,
                '破围：弃手牌伤害或获得围角色手牌', action.action_id, frame.frame_id,
                choices=tuple(choices), subject_player_id=target))
        if frame.step_index == 1:
            choice = frame.decision; frame.decision = None
            if choice == 'cancel':
                return StepResult.complete()
            state.metadata.setdefault('powei_range', {})[pid] = {'target': target, 'turn': state.turn_number}
            if choice == 'take_hand':
                card = self.rng.choice(state.cards_in(ZoneRef(ZoneType.HAND, target)))
                self.moves.move(state, CardMove(action.action_id + ':take', (card,), ZoneRef(ZoneType.HAND, target),
                    ZoneRef(ZoneType.HAND, pid), CardMoveReason.SYSTEM, pid, action.action_id))
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':discard', pid, RequestType.CHOOSE_CARD,
                '破围：选择弃置的手牌', action.action_id, frame.frame_id,
                eligible_card_ids=state.cards_in(ZoneRef(ZoneType.HAND, pid))))
        if frame.step_index == 2:
            card = frame.decision; frame.decision = None; frame.step_index = 3
            self.moves.move(state, CardMove(action.action_id + ':pay', (card,), ZoneRef(ZoneType.HAND, pid),
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, pid, action.action_id))
            return StepResult.push(MilitaryDamageAction(action.action_id + ':damage', pid, target, 1))
        return StepResult.complete()

    def sunce(self, state, frame):
        from .hp import LoseMaxHpAction, GainMaxHpAction
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMove, CardMoveReason
        action = frame.action; pid = action.player_id; mode = action.mode
        player = state.players[pid]
        if mode == 'fuhai_draw':
            if frame.step_index == 0:
                frame.step_index = 1
                return StepResult.push(DrawCardsAction(action.action_id + ':draw', pid, 1))
            return StepResult.complete()
        if mode == 'fuhai_death':
            if frame.step_index == 0:
                count = state.players[action.target_id].marks.get('pingding', 0)
                if not count:
                    return StepResult.complete()
                frame.local['count'] = count; frame.step_index = 1
                return StepResult.push(GainMaxHpAction(action.action_id + ':max', pid, count))
            if frame.step_index == 1:
                frame.step_index = 2
                return StepResult.push(DrawCardsAction(action.action_id + ':draw', pid, frame.local['count']))
            return StepResult.complete()
        if frame.step_index == 0:
            if mode == 'yingba':
                targets = tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive and state.players[q].max_hp > 1)
                if not targets or state.play_usage.count('skill.yingba'):
                    return StepResult.complete()
                frame.step_index = 1
                return StepResult.ask(PendingRequest(action.action_id + ':target', pid, RequestType.CHOOSE_PLAYER,
                    '英霸：选择另一角色', action.action_id, frame.frame_id, allowed_player_ids=targets))
            frame.step_index = 3
            return StepResult.push(LoseMaxHpAction(action.action_id + ':max', pid, 1))
        if frame.step_index == 1:
            target = frame.decision; frame.decision = None; frame.local['target'] = target
            state.play_usage.record('skill.yingba')
            state.players[target].marks['pingding'] = state.players[target].marks.get('pingding', 0) + 1
            frame.step_index = 2
            return StepResult.push(LoseMaxHpAction(action.action_id + ':target-max', target, 1))
        if frame.step_index == 2:
            frame.step_index = 5
            return StepResult.push(LoseMaxHpAction(action.action_id + ':own-max', pid, 1))
        if frame.step_index == 3:
            if self.skills.has(state, pid, 'yingba') and action.target_id in state.players:
                source = state.players[action.target_id]
                source.marks['pingding'] = source.marks.get('pingding', 0) + 1
            hand = state.cards_in(ZoneRef(ZoneType.HAND, pid))
            targets = tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive)
            if not hand or not targets:
                return StepResult.complete()
            frame.step_index = 4
            return StepResult.ask(PendingRequest(action.action_id + ':recipient', pid, RequestType.CHOOSE_PLAYER,
                '冯河：选择交牌对象', action.action_id, frame.frame_id, allowed_player_ids=targets))
        if frame.step_index == 4:
            frame.local['target'] = frame.decision; frame.decision = None; frame.step_index = 6
            return StepResult.ask(PendingRequest(action.action_id + ':card', pid, RequestType.CHOOSE_CARD,
                '冯河：选择交出的手牌', action.action_id, frame.frame_id,
                eligible_card_ids=state.cards_in(ZoneRef(ZoneType.HAND, pid))))
        if frame.step_index == 6:
            card = frame.decision; frame.decision = None
            self.moves.move(state, CardMove(action.action_id + ':give', (card,), ZoneRef(ZoneType.HAND, pid),
                ZoneRef(ZoneType.HAND, frame.local['target']), CardMoveReason.SYSTEM, pid, action.action_id))
        return StepResult.complete()

    def lusu(self, state, frame):
        from sanguosha.model.enums import Identity, Phase
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMove, CardMoveReason
        action = frame.action
        pid = action.player_id
        mode = action.mode
        if not self.skills.has(state, pid, mode):
            return StepResult.complete()
        def owned(owner):
            return tuple(c for ref, zone in state.zones.items()
                         if ref.player_id == owner and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                         for c in zone.card_ids)
        def field(owner):
            return tuple(c for ref, zone in state.zones.items()
                         if ref.player_id == owner and ref.zone_type in (ZoneType.EQUIPMENT, ZoneType.JUDGMENT)
                         for c in zone.card_ids)
        def move(cards, destination, suffix):
            groups = {}
            for card in cards:
                source = next(ref for ref, zone in state.zones.items() if card in zone.card_ids)
                groups.setdefault(source, []).append(card)
            for index, (source, group) in enumerate(groups.items()):
                self.moves.move(state, CardMove(action.action_id + ':' + suffix + ':' + str(index),
                    tuple(group), source, destination, CardMoveReason.SYSTEM, pid, action.action_id))
        if mode == 'tamo':
            nonlords = tuple(q for q in state.seat_order if state.players[q].is_alive and state.players[q].identity is not Identity.LORD)
            if frame.step_index == 0:
                frame.step_index = 1
                return StepResult.ask(PendingRequest(action.action_id + ':offer', pid, RequestType.YES_NO,
                    '榻谟：调整非主公角色座次？', action.action_id, frame.frame_id))
            if frame.step_index == 1:
                wanted = frame.decision is True; frame.decision = None
                if not wanted:
                    return StepResult.complete()
                frame.step_index = 2
                return StepResult.ask(PendingRequest(action.action_id + ':order', pid, RequestType.CHOOSE_PLAYERS,
                    '榻谟：按新座次顺序选择全部非主公角色', action.action_id, frame.frame_id,
                    allowed_player_ids=nonlords, min_count=len(nonlords), max_count=len(nonlords)))
            order = iter(frame.decision); frame.decision = None
            state.seat_order = tuple(q if state.players[q].identity is Identity.LORD else next(order)
                                     for q in state.seat_order)
            for index, q in enumerate(state.seat_order):
                state.players[q].seat = index
            return StepResult.complete()
        if frame.step_index == 0:
            if mode == 'dingzhou':
                if state.current_phase is not Phase.PLAY or state.current_player_id != pid or state.play_usage.count('skill.dingzhou'):
                    return StepResult.complete()
                targets = tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive
                                and 0 < len(field(q)) <= len(owned(pid)))
                frame.step_index = 2
            else:
                targets = tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive)
                frame.local['targets'] = targets
                frame.step_index = 1
                if not targets:
                    return StepResult.complete()
                return StepResult.ask(PendingRequest(action.action_id + ':offer', pid, RequestType.YES_NO,
                    '智盟：与另一角色随机均分手牌？', action.action_id, frame.frame_id))
            if not targets:
                return StepResult.complete()
            return StepResult.ask(PendingRequest(action.action_id + ':target', pid, RequestType.CHOOSE_PLAYER,
                '定州：选择有场上牌的另一角色', action.action_id, frame.frame_id, allowed_player_ids=targets))
        if frame.step_index == 1:
            wanted = frame.decision is True; frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':target', pid, RequestType.CHOOSE_PLAYER,
                '智盟：选择另一角色', action.action_id, frame.frame_id, allowed_player_ids=frame.local['targets']))
        if frame.step_index == 2:
            target = frame.decision; frame.decision = None
            frame.local['target'] = target
            if not state.players[target].is_alive:
                return StepResult.complete()
            if mode == 'dingzhou':
                count = len(field(target))
                frame.local['field'] = field(target)
                frame.step_index = 3
                return StepResult.ask(PendingRequest(action.action_id + ':cards', pid, RequestType.CHOOSE_CARDS,
                    '定州：选择交出的牌', action.action_id, frame.frame_id,
                    eligible_card_ids=owned(pid), min_count=count, max_count=count))
            first = state.cards_in(ZoneRef(ZoneType.HAND, pid))
            second = state.cards_in(ZoneRef(ZoneType.HAND, target))
            # This staging zone belongs to the owner; projection never exposes its contents to others.
            staging = ZoneRef(ZoneType.SPECIAL, pid, special_key='zhimeng')
            move(first + second, staging, 'pool')
            pooled = list(first + second); self.rng.shuffle(pooled)
            midpoint = (len(pooled) + 1) // 2
            move(tuple(pooled[:midpoint]), ZoneRef(ZoneType.HAND, pid), 'owner')
            move(tuple(pooled[midpoint:]), ZoneRef(ZoneType.HAND, target), 'target')
            return StepResult.complete()
        cards = tuple(frame.decision); frame.decision = None
        target = frame.local['target']
        state.play_usage.record('skill.dingzhou')
        move(cards, ZoneRef(ZoneType.HAND, target), 'give')
        move(frame.local['field'], ZoneRef(ZoneType.HAND, pid), 'take')
        return StepResult.complete()

    def lianpo(self, state, frame):
        action = frame.action
        pid = action.player_id
        player = state.players[pid]
        if not self.skills.has(state, pid, 'lianpo'):
            return StepResult.complete()
        if frame.step_index == 0:
            choices = ['cancel']
            if player.marks.get('lianpo_selected_turn', -1) != state.turn_number:
                choices.append('extra_turn')
            if self.skills.has(state, pid, 'jilue'):
                initialize_jilue(state, pid, self.skills)
                choices.extend('learn:' + skill for skill in JILUE_SKILLS
                               if not self.skills.has(state, pid, skill))
            if len(choices) == 1:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':choice', pid, RequestType.CHOOSE_OPTION,
                '连破：本回合结束后额外回合或永久学习极略技能',
                action.action_id, frame.frame_id, choices=tuple(choices)))
        choice = frame.decision
        frame.decision = None
        if choice == 'extra_turn':
            player.marks['lianpo_selected_turn'] = state.turn_number
            player.marks['lianpo_pending'] = 1
        elif choice.startswith('learn:'):
            add_grant(state, pid, choice.split(':', 1)[1], 'jilue.permanent')
        return StepResult.complete()


def register(registry, skills, moves, rng):
    registry.register(MobileGodAction, MobileGodHandler(skills, moves, rng))


def gain_ren_for_nonresponse(state, frame, skills, recorder):
    action = frame.action
    pid = action.player_id
    if (frame.local.get('mobile_ren_checked') or skills is None
            or not state.players[pid].is_alive or not skills.has(state, pid, 'renjie')
            or action.required_definition_id not in ('basic.slash', 'basic.dodge', 'trick.nullification')):
        return
    frame.local['mobile_ren_checked'] = True
    source = action.card_source_id
    delayed = action.delayed_card
    if source is None and not delayed:
        from .events import CardUsedEvent
        candidates = [e for e in recorder.events if isinstance(e, CardUsedEvent)
                      and e.event_id.endswith(':used')
                      and (action.source_action_id == e.event_id[:-5]
                           or action.source_action_id.startswith(e.event_id[:-5] + ':'))]
        if candidates:
            event = max(candidates, key=lambda e: len(e.event_id))
            source = event.player_id
            definition = event.virtual_definition_id or state.cards[event.card_id].definition_id
            delayed = definition.startswith('delayed.')
    if not delayed and (source is None or source == pid):
        return
    player = state.players[pid]
    if player.marks.get('renjie_round_count', 0) < 4:
        player.marks['renjie_round_count'] = player.marks.get('renjie_round_count', 0) + 1
        player.marks['ren'] = player.marks.get('ren', 0) + 1


def start_normal_round(state, pid):
    if state.extra_turn_anchor is not None:
        return
    visited = state.metadata.setdefault('mobile_round_visited', [])
    living = {q for q in state.seat_order if state.players[q].is_alive}
    if pid in visited or living.issubset(set(visited)):
        visited.clear()
        state.metadata['mobile_round_number'] = state.metadata.get('mobile_round_number', 1) + 1
        for player in state.players.values():
            player.marks.pop('renjie_round_count', None)
    if pid not in visited:
        visited.append(pid)


def event_reactions(state, event, skills, recorder=None):
    from .events import CardUsedEvent, PlayerDiedEvent, AfterDamageEvent, CardResolvedEvent
    result = []
    if isinstance(event, AfterDamageEvent):
        state.players[event.target_id].marks['ever_damaged'] = 1
        for key in tuple(state.players[event.target_id].marks):
            if key.startswith('wei:'):
                state.players[event.target_id].marks.pop(key, None)
    if isinstance(event, CardResolvedEvent) and skills.has(state,event.player_id,'shenzhu'):
        used = next((e for e in reversed(recorder.events) if isinstance(e,CardUsedEvent)
                     and e.event_id == event.event_id.removesuffix(':resolved') + ':used'), None) if recorder else None
        if (used is not None and not used.virtual_definition_id and used.virtual_card is None
                and state.cards[event.card_id].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash')):
            result.append(MobileGodAction(event.event_id + ':shenzhu',event.player_id,'shenzhu'))
    if isinstance(event, CardUsedEvent) and not event.virtual_definition_id and event.virtual_card is None:
        definition = state.cards[event.card_id].definition_id
        if definition.startswith(('trick.', 'delayed.')):
            for owner in state.seat_order:
                if (state.players[owner].is_alive and skills.has(state,owner,'lingce')
                        and (definition in ('trick.ex_nihilo','trick.dismantlement','trick.nullification','trick.qizhengxiangsheng')
                             or state.players[owner].marks.get('dinghan:' + definition))):
                    result.append(MobileGodAction(event.event_id + ':lingce:' + owner,owner,'fuhai_draw'))
    if isinstance(event, CardUsedEvent) and skills.has(state, event.player_id, 'fuhai'):
        pid = event.player_id; player = state.players[pid]
        if any(state.players[q].marks.get('pingding', 0) for q in event.target_ids):
            if player.marks.get('fuhai_draw_turn', -1) != state.turn_number:
                player.marks['fuhai_draw_turn'] = state.turn_number
                player.marks['fuhai_draw_count'] = 0
            if player.marks.get('fuhai_draw_count', 0) < 2:
                player.marks['fuhai_draw_count'] = player.marks.get('fuhai_draw_count', 0) + 1
                result.append(MobileGodAction(event.event_id + ':fuhai', pid, 'fuhai_draw'))
    if isinstance(event, PlayerDiedEvent) and state.players[event.player_id].marks.get('pingding', 0):
        for pid in state.seat_order:
            if state.players[pid].is_alive and skills.has(state, pid, 'fuhai'):
                result.append(MobileGodAction(event.event_id + ':fuhai:' + pid, pid, 'fuhai_death', event.player_id))
    return result


def fuhai_prohibits_response(state, action, skills, recorder):
    if skills is None or not state.players[action.player_id].marks.get('pingding', 0):
        return False
    source = action.card_source_id
    if source is None:
        from .events import CardUsedEvent
        candidates = [e for e in recorder.events if isinstance(e, CardUsedEvent)
            and e.event_id.endswith(':used') and action.source_action_id.startswith(e.event_id[:-5])]
        if candidates:
            source = max(candidates, key=lambda e: len(e.event_id)).player_id
    return source is not None and source != action.player_id and skills.has(state, source, 'fuhai')


def cancel_dinghan_target(state, pid, definition, skills):
    if skills is None: return False
    if definition == 'trick.qizhengxiangsheng' and skills.has(state,pid,'tianzuo'):
        return True
    if skills.has(state,pid,'dinghan') and not state.players[pid].marks.get('dinghan:' + definition):
        state.players[pid].marks['dinghan:' + definition] = 1
        return True
    return False


def inject_qizheng(state, pid, rng):
    from sanguosha.model.card import CardInstance
    from sanguosha.model.enums import Suit
    from sanguosha.model.zones import ZoneRef, ZoneType
    draw = state.zones[ZoneRef(ZoneType.DRAW_PILE)].card_ids
    for index, (suit, rank) in enumerate([(Suit.SPADE,n) for n in (2,4,6,8)] + [(Suit.CLUB,n) for n in (3,5,7,9)]):
        cid = 'tianzuo-' + pid + '-' + str(index)
        state.cards[cid] = CardInstance(cid,'trick.qizhengxiangsheng',suit,rank)
        draw.append(cid)
    rng.shuffle(draw)


def awakening_done(state,pid,skill):
    player = state.players[pid]
    marker = 'zili_awakened' if skill == 'zili' else 'awakened_baiyin' if skill == 'baoyin' else 'awakened_' + skill
    return bool(player.marks.get(marker))
