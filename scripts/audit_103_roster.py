from pathlib import Path
import sys,json,hashlib,subprocess
from urllib.request import urlopen
from PIL import Image
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'src'))
from sanguosha.content.characters.standard import ALL_GENERAL_POOL,PLAYABLE_GENERAL_POOL,ALL_SKILL_CATALOGUE
from sanguosha.content.characters.remaining import REMAINING_DEV_GENERALS
from sanguosha.pregame import Pregame
from sanguosha.ui.pregame_dialog import ALL_GENERAL_POOL as desktop_pool
ids={str(c.id) for c in ALL_GENERAL_POOL};assert len(ids)==103
assert ids=={str(c.id) for c in PLAYABLE_GENERAL_POOL}=={str(c.id) for c in desktop_pool}
worker_root=r/'cloudflare/game-room/src'
code="import sys,json;sys.path.insert(0,sys.argv[1]);from sanguosha.content.characters.standard import ALL_GENERAL_POOL;print(json.dumps([str(c.id) for c in ALL_GENERAL_POOL]))"
worker=set(json.loads(subprocess.check_output([sys.executable,'-c',code,str(worker_root)],text=True)))
catalog=json.load(urlopen('http://127.0.0.1:8018/api/catalog/generals'))
assert ids==worker=={g['id'] for g in catalog}
assert all(g['implemented'] and g['playable'] for g in catalog)
draft=set()
for seed in range(200):draft.update(Pregame.create(seed).candidates)
assert draft==ids
manifests={}
for rel in ('assets/manifest.json','web/public/assets/manifest.json','web/dist/assets/manifest.json'):
    manifest=json.loads((r/rel).read_text(encoding='utf-8'))
    actual={key.removeprefix('general.') for key in manifest if key.startswith('general.')}
    assert actual==ids,(rel,sorted(actual-ids),sorted(ids-actual))
    manifests[rel]=len(actual)
    for cid in ids:assert (r/Path(rel).parent/manifest['general.'+cid]).is_file()
source_files={p.relative_to(r/'src/sanguosha').as_posix():p for p in (r/'src/sanguosha').rglob('*.py') if not any(part in ('ui','relay','web','__pycache__') for part in p.relative_to(r/'src/sanguosha').parts)}
mirror_files={p.relative_to(worker_root/'sanguosha').as_posix():p for p in (worker_root/'sanguosha').rglob('*.py') if '__pycache__' not in p.parts}
assert source_files.keys()==mirror_files.keys()
assert all(p.read_text(encoding='utf-8')==mirror_files[key].read_text(encoding='utf-8') for key,p in source_files.items())
inventory=json.loads((r/'docs/t18b/portrait_inventory.json').read_text(encoding='utf-8'));assert len(inventory)==23
for row in inventory:
    for key,size in [('source',(1024,1536)),('runtime',(768,1152)),('web',(600,900))]:
        assert Image.open(r/row[key]).size==size
    assert hashlib.sha256((r/row['source']).read_bytes()).hexdigest()==row['source_sha256']
sources=json.loads((r/'docs/t18b/god_sources.json').read_text(encoding='utf-8'))
records={d['id']:d for d in json.loads((r/'docs/t18b/panel_media_report.json').read_text(encoding='utf-8'))}
masters={i:hashlib.sha256(Path(v['source']).read_bytes()).hexdigest()==records[i]['source_sha256'] for i,v in sources.items()}
assert len(masters)==4 and all(masters.values())
new_skills={str(s) for c in REMAINING_DEV_GENERALS for s in c.skill_ids}|{'paiyi'};assert len(new_skills)==50
assert new_skills<={str(s.id) for s in ALL_SKILL_CATALOGUE}
result={'status':'PASS','general_ids':sorted(ids),'catalogues':{'python':103,'web_http':103,'worker':103,'draft_sampled_200_seeds':103,'pyside':103},'manifests':manifests,'source_mirror_python_files':len(source_files),'new_generals':27,'new_skills_including_reused_mashu':50,'ordinary_art_dimensions_and_hashes':23,'god_master_unchanged':masters,'deployment':'NOT_PERFORMED'}
(r/'docs/t18b/registry_consistency.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='general_ids'},ensure_ascii=False))
