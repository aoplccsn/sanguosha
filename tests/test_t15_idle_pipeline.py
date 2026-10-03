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
    script,assets,target=pipeline(tmp_path,{'forest_god_lvbu':{'video':'/assets/portraits/idle/forest_god_lvbu.mp4'}})
    runtime=assets/'portraits/idle'
    runtime.mkdir(parents=True)
    (runtime/'forest_god_lvbu.mp4').write_bytes(b'cleaned-test-fixture')
    (runtime/'source.mp4').write_bytes(b'original')
    subprocess.run([sys.executable,str(script),'--production'],check=True)
    assert (target/'portraits/idle/forest_god_lvbu.mp4').read_bytes()==b'cleaned-test-fixture'
    assert not (target/'portraits/idle/source.mp4').exists()

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
