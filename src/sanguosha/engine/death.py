"""Death cleanup, identity rewards, and victory handoff."""

from dataclasses import dataclass

from sanguosha.model.enums import Identity, PlayerStatus
from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState, GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .deck import DrawCardsAction
from .events import EventRecorder, GameEndedEvent, KillRewardEvent, LordPenaltyEvent, PlayerDiedEvent
from .identity import IdentitySystem
from .resolution import ResolutionFrame


@dataclass(frozen=True, slots=True)
class DeathAction(Action):
    target_id: PlayerId
    killer_id: PlayerId | None


class DeathActionHandler:
    def __init__(self, moves: CardMoveService, identity: IdentitySystem, recorder: EventRecorder,
                 skills=None) -> None:
        self.moves = moves
        self.identity = identity
        self.recorder = recorder
        self.skills = skills

    def _discard_all(self, state: GameState, player_id: PlayerId, action_id: str,
                     personal=(ZoneType.HAND, ZoneType.EQUIPMENT, ZoneType.JUDGMENT, ZoneType.SPECIAL)) -> None:
        refs = sorted(
            (ref for ref in state.zones if ref.player_id == player_id and ref.zone_type in personal),
            key=lambda ref: (ref.zone_type.value, ref.equipment_slot.value if ref.equipment_slot else ""),
        )
        for index, ref in enumerate(refs):
            ids = state.cards_in(ref)
            if ids:
                self.moves.move(state, CardMove(
                    f"{action_id}:cleanup:{index}", ids, ref, ZoneRef(ZoneType.DISCARD_PILE),
                    CardMoveReason.SYSTEM, player_id, action_id,
                ))

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, DeathAction)
        victim = state.players[action.target_id]
        if frame.step_index == 0:
            victim.status = PlayerStatus.DEAD
            if action.target_id == state.current_player_id:
                from .yj2011_tier3 import clear_zhichi
                clear_zhichi(state)
            from .skill_leases import on_death
            on_death(state,action.target_id)
            from .card_limits import clear_source
            clear_source(state, action.target_id)
            from .fuhun import clear_grants
            clear_grants(state,action.target_id)
            from .skill_grants import remove_grant
            for skill in tuple(victim.granted_skills):
                remove_grant(state,action.target_id,skill,'jilue.permanent')
            for key in ('ren','renjie_round_count','jilue_learning_uses','lianpo_pending','lianpo_selected_turn'):
                victim.marks.pop(key,None)
            state.metadata.get('mobile_jilue_initialized',{}).pop(action.target_id,None)
            state.metadata.get('powei_range',{}).pop(action.target_id,None)
            for other in state.players.values():
                other.marks.pop('wei:' + action.target_id,None)
            state.revealed_identities.add(action.target_id)
            if (self.skills is not None and self.skills.has(state, action.target_id, 'duanchang')
                    and action.killer_id is not None and action.killer_id != action.target_id
                    and state.players[action.killer_id].is_alive):
                self.skills.suppress_character_skills(state, action.killer_id)
            frame.step_index = 3
            if (self.skills is not None and any(
                    pid != action.target_id and state.players[pid].is_alive
                    and self.skills.has(state, pid, 'xingshang') for pid in state.seat_order)):
                from .forest import XingshangAction
                return StepResult.push(XingshangAction(action.action_id + ':xingshang',
                                                       action.target_id))
            return StepResult.continue_()
        if frame.step_index == 3:
            if (self.skills is not None and self.skills.has(state, action.target_id, 'huilei')
                    and action.killer_id is not None and action.killer_id != action.target_id
                    and state.players[action.killer_id].is_alive):
                # Locked Q08: killer's hand/equipment are discarded before rewards.
                for ref in tuple(state.zones):
                    if ref.player_id == action.killer_id and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT):
                        ids = state.cards_in(ref)
                        if ids:
                            self.moves.move(state, CardMove(action.action_id + ':huilei:' + str(ref), ids,
                                ref, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
                                action.killer_id, action.action_id))
            self._discard_all(state, action.target_id, action.action_id)
            self.recorder.record(PlayerDiedEvent(
                f"{action.action_id}:died", action.target_id, victim.identity, action.killer_id,
            ))
            killer = state.players.get(action.killer_id) if action.killer_id is not None else None
            if victim.identity is Identity.REBEL and killer is not None and killer.is_alive:
                frame.step_index = 1
                return StepResult.push(DrawCardsAction(f"{action.action_id}:reward", action.killer_id, 3))
            if victim.identity is Identity.LOYALIST and killer is not None and killer.identity is Identity.LORD:
                self._discard_all(state, killer.player_id, f"{action.action_id}:lord-penalty",
                                  (ZoneType.HAND, ZoneType.EQUIPMENT))
                self.recorder.record(LordPenaltyEvent(f"{action.action_id}:penalty", killer.player_id, action.target_id))
            frame.step_index = 2
            return StepResult.continue_()
        if frame.step_index == 1:
            assert action.killer_id is not None
            self.recorder.record(KillRewardEvent(
                f"{action.action_id}:reward-event", action.killer_id, action.target_id,
                int(frame.child_result or 0),
            ))
            frame.step_index = 2
            return StepResult.continue_()
        if (frame.step_index == 2 and not frame.local.get('yj2012_zhuiyi')
                and self.skills is not None and self.skills.has(state, action.target_id, 'zhuiyi')):
            from .yj2012 import YJ2012Action
            frame.local['yj2012_zhuiyi'] = True
            return StepResult.push(YJ2012Action(action.action_id + ':zhuiyi', action.target_id, 'zhuiyi', action.killer_id))
        if (frame.step_index == 2 and not frame.local.get('wuhun_resolved')
                and self.skills is not None and self.skills.has(state, action.target_id, 'wuhun')):
            from .gods import WuhunDeathAction
            frame.local['wuhun_resolved'] = True
            return StepResult.push(WuhunDeathAction(action.action_id + ':wuhun', action.target_id))
        if (frame.step_index == 2 and not frame.local.get('mobile_lianpo')
                and self.identity.evaluate(state) is None and action.killer_id is not None
                and state.players[action.killer_id].is_alive and self.skills is not None
                and self.skills.has(state, action.killer_id, 'lianpo')):
            from .mobile_gods import MobileGodAction
            frame.local['mobile_lianpo'] = True
            return StepResult.push(MobileGodAction(action.action_id + ':lianpo', action.killer_id, 'lianpo'))
        # Keep transformed death skills available until their own resolution ends.
        victim.transformation_pool.clear()
        victim.active_transformation = None
        victim.transformation_skill = None
        victory = self.identity.evaluate(state)
        if victory is not None:
            state.victory = victory
            state.status = GameStatus.FINISHED
            self.recorder.record(GameEndedEvent(
                f"{action.action_id}:game-ended", victory.label, victory.winner_ids,
            ))
        return StepResult.complete("death-resolved")
