from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets'
TARGET = ROOT / 'web' / 'public' / 'assets'

PRODUCTION = '--production' in sys.argv

if not PRODUCTION:
    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns('source_art', '*.py', '*.qss'))
else:
    from PIL import Image

    # Two device pixels per CSS pixel at the largest regular display sizes.
    maximum = {'generals': (640, 900), 'cards': (320, 440),
               'backgrounds': (1920, 1080)}
    suitable_webp: set[Path] = set()
    undersized_webp: set[Path] = set()
    for png in SOURCE.rglob('*.png'):
        relative = png.relative_to(SOURCE)
        if relative.parts[0] not in maximum:
            continue
        webp = png.with_suffix('.webp')
        if not webp.exists():
            continue
        with Image.open(png) as original, Image.open(webp) as variant:
            needed = (min(original.width, maximum[relative.parts[0]][0]),
                      min(original.height, maximum[relative.parts[0]][1]))
            (suitable_webp if variant.width >= needed[0] and variant.height >= needed[1]
             else undersized_webp).add(webp)
    expected: set[Path] = set()
    for source in SOURCE.rglob('*'):
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE)
        if ('source_art' in relative.parts or relative.parts[0] == 'gods'
                or source.suffix.lower() in {'.py', '.qss', '.gitkeep'}):
            continue
        group = relative.parts[0]
        if source in undersized_webp:
            continue
        if source.suffix.lower() == '.png' and group in maximum:
            if source.with_suffix('.webp') in suitable_webp:
                continue  # Reuse the existing browser variant below.
            destination = TARGET / relative.with_suffix('.webp')
            expected.add(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or destination.stat().st_mtime_ns < source.stat().st_mtime_ns:
                with Image.open(source) as original:
                    image = original.copy()
                    image.thumbnail(maximum[group], Image.Resampling.LANCZOS)
                    image.save(destination, 'WEBP', quality=82, method=6)
            continue
        destination = TARGET / relative
        expected.add(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if relative.name == 'manifest.json':
            manifest = json.loads(source.read_text(encoding='utf-8'))
            for key, value in manifest.items():
                path = Path(value)
                if path.parts[0] in maximum and path.suffix == '.png':
                    manifest[key] = str(path.with_suffix('.webp')).replace('\\', '/')
            destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        elif not destination.exists() or destination.stat().st_mtime_ns < source.stat().st_mtime_ns:
            shutil.copy2(source, destination)
    for stale in TARGET.rglob('*'):
        if stale.is_file() and stale not in expected:
            stale.unlink()

print(f"Web {'production' if PRODUCTION else 'development'} assets synchronized: {TARGET}")
