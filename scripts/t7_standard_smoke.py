"""Write reproducible full-match T7 smoke evidence for seeds 1–20."""

import json
from pathlib import Path

from sanguosha.content.characters.standard import STANDARD_SKILL_CATALOGUE
from sanguosha.engine.events import (CardMovedEvent, CardRespondedEvent, CardUsedEvent,
                                      DamageDealtEvent, HpRecoveredEvent, VirtualResponseEvent)
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession


OUTPUT = Path(__file__).resolve().parents[1] / 'docs' / 'T7_STANDARD_SMOKE.json'
EFFECT_EVENTS = (CardMovedEvent, CardRespondedEvent, CardUsedEvent,
                 DamageDealtEvent, HpRecoveredEvent, VirtualResponseEvent)
SKILL_IDS = {skill.id for skill in STANDARD_SKILL_CATALOGUE}


def run_match(seed: int) -> dict:
    setup = Pregame.create(seed)
    setup.acknowledge_identity()
    setup.timeout()
    session = GameSession.new_game(military=True, setup=setup)
    for _ in range(12_000):
        if session.state.status is GameStatus.FINISHED:
            break
        request = session.engine.pending_request
        if request is not None and request.player_id == session.human_id:
            session.submit_human(session.ai.decide(session.state, request))
        elif not session.step_auto():
            break
    state = session.state
    state.__post_init__()
    assert state.status is GameStatus.FINISHED, seed
    assert session.engine.pending_request is None and session.engine.stack.is_empty(), seed
    assert not state.cards_in(ZoneRef(ZoneType.PROCESSING)), seed
    activations = []
    seen_activations = set()
    for event in session.events.events:
        if not isinstance(event, EFFECT_EVENTS):
            continue
        for skill in sorted(skill for skill in SKILL_IDS if f':{skill}' in event.event_id):
            key = event.event_id.split(f':{skill}', 1)[0] + ':' + skill
            if key not in seen_activations:
                activations.append({'skill': skill, 'action_id': key,
                                    'first_effect_event_id': event.event_id})
                seen_activations.add(key)
    return {
        'seed': seed,
        'identity_assignment': {str(pid): identity.value for pid, identity in setup.identities.items()},
        'general_assignment': {str(pid): str(general) for pid, general in setup.generals.items()},
        'skill_activations': activations,
        'winner': {'label': state.victory.label, 'winner_ids': list(state.victory.winner_ids),
                   'reason': state.victory.reason},
        'turn_count': state.turn_number,
    }


if __name__ == '__main__':
    matches = [run_match(seed) for seed in range(1, 21)]
    OUTPUT.write_text(json.dumps({'branch': 't7-standard-generals', 'matches': matches},
                                 ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(matches)} full matches written to {OUTPUT}')
