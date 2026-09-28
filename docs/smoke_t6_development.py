"""Deterministic development full-deck checks; not a T6 acceptance declaration."""
import json
from sanguosha.session import GameSession
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.model.state import GameStatus
from sanguosha.engine.events import CardUsedEvent

def match(seed):
    s=GameSession.new_game(seed,military=True)
    steps=0
    while s.state.status is not GameStatus.FINISHED and steps<20000:
        r=s.engine.pending_request
        if r:
            s.engine.submit_decision(s.ai.decide(s.state,r))
        else:
            s.step_auto()
        s.state.__post_init__()
        steps+=1
    assert s.state.status is GameStatus.FINISHED, (seed,steps)
    assert len(s.state.cards)==160
    assert s.engine.pending_request is None
    assert s.engine.stack.is_empty()
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    definitions=sorted({s.state.cards[e.card_id].definition_id for e in s.events.events if isinstance(e,CardUsedEvent)})
    return {'seed':seed,'steps':steps,'turns':s.state.turn_number,'winner':s.state.victory.label,'used':definitions}

if __name__=='__main__':
    for seed in range(1,6):
        first=match(seed)
        assert first==match(seed)
        print(json.dumps(first,ensure_ascii=False),flush=True)
