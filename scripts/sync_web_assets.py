from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets'
TARGET = ROOT / 'web' / 'public' / 'assets'

if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns('source_art', '*.py', '*.qss'))
print(f'Web assets synchronized: {TARGET}')
