import json
from pathlib import Path
from fastapi.testclient import TestClient
from sanguosha.web.app import create_app
from sanguosha.content.characters.remaining import REMAINING_DEV_GENERALS

def test_all_27_new_portraits_and_eight_video_variants_are_served_locally():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'web/dist/assets/manifest.json').read_text(encoding='utf-8'))
    idle=json.loads((root/'assets/idle_portraits.json').read_text(encoding='utf-8'))
    client=TestClient(create_app())
    for g in REMAINING_DEV_GENERALS:
        path='/assets/'+manifest['general.'+g.id]
        response=client.get(path)
        assert response.status_code==200 and response.headers['content-type'].startswith('image/'),path
        assert len(response.content)>100
        if g.metadata['portrait_mode']=='dynamic':
            for field in ('video','panelVideo'):
                video=client.get(idle[g.id][field],headers={'Range':'bytes=0-255'})
                assert video.status_code==206 and video.headers['content-type'].startswith('video/'),(g.id,field)
                assert video.headers['content-range'].startswith('bytes 0-255/')
