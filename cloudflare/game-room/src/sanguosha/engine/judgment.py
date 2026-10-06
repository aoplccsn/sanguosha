"""One-card judgment lifecycle, kept on a resolution frame for future replacement."""

from dataclasses import dataclass

from sanguosha.model.enums import Color, Suit, Kingdom
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .card_rules import InvalidCardUse
from .card_limits import card_allowed
from .events import Event, EventRecorder
from .resolution import ResolutionFrame
from .requests import PendingRequest, RequestType
from .suits import effective_color, effective_suit


@dataclass(frozen=True, slots=True)
class JudgmentPattern:
    suit: Suit | None = None
    color: Color | None = None
    ranks: frozenset[int] | None = None
    inverted: bool = False

    def matches(self, state: GameState, card_id: CardInstanceId, owner_id=None) -> bool:
        card = state.cards[card_id]
        matched = ((self.suit is None or effective_suit(state, card_id, owner_id) is self.suit)
                and (self.color is None or effective_color(state, card_id, owner_id) is self.color)
                and (self.ranks is None or card.rank in self.ranks))
        return not matched if self.inverted else matched


@dataclass(frozen=True, slots=True)
class JudgmentAction(Action):
    player_id: PlayerId
    pattern: JudgmentPattern
    gain_on_match: bool = False
    return_card_id: bool = False
    success_destination: ZoneRef | None = None


