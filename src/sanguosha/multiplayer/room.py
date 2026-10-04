"""Five-seat authoritative room and match orchestration."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.game_modes import game_mode
from sanguosha.decisions.ai import AIDecisionProvider
from sanguosha.engine.requests import Decision, PendingRequest, RequestType, PASS_RESPONSE
from sanguosha.engine.events import (Event, CardUsedEvent, CardRespondedEvent, TrickTargetsDeclaredEvent,
                                     VirtualResponseEvent, DamageDealtEvent, HpRecoveredEvent,
                                     PlayerDiedEvent, GameEndedEvent, TurnStartedEvent, TurnEndedEvent,
                                     CardMovedEvent, DyingRequiredEvent)
from sanguosha.engine.rng import PythonRandomSource
from sanguosha.model.enums import Identity
from sanguosha.model.ids import CharacterId, PlayerId
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.pregame import Pregame, ROLE_SET, SEATS, SetupStage
from sanguosha.projection import project_for_human
from sanguosha.session import GameSession

from .protocol import envelope, serialize_projection, serialize_request

Send = Callable[[dict], None]
from sanguosha.timing import HUMAN_DECISION_TIMEOUT_SECONDS
TIMEOUT_SECONDS = HUMAN_DECISION_TIMEOUT_SECONDS


class RoomPhase(StrEnum):
    OPEN = "OPEN"
    READY = "READY"
    DRAFT = "DRAFT"
    IN_GAME = "IN_GAME"
    FINISHED = "FINISHED"


class Controller(StrEnum):
    EMPTY = "EMPTY"
    HUMAN = "HUMAN"
    AI = "AI"


@dataclass(slots=True)
class Seat:
    player_id: PlayerId
    name: str = ""
    controller: Controller = Controller.EMPTY
    ready: bool = False
    connected: bool = False
    token: str = ""
    send: Send | None = None

    def public(self) -> dict:
        return {"seat_id": str(self.player_id), "player_name": self.name,
                "controller_type": self.controller.value, "ready": self.ready,
                "connected": self.connected}


class RoomError(ValueError):
    pass


class NetworkDecisionProvider:
    """Bridge engine requests to one remote human and validate the reply."""

    def __init__(self, room: "MultiplayerRoom"):
        self.room = room

    def dispatch(self, request: PendingRequest) -> None:
        room = self.room
        if request.request_id != room._last_request_id:
            room._last_request_id = request.request_id
            room.request_deadline = time.time() + room.timeout_seconds
            room._sync()

    def validate(self, pid: PlayerId, decision: Decision) -> PendingRequest:
        room = self.room
        request = room.session.engine.pending_request
        if request is None or request.player_id != pid or request.request_id != decision.request_id:
            raise RoomError("stale, duplicate, or wrong-player decision")
        if room.request_deadline is not None and time.time() >= room.request_deadline:
            room.poll()
            raise RoomError("request timed out")
        request.validate(decision.value)
        return request


class MultiplayerRoom:
    """One game state lives here; a send callback receives only viewer-safe messages."""

    def __init__(self, *, seed: int | None = None, timeout_seconds: float = TIMEOUT_SECONDS,
                 review_god_lvbu: bool = False, mode_id: str = 'military-five',
                 allow_gods: bool = True):
        self.mode = game_mode(mode_id)
        self.allow_gods = True
        self.seats = {pid: Seat(pid) for pid in self.mode.seats}
        self.phase = RoomPhase.OPEN
        self.host_id: PlayerId | None = None
        self.seed = seed
        self.review_god_lvbu = review_god_lvbu
        self.timeout_seconds = timeout_seconds
        self.pregame: Pregame | None = None
        self.draft_requests: dict[PlayerId, PendingRequest] = {}
        self.draft_deadlines: dict[PlayerId, float] = {}
        self.session: GameSession | None = None
        self.request_deadline: float | None = None
        self.accepted_request_id: str | None = None
        self._last_request_id: str | None = None
        self._seen_events = 0
        self._ai = AIDecisionProvider(self.mode.seats[0])
        self.network_decisions = NetworkDecisionProvider(self)
        self._revision = 0
        self.auto_step_budget = 20_000
        self.suspend_on_budget = False
        self.ai_presentation = False
        self.ai_deadline: float | None = None
        self._ai_wait_request: str | None = None

    def join(self, name: str, send: Send, *, token: str | None = None) -> tuple[PlayerId, str]:
        if token:
            seat = next((s for s in self.seats.values() if s.token == token and s.controller is Controller.HUMAN), None)
            if seat is None:
                raise RoomError("invalid reconnect token")
            seat.connected, seat.send = True, send
            self._send_current(seat.player_id)
            self._broadcast(envelope("PLAYER_RECONNECTED", seat_id=str(seat.player_id)))
            self._broadcast_lobby()
            return seat.player_id, token
        if self.phase not in (RoomPhase.OPEN, RoomPhase.READY):
            raise RoomError("game has already started")
        if not isinstance(name, str) or not name.strip() or len(name) > 32:
            raise RoomError("player name must contain 1–32 characters")
        seat = next((s for s in self.seats.values() if s.controller is Controller.EMPTY), None)
        if seat is None:
            raise RoomError("room is full")
        seat.name = name.strip()
        seat.controller = Controller.HUMAN
        seat.connected, seat.send = True, send
        seat.token = secrets.token_urlsafe(32)
        if self.host_id is None:
            self.host_id = seat.player_id
        self._broadcast_lobby()
        return seat.player_id, seat.token

    def disconnect(self, pid: PlayerId) -> None:
        seat = self.seats[pid]
        if not seat.connected:
            return
        seat.connected, seat.send = False, None
        self._broadcast(envelope("PLAYER_DISCONNECTED", seat_id=str(pid)))
        self._broadcast_lobby()

    def leave(self, pid: PlayerId) -> None:
        self.disconnect(pid)
        if self.phase in (RoomPhase.OPEN, RoomPhase.READY):
            self.seats[pid] = Seat(pid)
            if pid == self.host_id:
                self.host_id = next((s.player_id for s in self.seats.values()
                                     if s.controller is Controller.HUMAN), None)
            self.phase = RoomPhase.READY if any(s.ready for s in self.seats.values()) else RoomPhase.OPEN
            self._broadcast_lobby()

    def ready(self, pid: PlayerId, value: bool) -> None:
        if self.phase not in (RoomPhase.OPEN, RoomPhase.READY) or pid == self.host_id:
            raise RoomError("ready is unavailable")
        if self.seats[pid].controller is not Controller.HUMAN or not self.seats[pid].connected or type(value) is not bool:
            raise RoomError("invalid ready state")
        self.seats[pid].ready = value
        self.phase = RoomPhase.READY if any(s.ready for s in self.seats.values()) else RoomPhase.OPEN
        self._broadcast_lobby()

    def configure(self, host_id: PlayerId, *, mode_id: str | None = None,
                  allow_gods: bool | None = None) -> None:
        if host_id != self.host_id or self.phase not in (RoomPhase.OPEN, RoomPhase.READY):
            raise RoomError('only the host can configure an open room')
        if mode_id is not None and mode_id != self.mode.mode_id:
            mode = game_mode(mode_id)
            removed = set(self.seats) - set(mode.seats)
            if any(self.seats[pid].controller is Controller.HUMAN for pid in removed):
                raise RoomError('cannot remove an occupied human seat')
            self.seats = {pid: self.seats.get(pid, Seat(pid)) for pid in mode.seats}
            self.mode = mode
            self._ai = AIDecisionProvider(mode.seats[0])
        self._broadcast_lobby()

    def kick(self, host_id: PlayerId, target_id: PlayerId) -> None:
        if host_id != self.host_id or self.phase not in (RoomPhase.OPEN, RoomPhase.READY):
            raise RoomError('only the host can kick before the game starts')
        if target_id == host_id or target_id not in self.seats:
            raise RoomError('invalid kick target')
        seat = self.seats[target_id]
        if seat.controller is not Controller.HUMAN:
            raise RoomError('target is not a human player')
        self._send(target_id, envelope('KICKED', reason='房主已将你移出房间'))
        self.seats[target_id] = Seat(target_id)
        self.phase = RoomPhase.READY if any(s.ready for s in self.seats.values()) else RoomPhase.OPEN
        self._broadcast_lobby()

    def start(self, pid: PlayerId) -> None:
        if pid != self.host_id or not self.seats[pid].connected:
            raise RoomError("only the host can start")
        if self.phase not in (RoomPhase.OPEN, RoomPhase.READY):
            raise RoomError("game has already started")
        if any(s.controller is Controller.HUMAN and s.player_id != pid and not s.ready for s in self.seats.values()):
            raise RoomError("all guests must be ready")
        for seat in self.seats.values():
            if seat.controller is Controller.EMPTY:
                seat.controller, seat.name = Controller.AI, f"电脑{seat.player_id[1:]}"
        rng = PythonRandomSource(self.seed)
        roles = list(self.mode.roles)
        rng.shuffle(roles)
        self.pregame = Pregame(rng, dict(zip(self.mode.seats, roles)), (),
                               SetupStage.CHOOSE_GENERAL, mode_id=self.mode.mode_id)
        self.phase = RoomPhase.DRAFT
        self._broadcast_lobby()
        for seat in self.seats.values():
            if seat.controller is Controller.HUMAN:
                self._new_draft_request(seat.player_id)
        self._complete_draft_if_ready()

    def _new_draft_request(self, pid: PlayerId) -> None:
        assert self.pregame is not None
        pool = PLAYABLE_GENERAL_POOL
        remaining = [c.id for c in pool if c.id not in self.pregame.generals.values()]
        self.pregame.rng.shuffle(remaining)
        candidates = tuple(map(str, remaining[:9])) + (('forest_god_lvbu',) if self.review_god_lvbu and pid == self.host_id else (str(remaining[9]),))
        first_choices = {request.choices[0] for other_pid, request in self.draft_requests.items() if other_pid != pid}
        if candidates[0] in first_choices:
            alternative = next((choice for choice in candidates[1:] if choice not in first_choices), None)
            if alternative is not None:
                candidates = (alternative,) + tuple(choice for choice in candidates if choice != alternative)
        old = self.draft_requests.get(pid)
        serial = int(old.request_id.rsplit(":", 1)[-1]) + 1 if old else 1
        request = PendingRequest(f"draft:{pid}:{serial}", pid, RequestType.CHOOSE_OPTION,
                                 "选择武将并确认", "draft", "draft", choices=candidates)
        self.draft_requests[pid] = request
        self.draft_deadlines[pid] = time.time() + self.timeout_seconds
        self._send_draft(pid)

    def _send_draft(self, pid: PlayerId) -> None:
        assert self.pregame is not None
        request = self.draft_requests[pid]
        self._send(pid, envelope("DRAFT_REQUEST", request=serialize_request(
            request, max(0, int((self.draft_deadlines[pid] - time.time()) * 1000))),
            identity=self.pregame.identities[pid].value, lord_id=str(self.pregame.lord_id)))

    def submit(self, pid: PlayerId, decision: Decision, *, defer_resolution: bool = False,
               send_ack: bool = True) -> None:
        if self.seats[pid].controller is not Controller.HUMAN or not self.seats[pid].connected:
            raise RoomError("player is not connected")
        if decision.player_id != pid:
            raise RoomError("decision owner mismatch")
        if self.phase is RoomPhase.DRAFT:
            request = self.draft_requests.get(pid)
            if request is None or request.request_id != decision.request_id:
                if request is not None:
                    self._send_draft(pid)
                raise RoomError("stale or duplicate draft decision")
            request.validate(decision.value)
            if time.time() >= self.draft_deadlines[pid]:
                self.poll()
                raise RoomError('draft request timed out')
            assert self.pregame is not None
            if decision.value in self.pregame.generals.values():
                self._new_draft_request(pid)
                raise RoomError("general already taken; new candidates sent")
            self.pregame.generals[pid] = CharacterId(decision.value)
            del self.draft_requests[pid]
            del self.draft_deadlines[pid]
            if defer_resolution:
                self.accepted_request_id = decision.request_id
            if send_ack:
                self._send(pid, envelope("DECISION_RESULT", request_id=decision.request_id, accepted=True))
            if not defer_resolution:
                self._complete_draft_if_ready()
            return
        if self.phase is not RoomPhase.IN_GAME or self.session is None:
            raise RoomError("no active game request")
        request = self.session.engine.pending_request
        if request is None or request.request_id != decision.request_id:
            self._send_current(pid)
            raise RoomError("stale request; current response refreshed")
        if request is not None and request.request_id == decision.request_id:
            decision = self._resolve_hidden_choice(request, decision)
        self.network_decisions.validate(pid, decision)
        if isinstance(decision.value, dict):
            from dataclasses import replace
            from sanguosha.engine.card_use import UseCardAction
            frame = self.session.engine.stack.top()
            phase_handler = self.session.engine.registry.handler_for(frame.action)
            body = phase_handler.bodies.body_for(frame.action.phase)
            built = body.provider.build_action(self.session.state, pid, decision.value['option'],
                                               f'{frame.frame_id}-play-{frame.cursor-1}')
            if not isinstance(built, UseCardAction):
                raise RoomError('combined decision requires a physical card')
            built = replace(built, target_ids=decision.value['targets'], targets_confirmed=True)
            self.session.engine.registry.handler_for(built).validate_start(self.session.state, built)
        self.session.engine.submit_decision(decision, defer_resolution=defer_resolution)
        if send_ack:
            self._send(pid, envelope("DECISION_RESULT", request_id=decision.request_id, accepted=True))
        self._last_request_id = None
        self.request_deadline = None
        if defer_resolution:
            self.accepted_request_id = decision.request_id
        if not defer_resolution:
            self.pump()

    def resolve_accepted(self) -> None:
        """Advance a committed decision after its ACK has been sent."""
        if self.phase is RoomPhase.DRAFT:
            self._complete_draft_if_ready()
        elif self.phase is RoomPhase.IN_GAME:
            self.pump()
        self.accepted_request_id = None

    def _complete_draft_if_ready(self) -> None:
        if self.draft_requests:
            return
        assert self.pregame is not None
        pool = PLAYABLE_GENERAL_POOL
        available = [c.id for c in pool if c.id not in self.pregame.generals.values()]
        for seat in self.seats.values():
            if seat.controller is Controller.AI:
                selected = self.pregame.rng.choice(available)
                available.remove(selected)
                self.pregame.generals[seat.player_id] = selected
        self.pregame.stage = SetupStage.COMPLETE
        self.session = GameSession.new_game(military=True, setup=self.pregame)
        if self.review_god_lvbu:
            self._prepare_lvbu_review_match()
        self.phase = RoomPhase.IN_GAME
        self._broadcast_lobby()
        self.pump()

    def _prepare_lvbu_review_match(self) -> None:
        """Prepare cards and rage only in the explicit local review fixture."""
        from sanguosha.model.zones import ZoneRef, ZoneType
        state = self.session.state
        actor = self.host_id
        if state.players[actor].character_id != 'forest_god_lvbu':
            return
        state.players[actor].marks['rage'] = 8
        hand = state.zones[ZoneRef(ZoneType.HAND, actor)].card_ids
        for definition in ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash'):
            if any(state.cards[cid].definition_id == definition for cid in hand):
                continue
            for ref, zone in state.zones.items():
                if ref.zone_type is ZoneType.DRAW_PILE:
                    found = next((cid for cid in zone.card_ids if state.cards[cid].definition_id == definition), None)
                    if found is not None:
                        zone.card_ids.remove(found)
                        hand.append(found)
                    break

    def pump(self, max_steps: int | None = None) -> None:
        if self.session is None:
            return
        if (self.session.engine.pending_request is None
                and getattr(self.session.engine, 'stack', None) is not None
                and not self.session.engine.stack.is_empty()):
            self.session.engine.run_until_blocked()
        max_steps = self.auto_step_budget if max_steps is None else max_steps
        steps = 0
        while self.session.state.status is not GameStatus.FINISHED:
            steps += 1
            if steps > max_steps:
                if self.suspend_on_budget:
                    return
                raise RuntimeError("multiplayer match step limit exceeded")
            request = self.session.engine.pending_request
            if request is not None and self.seats[request.player_id].controller is Controller.HUMAN:
                if (request.request_type is RequestType.RESPOND_WITH_CARD
                        and request.allow_pass and not request.has_legal_response()):
                    self.session.engine.submit_decision(Decision(request.request_id, request.player_id, PASS_RESPONSE))
                    continue
                self.network_decisions.dispatch(request)
                return
            if request is not None:
                if request.request_type in (RequestType.CHOOSE_OPTION, RequestType.RESPOND_WITH_CARD,
                                             RequestType.YES_NO):
                    if self._ai_wait_request != request.request_id:
                        from hashlib import sha256
                        candidates = len(request.choices) + len(request.eligible_card_ids)
                        complexity = ('simple' if request.request_type is RequestType.RESPOND_WITH_CARD
                                      else 'complex' if candidates > 8 else 'ordinary')
                        self.session.events.record(Event(
                            'thinking:' + sha256(request.request_id.encode()).hexdigest()[:24],
                            'ai_thinking', request.player_id, metadata={'complexity': complexity}))
                        if self.ai_presentation:
                            self._ai_wait_request = request.request_id
                            self.ai_deadline = time.time() + {'simple': 1.5, 'ordinary': 2.4, 'complex': 3.6}[complexity]
                            self._sync()
                            return
                    if self.ai_deadline is not None and time.time() < self.ai_deadline:
                        return
                self._ai_wait_request = None
                self.ai_deadline = None
                self.session.engine.submit_decision(self._ai.decide(self.session.state, request))
            else:
                self.session.step_auto()
        self.phase = RoomPhase.FINISHED
        self._sync()
        self._broadcast_lobby()
        self._broadcast(envelope("GAME_OVER", result=self.session.state.victory.label if self.session.state.victory else ""))

    def poll(self) -> None:
        now = time.time()
        if self.ai_deadline is not None and now >= self.ai_deadline:
            self.pump()
        if self.phase is RoomPhase.DRAFT:
            for pid, deadline in tuple(self.draft_deadlines.items()):
                if now >= deadline:
                    request = self.draft_requests[pid]
                    self.pregame.generals[pid] = CharacterId(next(c for c in request.choices
                                                                   if c not in self.pregame.generals.values()))
                    del self.draft_requests[pid]
                    del self.draft_deadlines[pid]
            self._complete_draft_if_ready()
        elif self.phase is RoomPhase.IN_GAME and self.session and self.request_deadline is not None and now >= self.request_deadline:
            request = self.session.engine.pending_request
            if request is not None:
                self.session.engine.submit_decision(Decision(request.request_id, request.player_id, request.timeout_value()))
                self._last_request_id = None
                self.request_deadline = None
                self.pump()

    def takeover_ai(self, host_id: PlayerId, target_id: PlayerId) -> None:
        if host_id != self.host_id or self.phase not in (RoomPhase.DRAFT, RoomPhase.IN_GAME):
            raise RoomError("only the host can transfer a disconnected seat")
        seat = self.seats.get(target_id)
        if seat is None or seat.controller is not Controller.HUMAN or seat.connected:
            raise RoomError("seat is not a disconnected human")
        seat.controller, seat.token = Controller.AI, ""
        self._broadcast_lobby()
        if self.phase is RoomPhase.DRAFT and target_id in self.draft_requests:
            request = self.draft_requests.pop(target_id)
            self.draft_deadlines.pop(target_id)
            self.pregame.generals[target_id] = CharacterId(next(c for c in request.choices
                                                                 if c not in self.pregame.generals.values()))
            self._complete_draft_if_ready()
        else:
            self.pump()

    def _sync(self) -> None:
        assert self.session is not None
        self._revision += 1
        request = self.session.engine.pending_request
        for seat in self.seats.values():
            if seat.controller is Controller.HUMAN and seat.connected:
                view = project_for_human(self.session.state, self.session.definitions,
                                         seat.player_id, self.session.character_names)
                active_id = request.request_id if request is not None and request.player_id == seat.player_id else None
                self._send(seat.player_id, envelope("PROJECTION_UPDATE", revision=self._revision,
                                                    active_request_id=active_id,
                                                    projection=self._named_projection(view, seat.player_id)))
        for event in self.session.events.events[self._seen_events:]:
            public = self._public_event(event)
            if public:
                self._broadcast(envelope("PUBLIC_EVENT", event=public))
        self._seen_events = len(self.session.events.events)
        if request is not None and self.seats[request.player_id].controller is Controller.HUMAN:
            self._send(request.player_id, envelope("PENDING_REQUEST", request=self._request_payload(request)))

    def _send_current(self, pid: PlayerId) -> None:
        self._send(pid, envelope("LOBBY_STATE", **self.lobby_state()))
        if self.phase is RoomPhase.DRAFT and pid in self.draft_requests:
            self._send_draft(pid)
        elif self.session is not None:
            view = project_for_human(self.session.state, self.session.definitions, pid, self.session.character_names)
            request = self.session.engine.pending_request
            active_id = request.request_id if request is not None and request.player_id == pid else None
            self._send(pid, envelope("PROJECTION_UPDATE", revision=self._revision,
                                     active_request_id=active_id,
                                     projection=self._named_projection(view, pid)))
            if request is not None and request.player_id == pid and self.request_deadline is not None:
                self._send(pid, envelope("PENDING_REQUEST", request=self._request_payload(request)))

    def _hidden_hand_aliases(self, request: PendingRequest) -> dict[str, str]:
        if (self.session is None or request.subject_player_id is None
                or request.subject_player_id == request.player_id
                or request.request_type not in (RequestType.CHOOSE_CARD, RequestType.CHOOSE_CARDS)):
            return {}
        hand = self.session.state.cards_in(ZoneRef(ZoneType.HAND, request.subject_player_id))
        return {f'hidden-hand:{index}': card_id for index, card_id in enumerate(hand, 1)
                if card_id in request.eligible_card_ids}

    def _request_payload(self, request: PendingRequest) -> dict:
        remaining = max(0, int((self.request_deadline - time.time()) * 1000)) if self.request_deadline else 0
        payload = serialize_request(request, remaining)
        from .choice_labels import choice_labels
        payload['choice_labels'] = choice_labels(self, request)
        aliases = self._hidden_hand_aliases(request)
        if aliases:
            reverse = {card_id: alias for alias, card_id in aliases.items()}
            payload['eligible_card_ids'] = [reverse.get(card_id, card_id)
                                            for card_id in request.eligible_card_ids]
        return payload

    def _resolve_hidden_choice(self, request: PendingRequest, decision: Decision) -> Decision:
        aliases = self._hidden_hand_aliases(request)
        value = decision.value
        if isinstance(value, str):
            value = aliases.get(value, value)
        elif isinstance(value, tuple):
            value = tuple(aliases.get(item, item) for item in value)
        return Decision(decision.request_id, decision.player_id, value)

    def lobby_state(self) -> dict:
        return {"phase": self.phase.value, "host_id": self.host_id,
                "mode_id": self.mode.mode_id, "seat_count": self.mode.seat_count,
                "allow_gods": self.allow_gods,
                "seats": [seat.public() for seat in self.seats.values()]}

    def _named_projection(self, view, viewer):
        result = serialize_projection(view)
        for player in result["players"]:
            pid = PlayerId(player["player_id"])
            player["name"] = ("你 · " if pid == viewer else "") + self.seats[pid].name
        return result

    def _public_event(self, event) -> dict | None:
        """Allowlist semantic facts; card instance IDs and hidden moves are excluded."""
        result = {"kind": type(event).__name__, "event_id": event.event_id}
        if isinstance(event, Event) and event.event_type == 'ai_thinking':
            result.update(kind='AIThinkingEvent', source_id=str(event.source_id),
                          complexity=event.metadata['complexity'])
        elif isinstance(event, Event) and event.event_type in ('skill_wuwei', 'skill_shenfen'):
            result.update(kind='GodSkillEvent', source_id=str(event.source_id),
                          target_ids=list(map(str, event.target_ids)),
                          skill_id=str(event.metadata['skill_id']), level=int(event.metadata['level']))
        elif isinstance(event, Event) and event.event_type in ('guhuo_declare', 'guhuo_reveal'):
            result.update(kind='GuhuoEvent', source_id=str(event.source_id),
                          stage='declare' if event.event_type == 'guhuo_declare' else 'reveal',
                          declared=str(event.metadata['declared']))
            if event.event_type == 'guhuo_reveal':
                result.update(actual=str(event.metadata['actual']),
                              suit=str(event.metadata['suit']), truth=bool(event.metadata['truth']))
        elif isinstance(event, (CardUsedEvent, TrickTargetsDeclaredEvent)):
            result.update(source_id=str(event.player_id), target_ids=list(map(str, event.target_ids)))
            definition_id = (event.virtual_definition_id or str(self.session.state.cards[event.card_id].definition_id)
                             if isinstance(event, CardUsedEvent) else event.definition_id)
            result["definition_id"] = str(definition_id)
            result["card_name"] = self.session.definitions.get(definition_id).name
        elif isinstance(event, (CardRespondedEvent, VirtualResponseEvent)):
            result.update(source_id=str(event.player_id), response_number=event.response_number,
                          response_total=event.response_total)
            definition_id = (event.response_definition_id or str(self.session.state.cards[event.card_id].definition_id)
                             if isinstance(event, CardRespondedEvent) else event.response_definition_id)
            result["definition_id"] = str(definition_id)
        elif isinstance(event, (DamageDealtEvent, HpRecoveredEvent)):
            result.update(source_id=str(event.source_id) if event.source_id else "",
                          target_id=str(event.target_id), amount=event.amount)
        elif isinstance(event, PlayerDiedEvent):
            result.update(target_id=str(event.player_id), source_id=str(event.killer_id) if event.killer_id else "")
        elif isinstance(event, (TurnStartedEvent, TurnEndedEvent)):
            result.update(player_id=str(event.player_id), turn_number=event.turn_number)
        elif isinstance(event, DyingRequiredEvent):
            result.update(player_id=str(event.target_id))
        elif isinstance(event, CardMovedEvent) and event.reason == 'discard':
            # Count only; never serialize hand IDs, hidden draws or move metadata.
            from hashlib import sha256
            result.update(kind='DiscardEvent', event_id=sha256(event.event_id.encode()).hexdigest()[:24],
                          player_id=str(event.actor_id or ''), count=len(event.card_ids))
        elif isinstance(event, Event) and event.event_type == 'card_revealed':
            card = self.session.state.cards[event.metadata['card_id']]
            result.update(kind='CardRevealedEvent', source_id=str(event.source_id),
                          definition_id=str(card.definition_id), card_name=self.session.definitions.get(card.definition_id).name,
                          suit=card.suit.value, rank=card.rank, skill_id=event.metadata.get('skill_id', ''))
        elif isinstance(event, Event) and event.event_type == 'after_judgment':
            result.update(kind='JudgmentEvent', source_id=str(event.source_id or ''),
                          matched=bool(event.metadata.get('matched', False)))
        elif isinstance(event, Event) and event.event_type.startswith('skill_'):
            from sanguosha.content.characters.standard import ALL_SKILL_CATALOGUE
            skill_id = event.event_type.removeprefix('skill_')
            skill = next((item for item in ALL_SKILL_CATALOGUE if str(item.id) == skill_id), None)
            if skill is None:
                return None
            result.update(kind='SkillEvent', source_id=str(event.source_id or ''), skill_name=skill.name)
        elif isinstance(event, GameEndedEvent):
            result.update(label=event.label, winner_ids=list(map(str, event.winner_ids)))
        else:
            return None
        return result

    def _broadcast_lobby(self) -> None:
        self._broadcast(envelope("LOBBY_STATE", **self.lobby_state()))

    def _broadcast(self, message: dict) -> None:
        for seat in self.seats.values():
            if seat.controller is Controller.HUMAN and seat.connected and seat.send:
                seat.send(message)

    def _send(self, pid: PlayerId, message: dict) -> None:
        seat = self.seats[pid]
        if seat.connected and seat.send:
            seat.send(message)
