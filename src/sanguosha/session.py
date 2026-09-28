"""Headless five-player match composition and one-turn-at-a-time orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from sanguosha.content.cards.basic import register_basic_cards
from sanguosha.decisions.ai import AIDecisionProvider
from sanguosha.engine.actions import Action
from sanguosha.engine.card_effects import PeachEffectAction, PeachEffectHandler, SlashEffectAction, SlashEffectHandler
from sanguosha.engine.card_moves import CardMoveService
from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.engine.card_rules import CardRuleRegistry, CardUseValidator, TargetValidator
from sanguosha.engine.card_use import LegalPlayActionProvider, UseCardAction, UseCardActionHandler
from sanguosha.engine.damage import DamageAction, DamageActionHandler
from sanguosha.engine.death import DeathAction, DeathActionHandler
from sanguosha.engine.deck import DeckService, DrawCardsAction, DrawCardsHandler, DrawPhaseBody, basic_deck, classic_military_deck
from sanguosha.engine.discard import DiscardPhaseBody
from sanguosha.engine.dying import DyingAction, DyingActionHandler
from sanguosha.engine.engine import EngineStatus, GameEngine
from sanguosha.engine.events import Event, EventRecorder
from sanguosha.engine.identity import IdentitySystem
from sanguosha.engine.phases import PhaseAction, PhaseActionHandler, standard_phase_bodies
from sanguosha.engine.recovery import RecoverAction, RecoverActionHandler
from sanguosha.engine.registry import ActionHandlerRegistry
from sanguosha.engine.requests import Decision, PASS_RESPONSE
from sanguosha.engine.response import RespondWithCardAction, RespondWithCardHandler
from sanguosha.engine.rng import PythonRandomSource
from sanguosha.engine.turn_order import next_alive_player
from sanguosha.engine.turns import TurnAction, TurnActionHandler
from sanguosha.model.enums import Identity, Phase
from sanguosha.model.ids import CharacterId, PlayerId
from sanguosha.model.player import PlayerState
from sanguosha.model.state import GameState, GameStatus
from sanguosha.pregame import Pregame, SetupStage


CHARACTER_NAMES = ("曹操", "刘备", "孙权", "吕布", "关羽")
IDENTITIES = (Identity.LORD, Identity.LOYALIST, Identity.REBEL, Identity.REBEL, Identity.RENEGADE)


@dataclass(slots=True)
class GameSession:
    engine: GameEngine
    events: EventRecorder
    definitions: CardDefinitionRegistry
    human_id: PlayerId
    ai: AIDecisionProvider
    character_names: dict[PlayerId, str]
    skills: object | None = None
    declined_nullification_windows: set[str] = field(default_factory=set)

    def nullification_window_id(self, request=None) -> str | None:
        request = request or self.engine.pending_request
        if request is None or request.required_definition_id != "trick.nullification":
            return None
        from sanguosha.engine.military_tricks import NullificationWindow
        return next((frame.action.action_id for frame in reversed(self.engine.stack.snapshot())
                     if isinstance(frame.action, NullificationWindow)), None)

    def pass_unavailable_nullification(self) -> bool:
        """Resolve only the current human counter request using its rule candidates."""
        request = self.engine.pending_request
        window = self.nullification_window_id(request)
        if window is None or request.player_id != self.human_id:
            return False
        if window not in self.declined_nullification_windows and request.has_legal_response():
            return False
        self.submit_human(Decision(request.request_id, request.player_id, PASS_RESPONSE))
        return True

    def decline_nullification_window(self) -> None:
        window = self.nullification_window_id()
        if window is None:
            raise ValueError("no nullification window is pending")
        self.declined_nullification_windows.add(window)

    def clear_finished_nullification_windows(self) -> None:
        from sanguosha.engine.military_tricks import NullificationWindow
        live = {frame.action.action_id for frame in self.engine.stack.snapshot()
                if isinstance(frame.action, NullificationWindow)}
        self.declined_nullification_windows.intersection_update(live)

    @classmethod
    def new_game(cls, seed: int = 6, *, military: bool = False, five_generals: bool = False,
                 setup: Pregame | None = None) -> "GameSession":
        if setup is not None and setup.stage is not SetupStage.COMPLETE:
            raise ValueError('general draft must finish before starting a match')
        if setup is not None and not military:
            raise ValueError('standard general draft requires the military ruleset')
        rng = setup.rng if setup is not None else PythonRandomSource(seed)
        card_instances, draw_zone = classic_military_deck(rng) if military else basic_deck(rng)
        ids = tuple(PlayerId(f"p{i}") for i in range(1, 6))
        if five_generals and not military:
            raise ValueError('five generals require the military ruleset')
        skills = None
        characters = None
        if five_generals or setup is not None:
            from sanguosha.engine.skills import SkillRegistry
            skills = SkillRegistry()
            # Seat order follows the original portrait order.
            characters = (tuple(skills.characters[setup.generals[pid]] for pid in ids) if setup is not None else
                          tuple(skills.characters[key] for key in ('caocao','liubei','sunquan','lvbu','guanyu')))
        identities = tuple(setup.identities[pid] for pid in ids) if setup is not None else IDENTITIES
        players = {}
        for index, pid in enumerate(ids):
            character = characters[index] if characters else None
            maximum = character.max_hp + (1 if identities[index] is Identity.LORD and characters else 0) if character else 4
            players[pid] = PlayerState(pid, index, character.id if character else CharacterId(f'blank-{index+1}'),
                                       identities[index], maximum, maximum)
        state = GameState(
            "classic-military" if military else "t5-basic-identity", players=players, seat_order=ids,
            cards=card_instances, zones={draw_zone.ref: draw_zone},
            status=GameStatus.ACTIVE,
            revealed_identities={setup.lord_id} if setup is not None else {ids[0]},
        )
        events = EventRecorder()
        events.record(Event("game-start", "game-start"))
        if military:
            from sanguosha.engine.military_equipment import MilitaryMoveService
            moves = MilitaryMoveService(events, skills)
        else:
            moves = CardMoveService(events)
        deck = DeckService(rng, moves)
        for pid in ids:
            deck.draw(state, pid, 4, f"initial-deal:{pid}")
        definitions = CardDefinitionRegistry()
        card_rules = CardRuleRegistry()
        register_basic_cards(definitions, card_rules)
        validator = CardUseValidator(definitions, card_rules, TargetValidator())
        bodies = standard_phase_bodies(LegalPlayActionProvider(validator))
        bodies.register(Phase.DRAW, DrawPhaseBody(skills))
        bodies.register(Phase.DISCARD, DiscardPhaseBody(moves, skills, events))
        registry = ActionHandlerRegistry()
        registry.register(TurnAction, TurnActionHandler(events))
        registry.register(PhaseAction, PhaseActionHandler(bodies, events))
        registry.register(DrawCardsAction, DrawCardsHandler(deck))
        registry.register(UseCardAction, UseCardActionHandler(validator, moves, events, skills))
        registry.register(SlashEffectAction, SlashEffectHandler())
        registry.register(RespondWithCardAction, RespondWithCardHandler(moves, events))
        registry.register(PeachEffectAction, PeachEffectHandler())
        registry.register(RecoverAction, RecoverActionHandler(events))
        registry.register(DamageAction, DamageActionHandler(
            events, lambda action: DyingAction(f"{action.action_id}:dying-resolution", action.target_id, action.source_id),
        ))
        registry.register(DyingAction, DyingActionHandler(events, skills))
        from sanguosha.engine.hp import LoseHpAction, LoseHpHandler
        registry.register(LoseHpAction, LoseHpHandler(events))
        registry.register(DeathAction, DeathActionHandler(moves, IdentitySystem(), events))
        if military:
            from sanguosha.engine.military_basics import register_military_basics
            register_military_basics(definitions, card_rules, registry, moves, events, bodies, skills)
            from sanguosha.engine.military_tricks import register_military_tricks
            register_military_tricks(definitions, card_rules, registry, moves, events, deck, bodies, skills)
            from sanguosha.engine.judgment import JudgmentAction, JudgmentHandler
            registry.register(JudgmentAction, JudgmentHandler(moves, events, deck, skills))
            from sanguosha.engine.view_as import UseSpear,UseSpearHandler,MilitaryPlayOptions
            from sanguosha.engine.phases import PlayPhaseBody
            provider=MilitaryPlayOptions(validator)
            if skills is not None:
                from sanguosha.engine.skills import (SkillPlayOptions, RendeAction, RendeHandler,
                    ZhihengAction, ZhihengHandler, WushengUse, WushengUseHandler,
                    JijiangUse, JijiangUseHandler, AllianceResponse, AllianceResponseHandler,
                    KurouAction, KurouHandler, QingnangAction, QingnangHandler,
                    LianyingAction, LianyingHandler, XiaojiAction, XiaojiHandler,
                    GanglieAction, GanglieHandler)
                slash_rule = card_rules.get('basic.slash')
                provider = SkillPlayOptions(provider, skills, slash_rule)
                registry.register(RendeAction, RendeHandler(moves))
                registry.register(ZhihengAction, ZhihengHandler(moves))
                registry.register(WushengUse, WushengUseHandler(skills,moves,slash_rule))
                registry.register(JijiangUse, JijiangUseHandler(skills,slash_rule))
                registry.register(AllianceResponse, AllianceResponseHandler(skills))
                registry.register(KurouAction, KurouHandler(skills))
                registry.register(QingnangAction, QingnangHandler(skills, moves))
                registry.register(LianyingAction, LianyingHandler())
                registry.register(XiaojiAction, XiaojiHandler())
                registry.register(GanglieAction, GanglieHandler(moves))
            registry.register(UseSpear,UseSpearHandler(provider,moves))
            bodies.register(Phase.PLAY,PlayPhaseBody(provider))
            if skills is not None:
                from sanguosha.engine.skills import FinishSkillBody
                from sanguosha.engine.military_basics import MilitaryFinishBody
                bodies.register(Phase.FINISH, FinishSkillBody(skills, MilitaryFinishBody()))
        engine = GameEngine(state, registry)
        if military:
            engine.reaction_provider = moves.next_reaction
        return cls(
            engine, events, definitions, ids[0],
            AIDecisionProvider(ids[0]),
            {pid: characters[index].name for index, pid in enumerate(ids)} if setup is not None else dict(zip(ids, CHARACTER_NAMES)),
            skills,
        )

    @property
    def state(self) -> GameState:
        return self.engine.state

    def submit_human(self, decision: Decision) -> EngineStatus:
        request = self.engine.pending_request
        if request is None or request.player_id != self.human_id:
            raise ValueError("no human decision is pending")
        return self.engine.submit_decision(decision)

    def step_auto(self) -> bool:
        """Perform at most one AI decision or start one turn; Qt schedules each call."""
        if self.state.status is GameStatus.FINISHED:
            return False
        self.clear_finished_nullification_windows()
        if self.pass_unavailable_nullification():
            return True
        if self.engine.status in (EngineStatus.IDLE, EngineStatus.COMPLETED):
            current = self.state.current_player_id
            next_player = (next(pid for pid in self.state.seat_order if self.state.players[pid].identity is Identity.LORD)
                           if current is None else next_alive_player(self.state, current))
            self.engine.start_action(TurnAction(f"turn-{self.state.turn_number + 1}", next_player))
            return True
        request = self.engine.pending_request
        if request is not None and request.player_id != self.human_id:
            self.engine.submit_decision(self.ai.decide(self.state, request))
            return True
        return False

    def pump_until_human_or_end(self, max_steps: int = 10_000) -> int:
        """Headless test helper; rule execution remains inside GameEngine."""
        steps = 0
        while steps < max_steps and self.step_auto():
            steps += 1
        if steps >= max_steps:
            raise RuntimeError("match automation step limit exceeded")
        return steps
