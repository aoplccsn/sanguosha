"""Prevent source media leakage and validate isolated production asset registration."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def pipeline(tmp_path, manifest):
    scripts=tmp_path/'scripts'
    scripts.mkdir()
    shutil.copy2(ROOT/'scripts/sync_web_assets.py',scripts/'sync_web_assets.py')
    assets=tmp_path/'assets'
    assets.mkdir()
    (assets/'manifest.json').write_text('{}',encoding='utf-8')
    (assets/'idle_portraits.json').write_text(json.dumps(manifest),encoding='utf-8')
    return scripts/'sync_web_assets.py',assets,tmp_path/'web/public/assets'

def test_source_masters_never_enter_development_or_production(tmp_path):
    script,assets,target=pipeline(tmp_path,{})
    (assets/'master.mp4').write_bytes(b'SOURCE MASTER MUST STAY PRIVATE')
    source_art=assets/'source_art'
    source_art.mkdir()
    (source_art/'master.mp4').write_bytes(b'SOURCE')
    for mode in [[],['--production']]:
        subprocess.run([sys.executable,str(script),*mode],check=True)
        assert not list(target.rglob('*.mp4'))
        assert (assets/'master.mp4').read_bytes()==b'SOURCE MASTER MUST STAY PRIVATE'

def test_registered_runtime_only_is_copied(tmp_path):
    script,assets,target=pipeline(tmp_path,{'forest_god_lvbu':{'video':'/assets/portraits/idle/forest_god_lvbu.mp4','panelVideo':'/assets/portraits/idle/forest_god_lvbu.panel.mp4'}})
    runtime=assets/'portraits/idle'
    runtime.mkdir(parents=True)
    (runtime/'forest_god_lvbu.mp4').write_bytes(b'cleaned-test-fixture')
    (runtime/'source.mp4').write_bytes(b'original')
    (runtime/'forest_god_lvbu.panel.mp4').write_bytes(b'panel-fixture')
    subprocess.run([sys.executable,str(script),'--production'],check=True)
    assert (target/'portraits/idle/forest_god_lvbu.mp4').read_bytes()==b'cleaned-test-fixture'
    assert not (target/'portraits/idle/source.mp4').exists()
    assert (target/'portraits/idle/forest_god_lvbu.panel.mp4').read_bytes()==b'panel-fixture'

def test_missing_runtime_fails_build_registration(tmp_path):
    script,_,_=pipeline(tmp_path,{'forest_god_lvbu':{'video':'/assets/portraits/idle/missing.mp4'}})
    result=subprocess.run([sys.executable,str(script),'--production'],capture_output=True,text=True)
    assert result.returncode!=0
    assert 'Missing or unsafe' in result.stderr

def test_outside_runtime_directory_is_rejected(tmp_path):
    script,_,_=pipeline(tmp_path,{'forest_god_lvbu':{'video':'/assets/portraits/idle/../../../secret.mp4'}})
    result=subprocess.run([sys.executable,str(script),'--production'],capture_output=True,text=True)
    assert result.returncode!=0
    assert 'Missing or unsafe' in result.stderr


def test_all_final_portraits_have_verified_audio_free_runtime_and_matched_static():
    import hashlib
    from PIL import Image
    reports=json.loads((ROOT/'docs/t15/media_report.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'assets/idle_portraits.json').read_text(encoding='utf-8'))
    expected={'forest_god_lvbu','mountain_god_zhaoyun','fire_god_zhouyu','fire_god_zhugeliang','forest_god_caocao','mountain_god_simayi','wind_god_guanyu','wind_god_lvmeng','wind_zhang_jiao','shadow_god_liubei','shadow_god_luxun','thunder_god_ganning','thunder_god_zhangliao'}
    assert set(manifest)==expected
    assert {r['id'] for r in reports}==expected
    for report in reports:
        runtime=ROOT/report['runtime']
        assert hashlib.sha256(runtime.read_bytes()).hexdigest()==report['runtime_sha256']
        assert runtime.stat().st_size==report['bytes']
        assert manifest[report['id']]['video']=='/'+report['runtime']
        assert report['faststart'] and not report['audio']
        assert report.get('web_optimized') or report['video_payload_identical']
        streams=report['runtime_probe']['streams']
        assert len(streams)==1 and streams[0]['codec_type']=='video'
        assert streams[0]['codec_name']=='h264' and streams[0]['pix_fmt']=='yuv420p'
        assert streams[0]['width']==720 and streams[0]['height']==1280
        with Image.open(ROOT/report['static']) as image:
            assert image.size==(720,1280)
            assert hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==report['static_pixel_sha256']


def test_current_panel_integrity():
    import hashlib
    reports=json.loads((ROOT/'docs/t18b/panel_media_report.json').read_text())
    manifest=json.loads((ROOT/'assets/idle_portraits.json').read_text())
    sys.path.insert(0,str(ROOT/'scripts'))
    from prepare_idle_portraits import faststart
    assert len(reports)==len(manifest)==13
    for report in reports:
        path=ROOT/report['path']
        assert manifest[report['id']]['panelVideo']=='/'+report['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==report['panel_sha256']
        assert path.stat().st_size==report['bytes']
        assert hashlib.sha256((ROOT/'assets/portraits/idle'/(report['id']+'.mp4')).read_bytes()).hexdigest()==report['detail_sha256']
        assert faststart(path) and report['resolution']==[360,640]
        assert report['codec']=='h264' and report['pixel_format']=='yuv420p' and not report['audio']
