from pathlib import Path
import sys,json
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL,ALL_SKILL_CATALOGUE
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.session import GameSession
source=root/'src/sanguosha';mirror=root/'cloudflare/game-room/src/sanguosha'
a={p.relative_to(source).as_posix():p.read_text(encoding='utf-8') for p in source.rglob('*.py') if not any(x in ('ui','relay','web','__pycache__') for x in p.relative_to(source).parts)}
b={p.relative_to(mirror).as_posix():p.read_text(encoding='utf-8') for p in mirror.rglob('*.py') if '__pycache__' not in p.parts}
assert a==b
coverage={mode:set() for mode in ('military-five','military-eight')}
for mode in coverage:
 for seed in range(200):
  room=MultiplayerRoom(seed=seed,mode_id=mode);pid,_=room.join('reachability',lambda _:None);room.start(pid);coverage[mode].update(room.draft_requests[pid].choices)
 assert {c.id for c in PLAYABLE_GENERAL_POOL}==coverage[mode]
s=GameSession.new_game(military=True)
cards=[{'id':d.id,'name':d.name,'category':d.category.value,'attack_range':d.attack_range,'equipment_slot':d.equipment_slot.value if d.equipment_slot else None,'metadata':dict(d.metadata),'status':'BLOCKED','evidence':'registered and golden tests; independent per-card source and interaction closure incomplete'} for d in s.definitions._definitions.values()]
assert len(cards)==43 and len(s.state.cards)==160
(root/'docs/t18a11/card_audit.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2),encoding='utf-8')
report={'status':'PASS','worker_python_files':len(a),'generals':len(PLAYABLE_GENERAL_POOL),'skills':len({s.id for s in ALL_SKILL_CATALOGUE}),'card_definitions':len(cards),'physical_cards':len(s.state.cards),'draft_offers_200_seeds_per_mode':{mode:len(v) for mode,v in coverage.items()},'deployment':'NOT_PERFORMED'}
(root/'docs/t18a11/registry_consistency.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report)
