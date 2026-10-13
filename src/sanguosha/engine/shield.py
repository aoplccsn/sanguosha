"""Shield changes HP payment, preserving the damage event and amount."""
from .events import Event

def apply_damage_to_hp(state, target_id, amount, recorder, action_id):
    target = state.players[target_id]
    absorbed = min(max(0, target.marks.get('shield', 0)), amount)
    if absorbed:
        remaining = target.marks['shield'] - absorbed
        if remaining: target.marks['shield'] = remaining
        else: target.marks.pop('shield', None)
        recorder.record(Event(action_id + ':shield', 'shield_lost', target_id,
            metadata={'amount': absorbed, 'remaining': remaining, 'damage_amount': amount}))
    target.hp -= amount - absorbed
    return amount - absorbed
