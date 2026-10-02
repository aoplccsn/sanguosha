"""Authoritative hidden-card declaration and ordered challenge resolution."""

from dataclasses import dataclass

from sanguosha.model.enums import CardCategory, Phase, Suit
from sanguosha.model.state import GameStatus
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .deck import DrawCardsAction
from .events import CardRespondedEvent, CardUsedEvent, Event
from .hp import LoseHpAction
from .military_basics import SlashSequence
from .requests import PendingRequest, RequestType
from .suits import effective_color, effective_suit


def committed_zone(action):
    return ZoneRef(ZoneType.SPECIAL, action.player_id,
                   special_key=f'committed:{action.action_id}')


@dataclass(frozen=True, slots=True)
class GuhuoAction(Action):
    player_id: str
    required_definition_id: str = ''
    source_action_id: str = ''
    subject_player_id: str | None = None
    response_number: int = 1
    response_total: int = 1


class GuhuoHandler:
    def __init__(self, skills, definitions, rules, moves, events):
        self.skills = skills
        self.definitions = definitions
        self.rules = rules
        self.moves = moves
        self.events = events

    def _active_definitions(self, state, player_id):
        usage = state.play_usage
        if (state.current_player_id != player_id or state.current_phase is not Phase.PLAY
                or usage is None or usage.player_id != player_id):
            return ()
        result = []
        for definition_id, rule in self.rules._rules.items():
            category = self.definitions.get(definition_id).category
            if category not in (CardCategory.BASIC, CardCategory.TRICK):
                continue
            limit = rule.usage_limit(state, player_id)
            if limit is not None and usage.count(getattr(rule, 'usage_key', definition_id)) >= limit:
                continue
            if not rule.can_use(state, player_id):
                continue
            if rule.requires_target_selection:
                low, _ = (rule.target_bounds(state, player_id, None)
                          if hasattr(rule, 'target_bounds') else (1, 1))
                if low and not rule.target_candidates(state, player_id):
                    continue
            result.append(str(definition_id))
        return tuple(result)

    def available(self, state, player_id):
        return (self.skills.has(state, player_id, 'guhuo')
                and state.players[player_id].is_alive
                and bool(state.cards_in(ZoneRef(ZoneType.HAND, player_id)))
                and bool(self._active_definitions(state, player_id)))

    @staticmethod
    def response_definitions_for(state, required, player_id, subject_player_id):
        choices = [required]
        if required == 'basic.slash':
            choices.extend(('basic.fire_slash', 'basic.thunder_slash'))
        if (required == 'basic.peach' and subject_player_id == player_id
                and state.players[player_id].hp <= 0):
            choices.append('basic.wine')
        return tuple(choices)

    def response_definitions(self, state, action):
        choices = self.response_definitions_for(
            state, action.required_definition_id, action.player_id, action.subject_player_id)
        return tuple(d for d in choices if d in self.definitions._definitions
                     and self.definitions.get(d).category in (CardCategory.BASIC, CardCategory.TRICK))

    def validate_start(self, state, action):
        if (not self.skills.has(state, action.player_id, 'guhuo')
                or not state.players[action.player_id].is_alive
                or not state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))):
            raise InvalidCardUse('蛊惑不可用')
        if not action.required_definition_id and not self._active_definitions(state, action.player_id):
            raise InvalidCardUse('蛊惑没有合法声明')
        if action.required_definition_id and not self.response_definitions(state, action):
            raise InvalidCardUse('蛊惑不能响应此牌')

    def _declare_choices(self, state, action):
        return (self.response_definitions(state, action) if action.required_definition_id
                else self._active_definitions(state, action.player_id))

    def _commit(self, state, frame):
        action = frame.action
        card_id = frame.local['card_id']
        declared = frame.local['declared']
        if card_id not in state.cards_in(ZoneRef(ZoneType.HAND, action.player_id)):
            raise InvalidCardUse('蛊惑实体牌已不可用')
        if declared not in self._declare_choices(state, action):
            raise InvalidCardUse('蛊惑声明已不可用')
        if not action.required_definition_id:
            self.rules.get(declared).validate_targets(
                state, action.player_id, tuple(filter(None, frame.local.get('targets', '').split('|'))))
        self.moves.move(state, CardMove(action.action_id + ':commit', (card_id,),
            ZoneRef(ZoneType.HAND, action.player_id), committed_zone(action),
            CardMoveReason.USE if not action.required_definition_id else CardMoveReason.RESPONSE,
            action.player_id, action.action_id))
        self.events.record(Event(action.action_id + ':declare', 'guhuo_declare',
            action.player_id, metadata={'declared': declared}))
        frame.step_index = 4
        return StepResult.continue_()

    def _finish(self, state, frame):
        action = frame.action
        card_id = frame.local['card_id']
        declared = frame.local['declared']
        challenged = bool(frame.local.get('challengers'))
        card = state.cards[card_id]
        succeeds = not challenged or (card.definition_id == declared and card.suit is Suit.HEART)
        zone = committed_zone(action)
        state.metadata.get('revealed_committed', {}).pop(card_id, None)
        if not succeeds or not state.players[action.player_id].is_alive or state.status is GameStatus.FINISHED:
            if card_id in state.cards_in(zone):
                self.moves.move(state, CardMove(action.action_id + ':void', (card_id,), zone,
                    ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM, action.player_id))
            return StepResult.complete()
        processing = ZoneRef(ZoneType.PROCESSING)
        self.moves.move(state, CardMove(action.action_id + ':effective', (card_id,), zone,
            processing, CardMoveReason.USE if not action.required_definition_id
            else CardMoveReason.RESPONSE, action.player_id))
        if not challenged:
            state.metadata.setdefault('concealed_discard_cards', {})[card_id] = declared
        if action.required_definition_id:
            self.events.record(CardRespondedEvent(action.action_id + ':responded',
                action.player_id, card_id, action.source_action_id, declared,
                action.response_number, action.response_total))
            virtual = VirtualCard(declared, (card_id,),
                                  effective_suit(state, card_id, action.player_id),
                                  effective_color(state, card_id, action.player_id))
            self.moves.move(state, CardMove(action.action_id + ':discard', (card_id,),
                processing, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.RESPONSE,
                action.player_id))
            return StepResult.complete(virtual)
        rule = self.rules.get(declared)
        targets = tuple(filter(None, frame.local.get('targets', '').split('|')))
        state.play_usage.record(getattr(rule, 'usage_key', declared))
        self.events.record(CardUsedEvent(action.action_id + ':used', action.player_id,
                                         card_id, targets, declared))
        if declared in ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash'):
            effect = SlashSequence(action.action_id + ':effect', action.player_id, card_id,
                targets, VirtualCard(declared, (card_id,),
                    effective_suit(state, card_id, action.player_id),
                    effective_color(state, card_id, action.player_id)))
        else:
            effect = rule.effect_action(action.action_id + ':effect', action.player_id,
                                        card_id, targets)
        frame.step_index = 10
        return StepResult.push(effect)

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':declare',
                action.player_id, RequestType.CHOOSE_OPTION, '蛊惑：声明基本牌或普通锦囊',
                action.action_id, frame.frame_id,
                choices=self._declare_choices(state, action)))
        if frame.step_index == 1:
            declared = frame.decision
            frame.decision = None
            if declared not in self._declare_choices(state, action):
                raise InvalidCardUse('蛊惑声明不合法')
            frame.local['declared'] = declared
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':card',
                action.player_id, RequestType.CHOOSE_CARD, '蛊惑：扣置一张手牌',
                action.action_id, frame.frame_id,
                choices=('declared:' + declared,),
                eligible_card_ids=state.cards_in(ZoneRef(ZoneType.HAND, action.player_id))))
        if frame.step_index == 2:
            card_id = frame.decision
            frame.decision = None
            if card_id not in state.cards_in(ZoneRef(ZoneType.HAND, action.player_id)):
                raise InvalidCardUse('蛊惑只能扣置手牌')
            frame.local['card_id'] = card_id
            if not action.required_definition_id:
                rule = self.rules.get(frame.local['declared'])
                if rule.requires_target_selection:
                    low, high = (rule.target_bounds(state, action.player_id, card_id)
                                 if hasattr(rule, 'target_bounds') else (1, 1))
                    frame.step_index = 3
                    return StepResult.ask(PendingRequest(action.action_id + ':targets',
                        action.player_id, RequestType.CHOOSE_PLAYERS if high > 1 else RequestType.CHOOSE_PLAYER,
                        '蛊惑：选择声明牌的目标', action.action_id, frame.frame_id,
                        allowed_player_ids=rule.target_candidates(state, action.player_id),
                        min_count=low, max_count=high))
            return self._commit(state, frame)
        if frame.step_index == 3:
            target = frame.decision
            frame.decision = None
            targets = target if isinstance(target, tuple) else (target,)
            frame.local['targets'] = '|'.join(targets)
            return self._commit(state, frame)
        if frame.step_index == 4:
            seats = state.seat_order
            start = seats.index(action.player_id)
            while frame.cursor < len(seats) - 1:
                frame.cursor += 1
                pid = seats[(start + frame.cursor) % len(seats)]
                if not state.players[pid].is_alive:
                    continue
                frame.local['challenger'] = pid
                frame.step_index = 5
                name = self.definitions.get(frame.local['declared']).name
                return StepResult.ask(PendingRequest(
                    f'{action.action_id}:challenge:{frame.cursor}', pid, RequestType.YES_NO,
                    f'蛊惑声明【{name}】：是否质疑？', action.action_id, frame.frame_id,
                    choices=('declared:' + frame.local['declared'],),
                    subject_player_id=action.player_id))
            frame.cursor = 0
            frame.step_index = 6
            return StepResult.continue_()
        if frame.step_index == 5:
            if frame.decision is True:
                challengers = frame.local.get('challengers', '')
                frame.local['challengers'] = challengers + ('|' if challengers else '') + frame.local['challenger']
            frame.decision = None
            frame.step_index = 4
            return StepResult.continue_()
        if frame.step_index == 6:
            challengers = frame.local.get('challengers', '')
            if challengers:
                card_id = frame.local['card_id']
                card = state.cards[card_id]
                state.metadata.setdefault('revealed_committed', {})[card_id] = True
                frame.local['truth'] = card.definition_id == frame.local['declared']
                self.events.record(Event(action.action_id + ':reveal', 'guhuo_reveal',
                    action.player_id, metadata={'declared': frame.local['declared'],
                        'actual': str(card.definition_id), 'suit': card.suit.value,
                        'truth': bool(frame.local['truth'])}))
            frame.step_index = 7
            return StepResult.continue_()
        if frame.step_index == 7:
            challengers = tuple(filter(None, frame.local.get('challengers', '').split('|')))
            while frame.cursor < len(challengers):
                pid = challengers[frame.cursor]
                frame.cursor += 1
                if not state.players[pid].is_alive:
                    continue
                frame.step_index = 8
                if frame.local['truth']:
                    return StepResult.push(LoseHpAction(
                        f'{action.action_id}:challenge-loss:{frame.cursor}', pid, 1))
                return StepResult.push(DrawCardsAction(
                    f'{action.action_id}:challenge-draw:{frame.cursor}', pid, 1))
            frame.step_index = 9
            return StepResult.continue_()
        if frame.step_index == 8:
            frame.step_index = 7
            return StepResult.continue_()
        if frame.step_index == 9:
            return self._finish(state, frame)
        if frame.step_index == 10:
            card_id = frame.local['card_id']
            if card_id in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
                self.moves.move(state, CardMove(action.action_id + ':discard', (card_id,),
                    ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                    CardMoveReason.USE, action.player_id))
            return StepResult.complete(frame.child_result)
        raise InvalidCardUse('蛊惑阶段状态无效')