class JudgmentHandler:
    def __init__(self, moves: CardMoveService, recorder: EventRecorder, deck=None, skills=None) -> None:
        self.moves = moves
        self.recorder = recorder
        self.deck = deck
        self.skills = skills

    @staticmethod
    def retrial_cards(state, actor, black=False):
        zones = (ZoneType.HAND, ZoneType.EQUIPMENT) if black else (ZoneType.HAND,)
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == actor and ref.zone_type in zones
                     for cid in zone.card_ids
                     if (not black or effective_color(state, cid, actor) is Color.BLACK)
                     and card_allowed(state, actor, (cid,)))

    def _finish(self, state, frame, card_id, destination):
        action = frame.action
        if (not frame.local.get('songwei_finished') and self.skills is not None and state.players[action.player_id].is_alive
                and self.skills.faction(state, action.player_id) is Kingdom.WEI
                and effective_color(state, card_id, action.player_id) is Color.BLACK):
            lord = next((pid for pid in state.seat_order if pid != action.player_id
                         and state.players[pid].is_alive
                         and self.skills.has(state, pid, 'songwei')), None)
            if lord is not None:
                from .forest import SongweiAction
                frame.local['finish_destination'] = destination
                frame.step_index = 8
                return StepResult.push(SongweiAction(action.action_id + ':songwei',
                                                     action.player_id, lord))
        self.moves.move(state, CardMove(f"{action.action_id}:after-move", (card_id,),
                                        ZoneRef(ZoneType.PROCESSING), destination,
                                        CardMoveReason.SYSTEM, action.player_id, action.action_id))
        self.recorder.record(Event(f"{action.action_id}:after", "after_judgment", action.player_id,
                                   metadata={"card_id": str(card_id), "matched": bool(frame.local["matched"]),
                                             **frame.local.get("final_face", {})}))
        return StepResult.complete(str(card_id) if action.return_card_id else bool(frame.local["matched"]))

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, JudgmentAction)
        if frame.step_index == 8:
            frame.local['songwei_finished'] = True
            return self._finish(state, frame, CardInstanceId(str(frame.local['card_id'])),
                                frame.local['finish_destination'])
        draw = ZoneRef(ZoneType.DRAW_PILE)
        processing = ZoneRef(ZoneType.PROCESSING)
        if frame.step_index == 0:
            self.recorder.record(Event(f"{action.action_id}:before", "before_judgment", action.player_id))
            if self.deck is not None:
                self.deck.ensure_draw(state, action.action_id)
            available = state.cards_in(draw)
            if not available:
                raise ValueError("judgment draw pile is empty")
            card_id = available[0]
            self.moves.move(state, CardMove(f"{action.action_id}:reveal", (card_id,), draw, processing,
                                            CardMoveReason.SYSTEM, action.player_id, action.action_id))
            frame.local["card_id"] = str(card_id)
            self.recorder.record(Event(f"{action.action_id}:revealed", "judgment_card_revealed",
                                       action.player_id, metadata={"card_id": str(card_id), "judged_player_id": action.player_id,
                                                 "effective_suit": effective_suit(state, card_id, action.player_id).value,
                                                 "effective_color": effective_color(state, card_id, action.player_id).value}))
            frame.step_index = 1
            return StepResult.continue_()
        card_id = CardInstanceId(str(frame.local["card_id"]))
        if frame.step_index == 4:
            replace_card = frame.decision is True
            frame.decision = None
            frame.step_index = 1
            if replace_card:
                actor = PlayerId(str(frame.local['guicai_actor']))
                candidates = self.retrial_cards(state, actor)
                if candidates:
                    frame.step_index = 5
                    preferred = set(str(frame.local.get('guicai_preferred', '')).split('|'))
                    candidates = tuple(sorted(candidates, key=lambda cid: cid not in preferred))
                    return StepResult.ask(PendingRequest(f'{action.action_id}:guicai-card:{actor}', actor,
                        RequestType.CHOOSE_CARD, '【鬼才】选择一张手牌替换判定牌',
                        action.action_id, frame.frame_id, eligible_card_ids=candidates,
                        choices=tuple(f'better:{cid}' for cid in candidates if cid in preferred)))
            return StepResult.continue_()
        if frame.step_index == 9:
            replace_card = frame.decision is True
            frame.decision = None
            frame.step_index = 1
            actor = PlayerId(str(frame.local['guicai_actor']))
            candidates = self.retrial_cards(state, actor)
            if replace_card and candidates and state.players[actor].marks.get('ren', 0) > 0:
                state.players[actor].marks['ren'] -= 1
                frame.step_index = 5
                return StepResult.ask(PendingRequest(
                    f'{action.action_id}:jilue-guicai-card:{actor}', actor,
                    RequestType.CHOOSE_CARD, '极略·鬼才：选择替换判定牌的手牌',
                    action.action_id, frame.frame_id, eligible_card_ids=candidates))
            return StepResult.continue_()
        if frame.step_index == 5:
            actor = PlayerId(str(frame.local['guicai_actor']))
            material = CardInstanceId(str(frame.decision))
            frame.decision = None
            if material not in self.retrial_cards(state, actor):
                raise InvalidCardUse('retrial material is unavailable or prohibited')
            self.moves.move(state, CardMove(f'{action.action_id}:guicai-old:{actor}', (card_id,),
                processing, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM,
                actor, action.action_id))
            self.moves.move(state, CardMove(f'{action.action_id}:guicai-new:{actor}', (material,),
                ZoneRef(ZoneType.HAND, actor), processing, CardMoveReason.RESPONSE,
                actor, action.action_id))
            frame.local['card_id'] = str(material)
            self.recorder.record(Event(f'{action.action_id}:replaced:{actor}', 'judgment_card_replaced', actor,
                metadata={'old_card_id': str(card_id), 'card_id': str(material),
                          'judged_player_id': action.player_id,
                          'effective_suit': effective_suit(state, material, action.player_id).value,
                          'effective_color': effective_color(state, material, action.player_id).value}))
            frame.step_index = 1
            return StepResult.continue_()
        if frame.step_index == 6:
            replace_card = frame.decision is True
            frame.decision = None
            frame.step_index = 1
            if replace_card:
                actor = PlayerId(str(frame.local['guidao_actor']))
                candidates = self.retrial_cards(state, actor, black=True)
                if candidates:
                    preferred = set(str(frame.local.get('guidao_preferred', '')).split('|'))
                    frame.step_index = 7
                    return StepResult.ask(PendingRequest(f'{action.action_id}:guidao-card:{actor}', actor,
                        RequestType.CHOOSE_CARD, '【鬼道】选择一张黑色牌替换判定牌',
                        action.action_id, frame.frame_id, eligible_card_ids=candidates,
                        choices=tuple(f'better:{cid}' for cid in candidates if cid in preferred)))
            return StepResult.continue_()
        if frame.step_index == 7:
            actor = PlayerId(str(frame.local['guidao_actor']))
            material = CardInstanceId(str(frame.decision))
            frame.decision = None
            source = next((ref for ref, zone in state.zones.items()
                           if ref.player_id == actor and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                           and material in zone.card_ids), None)
            if source is None or material not in self.retrial_cards(state, actor, black=True):
                raise InvalidCardUse('鬼道材料已不可用')
            self.moves.move(state, CardMove(f'{action.action_id}:guidao-old:{actor}', (card_id,),
                processing, ZoneRef(ZoneType.HAND, actor), CardMoveReason.SYSTEM,
                actor, action.action_id))
            self.moves.move(state, CardMove(f'{action.action_id}:guidao-new:{actor}', (material,),
                source, processing, CardMoveReason.RESPONSE, actor, action.action_id))
            frame.local['card_id'] = str(material)
            self.recorder.record(Event(f'{action.action_id}:guidao-replaced:{actor}',
                'judgment_card_replaced', actor,
                metadata={'old_card_id': str(card_id), 'card_id': str(material),
                          'judged_player_id': action.player_id,
                          'effective_suit': effective_suit(state, material, action.player_id).value,
                          'effective_color': effective_color(state, material, action.player_id).value}))
            frame.step_index = 1
            return StepResult.continue_()
        if frame.step_index == 1:
            if card_id not in state.cards_in(processing):
                raise ValueError("judgment card left processing before result")
            if self.skills is not None:
                start = state.seat_order.index(state.current_player_id or state.seat_order[0])
                order = state.seat_order[start:] + state.seat_order[:start]
                if state.current_phase is None and state.current_player_id in order:
                    order = tuple(pid for pid in order if pid != state.current_player_id) + (state.current_player_id,)
                for actor in order:
                    if not state.players[actor].is_alive:
                        continue
                    for skill in ('guicai', 'jilue', 'guidao'):
                        key = actor + ':' + skill
                        if key in frame.local.get('retrial_offered', ()):
                            continue
                        frame.local['retrial_offered'] = (*frame.local.get('retrial_offered', ()), key)
                        if not self.skills.has(state, actor, skill):
                            continue
                        hand = self.retrial_cards(state, actor)
                        if skill in ('guicai', 'jilue') and not hand:
                            continue
                        if skill == 'jilue' and state.players[actor].marks.get('ren', 0) <= 0:
                            continue
                        if skill == 'guidao' and not self.retrial_cards(state, actor, black=True):
                            continue
                        if skill == 'guicai':
                            frame.local['guicai_actor'] = str(actor)
                            current_match = action.pattern.matches(state, card_id, action.player_id)
                            preferred = tuple(str(cid) for cid in self.retrial_cards(state, actor)
                                              if action.pattern.matches(state, cid, action.player_id) != current_match)
                            frame.local['guicai_preferred'] = '|'.join(preferred)
                            frame.step_index = 4
                            return StepResult.ask(PendingRequest(f'{action.action_id}:guicai:{actor}', actor,
                                RequestType.YES_NO, '判定牌已亮出，是否发动【鬼才】改判？',
                                action.action_id, frame.frame_id,
                                choices=(f'current:{int(current_match)}', *(f'better:{cid}' for cid in preferred)),
                                subject_player_id=action.player_id))
                        elif skill == 'jilue':
                            frame.local['guicai_actor'] = str(actor)
                            frame.step_index = 9
                            return StepResult.ask(PendingRequest(
                                f'{action.action_id}:jilue-guicai:{actor}', actor,
                                RequestType.YES_NO, '是否弃一枚忍标记发动【极略·鬼才】？',
                                action.action_id, frame.frame_id,
                                subject_player_id=action.player_id))
                        elif skill == 'guidao':
                            frame.local['guidao_actor'] = str(actor)
                            candidates = self.retrial_cards(state, actor, black=True)
                            leiji = ':leiji:' in action.action_id
                            current_suit = effective_suit(state, card_id, action.player_id)
                            current_match = action.pattern.matches(state, card_id, action.player_id)
                            preferred = tuple(str(cid) for cid in candidates
                                              if (effective_suit(state, cid, action.player_id) is Suit.SPADE
                                                  and current_suit is not Suit.SPADE
                                                  or effective_suit(state, cid, action.player_id) is Suit.CLUB
                                                  and current_suit not in (Suit.SPADE, Suit.CLUB))
                                              if leiji) if leiji else tuple(str(cid) for cid in candidates
                                                  if action.pattern.matches(state, cid, action.player_id) != current_match)
                            frame.local['guidao_preferred'] = '|'.join(preferred)
                            frame.step_index = 6
                            return StepResult.ask(PendingRequest(f'{action.action_id}:guidao:{actor}', actor,
                                RequestType.YES_NO,
                                '雷击判定：是否发动【鬼道】改判？' if leiji else '判定牌已亮出，是否发动【鬼道】改判？',
                                action.action_id, frame.frame_id,
                                choices=(f'current:{int(current_match)}',
                                         *(f'better:{cid}' for cid in preferred)),
                                subject_player_id=action.player_id))
            matched = action.pattern.matches(state, card_id, action.player_id)
            frame.local["matched"] = matched
            frame.local["final_face"] = {"judged_player_id": action.player_id,
                "effective_suit": effective_suit(state, card_id, action.player_id).value,
                "effective_color": effective_color(state, card_id, action.player_id).value}
            self.recorder.record(Event(f"{action.action_id}:result", "judgment_result",
                                       action.player_id, metadata={"card_id": str(card_id), "matched": matched, **frame.local.get("final_face", {})}))
            frame.step_index = 2
            return StepResult.continue_()
        if (frame.step_index == 2 and self.skills is not None
                and self.skills.has(state, action.player_id, 'tiandu')
                and state.players[action.player_id].is_alive):
            frame.step_index = 3
            return StepResult.ask(PendingRequest(f'{action.action_id}:tiandu', action.player_id,
                RequestType.YES_NO, '自己的判定牌结算后，是否发动【天妒】获得之？',
                action.action_id, frame.frame_id))
        if frame.step_index == 2 and action.success_destination is not None and frame.local['matched']:
            return self._finish(state, frame, card_id, action.success_destination)
        if frame.step_index == 2 and action.gain_on_match and frame.local['matched']:
            return self._finish(state, frame, card_id, ZoneRef(ZoneType.HAND, action.player_id))
        if frame.step_index == 3:
            obtain = frame.decision is True or (action.gain_on_match and frame.local['matched'])
            frame.decision = None
            return self._finish(state, frame, card_id,
                                ZoneRef(ZoneType.HAND, action.player_id) if obtain else
                                action.success_destination if action.success_destination is not None and frame.local['matched']
                                else ZoneRef(ZoneType.DISCARD_PILE))
        return self._finish(state, frame, card_id, ZoneRef(ZoneType.DISCARD_PILE))
