from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL,ALL_SKILL_CATALOGUE
registry={s.id:s for s in ALL_SKILL_CATALOGUE}
invalid=[s.id for s in registry.values() if not s.name or len(s.description)<10 or any(t in s.description.lower() for t in ('todo','placeholder','规则摘要','待补','generic'))]
assert not invalid,invalid
rows=[dict(id=g.id,name=g.name,kingdom=g.kingdom.value,max_hp=g.max_hp,initial_hp=g.metadata.get('initial_hp',g.max_hp),version=g.metadata.get('version',''),skills=[dict(id=s.id,name=s.name,type=s.skill_type.value,description=s.description) for sid in g.skill_ids for s in [registry[sid]]]) for g in PLAYABLE_GENERAL_POOL]
report=dict(status='PASS',generals=len(rows),registered_skills=len(registry),placeholder_count=len(invalid),generals_detail=rows)
(ROOT/'docs/t18a10/skill_description_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(report['status'],report['generals'],report['registered_skills'],report['placeholder_count'])
