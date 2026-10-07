"""T19 authoritative ten-general sampling; uses only the room's seeded RNG."""
from sanguosha.engine.rng import RandomSource

OVERPOWERED_SLOT_RATE = 0.05
OVERPOWERED_WEIGHTS = {
    'mobile_god_taishici': 10,
    'mobile_god_sunce': 8,
    'mountain_god_simayi': 7,
    'mobile_god_guojia': 6,
    'mobile_god_xunyu': 4,
}


def draft_general_ids(catalogue, taken, rng: RandomSource, count=10):
    available = list(dict.fromkeys(gid for gid in catalogue if gid not in taken))
    ordinary = [gid for gid in available if gid not in OVERPOWERED_WEIGHTS]
    powered = [gid for gid in available if gid in OVERPOWERED_WEIGHTS]
    hit = rng.choice(range(10000)) < round(OVERPOWERED_SLOT_RATE * 10000)
    selected = None
    if hit and powered:
        ticket = rng.choice(range(sum(OVERPOWERED_WEIGHTS[gid] for gid in powered)))
        for gid in powered:
            ticket -= OVERPOWERED_WEIGHTS[gid]
            if ticket < 0:
                selected = gid
                break
    rng.shuffle(ordinary)
    return tuple(ordinary[:count - (selected is not None)]) + ((selected,) if selected else ())
