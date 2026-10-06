"""Shared chain state changes, including locked chain immunity."""
def set_chained(state,pid,value,skills):
    player=state.players[pid]
    if not value and player.is_alive and skills is not None and skills.has(state,pid,'jieying_liubei'):
        player.chained=True
        return False
    changed=player.chained!=value
    player.chained=value
    return changed


def jieying_hand_bonus(state,pid,skills):
    return 2 if state.players[pid].chained and any(state.players[q].is_alive and skills.has(state,q,'jieying_liubei') for q in state.seat_order) else 0
