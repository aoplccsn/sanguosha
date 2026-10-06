"""HTTP smoke for the FastAPI-hosted production bundle (not Vite)."""
import json
import sys
from urllib.request import urlopen
base=(sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000').rstrip('/')
def get(path):
    with urlopen(base+path,timeout=20) as response:
        body=response.read()
        assert response.status==200 and body,path
        return body,response.headers.get_content_type()
catalog=json.loads(get('/api/catalog/generals')[0])
assert len(catalog)==108
portraits=[row['portrait'] for row in catalog]
assert len(set(portraits))==108 and all('default' not in path for path in portraits)
manifest=json.loads(get('/assets/manifest.json')[0])
cards=sorted({'/assets/'+path for key,path in manifest.items() if key.startswith(('basic.','trick.','delayed.','equipment.'))})
for path in portraits+cards:
    body,content_type=get(path)
    assert content_type in ('image/png','image/webp') and len(body)>100,(path,content_type)
print(json.dumps({'portraits':f'{len(portraits)}/108','card_art':f'{len(cards)}/{len(cards)}','host':base,'status':'PASS'},ensure_ascii=False))
