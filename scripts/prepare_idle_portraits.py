"""Generate cleaned native-video assets from an explicit source-to-registry mapping.

Usage: python scripts/prepare_idle_portraits.py --sources sources.json
JSON: {"forest_god_lvbu": {"source": "D:/masters/lvbu.mp4",
      "static_master": "D:/masters/lvbu.png", "objectPosition": "center top"}}
ffmpeg/ffprobe must already be installed; optional --ffmpeg/--ffprobe paths.
This tool never modifies source media and never deploys.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = {
    'forest_god_lvbu', 'mountain_god_zhaoyun', 'fire_god_zhouyu',
    'fire_god_zhugeliang', 'forest_god_caocao', 'mountain_god_simayi',
    'wind_god_guanyu', 'wind_god_lvmeng', 'wind_zhang_jiao',
}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def probe(tool, path):
    return json.loads(subprocess.check_output([tool, '-v', 'error', '-show_streams',
        '-show_format', '-of', 'json', str(path)], text=True))

def faststart(path):
    positions = {}
    with path.open('rb') as stream:
        while True:
            offset = stream.tell()
            header = stream.read(8)
            if len(header) < 8:
                break
            size, atom = struct.unpack('>I4s', header)
            header_size = 8
            if size == 1:
                size = struct.unpack('>Q', stream.read(8))[0]
                header_size = 16
            positions.setdefault(atom, offset)
            if size < header_size:
                break
            stream.seek(offset + size)
    return b'moov' in positions and b'mdat' in positions and positions[b'moov'] < positions[b'mdat']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', required=True, type=Path)
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--ffprobe', default=shutil.which('ffprobe'))
    args = parser.parse_args()
    if not args.ffmpeg or not args.ffprobe:
        parser.error('Existing ffmpeg and ffprobe required; no software will be installed.')
    sources = json.loads(args.sources.read_text(encoding='utf-8-sig'))
    if set(sources) - IDS:
        parser.error('Unknown registry IDs: ' + ', '.join(set(sources) - IDS))
    manifest_path = ROOT / 'assets/idle_portraits.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    static_manifest = json.loads((ROOT / 'assets/manifest.json').read_text(encoding='utf-8'))
    reports = []
    # Validate all input files before creating any output.
    for entry in sources.values():
        for field in ('source', 'static_master'):
            if field in entry and not Path(entry[field]).is_file():
                parser.error('Missing input: ' + entry[field])
    for general_id, entry in sources.items():
        source = Path(entry['source']).resolve()
        output = ROOT / 'assets/portraits/idle' / (general_id + '.mp4')
        if source == output.resolve():
            parser.error('Source must be separate from runtime output')
        if output.exists():
            parser.error('Runtime already exists; review it before regenerating: ' + str(output))
        before = digest(source)
        info = probe(args.ffprobe, source)
        video = next(stream for stream in info['streams'] if stream['codec_type'] == 'video')
        copy = video['codec_name'] == 'h264' and video.get('pix_fmt') == 'yuv420p'
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix('.pending.mp4')
        if temporary.exists():
            parser.error('Pending runtime exists: ' + str(temporary))
        encode = ['-c:v', 'copy'] if copy else ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow']
        try:
            subprocess.run([args.ffmpeg, '-nostdin', '-n', '-i', str(source), '-map', '0:v:0',
                *encode, '-an', '-movflags', '+faststart', str(temporary)], check=True)
            cleaned = probe(args.ffprobe, temporary)
            result = next(stream for stream in cleaned['streams'] if stream['codec_type'] == 'video')
            assert not any(stream['codec_type'] == 'audio' for stream in cleaned['streams']), 'Audio remains'
            assert faststart(temporary), 'faststart missing'
            assert result['codec_name'] == 'h264' and result['pix_fmt'] == 'yuv420p', 'Incompatible codec'
            assert abs(float(info['format']['duration']) - float(cleaned['format']['duration'])) < .15, 'Duration changed'
            assert digest(source) == before, 'Source changed'
            temporary.replace(output)
        finally:
            if temporary.exists():
                temporary.unlink()  # Only this invocation's scratch output.
        static_path = ROOT / 'assets' / static_manifest['general.' + general_id]
        if 'static_master' in entry:
            from PIL import Image
            master = Path(entry['static_master']).resolve()
            if master == static_path.resolve() or master == static_path.with_suffix('.webp').resolve():
                parser.error('Static Master must be separate from runtime output')
            with Image.open(master) as original:
                original.save(static_path, 'PNG')
                browser = original.copy()
                browser.thumbnail((640, 900), Image.Resampling.LANCZOS)
                browser.save(static_path.with_suffix('.webp'), 'WEBP', quality=90, method=6)
        url = '/assets/portraits/idle/' + output.name
        manifest[general_id] = {'video': url, 'objectPosition': entry.get('objectPosition', 'center top')}
        reports.append({'id': general_id, 'source': str(source), 'source_sha256': before,
            'static': str(static_path.relative_to(ROOT)), 'runtime': str(output.relative_to(ROOT)),
            'codec': result['codec_name'], 'pixel_format': result['pix_fmt'],
            'resolution': [result['width'], result['height']], 'fps': result['avg_frame_rate'],
            'duration': cleaned['format']['duration'], 'bytes': output.stat().st_size,
            'audio': False, 'faststart': True, 'stream_copy': copy,
            'source_probe': info, 'static_master_updated': 'static_master' in entry})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = ROOT / 'docs/t15/media_report.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(reports)} cleaned portraits; {sum(item["bytes"] for item in reports)} bytes')

if __name__ == '__main__':
    main()
