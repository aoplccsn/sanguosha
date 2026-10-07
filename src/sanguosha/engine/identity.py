"""Five-player classic identity victory checks."""

from sanguosha.model.enums import Identity
from sanguosha.model.state import GameState
from sanguosha.model.victory import VictoryResult


class IdentitySystem:
    def evaluate(self, state: GameState) -> VictoryResult | None:
        from sanguosha.game_modes import game_mode
        mode = game_mode(state.metadata.get('mode_id', 'military-five'))
        if mode.public_sides:
            surviving = {mode.team_for(pid) for pid in state.seat_order if state.players[pid].is_alive}
            if len(surviving) > 1:
                return None
            if not surviving:
                return VictoryResult('平局', (), '双方全部阵亡')
            team = next(iter(surviving))
            winners = tuple(pid for pid in state.seat_order if mode.team_for(pid) == team)
            label = f'玩家{team}胜利' if mode.seat_count == 2 else f'{team}队胜利'
            return VictoryResult(label, winners, '对方全部阵亡')
        lords = [p for p in state.players.values() if p.identity is Identity.LORD]
        if len(lords) != 1:
            return None
        lord = lords[0]
        living = [state.players[pid] for pid in state.seat_order if state.players[pid].is_alive]
        if not lord.is_alive:
            if len(living) == 1 and living[0].identity is Identity.RENEGADE:
                winner = (living[0].player_id,)
                return VictoryResult("内奸胜利", winner, "主公死亡且内奸独存")
            winners = tuple(pid for pid in state.seat_order if state.players[pid].identity is Identity.REBEL)
            return VictoryResult("反贼胜利", winners, "主公死亡")
        if not any(p.identity in (Identity.REBEL, Identity.RENEGADE) for p in living):
            winners = tuple(pid for pid in state.seat_order if state.players[pid].identity in (Identity.LORD, Identity.LOYALIST))
            return VictoryResult("主公与忠臣胜利", winners, "反贼与内奸全部死亡")
        return None
