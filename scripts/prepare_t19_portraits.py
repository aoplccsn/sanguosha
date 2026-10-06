"""Prepare T19 master-derived assets without modifying masters or live manifests."""
import argparse
import json
import subprocess
from pathlib import Path
from prepare_idle_portraits import digest, faststart, probe

ROOT = Path(__file__).resolve().parents[1]
NEW = ('lusu', 'taishici', 'sunce', 'guojia', 'xunyu')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources-dir', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--ffprobe', required=True)
    args = parser.parse_args()
    destination = ROOT / 'docs/t19/prepared_portraits'
    destination.mkdir(parents=True, exist_ok=True)
    report = []
    for name in NEW:
        source = args.sources_dir / f'god_{name}_idle.mp4'
        gid = f'mobile_god_{name}'
        if not source.is_file():
            report.append({'id': gid, 'status': 'missing_master', 'expected_file': source.name})
            continue
        before = digest(source)
        source_info = probe(args.ffprobe, source)
        original = next(s for s in source_info['streams'] if s['codec_type'] == 'video')
        variants = []
        for kind, width, height, crf in (('detail',720,1280,20),('panel',360,640,18)):
            target = destination / f'{gid}.{kind}.mp4'
            if target.exists():
                raise FileExistsError(target)
            subprocess.run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
                '-i', str(source), '-map', '0:v:0', '-vf', f'scale={width}:{height}:flags=lanczos',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', str(crf), '-preset', 'slow',
                '-threads', '2', '-an', '-movflags', '+faststart', str(target)], check=True)
            info = probe(args.ffprobe, target)
            video = info['streams'][0]
            assert len(info['streams']) == 1 and video['codec_name'] == 'h264'
            assert video['pix_fmt'] == 'yuv420p' and faststart(target)
            assert abs(original['width']/original['height'] - width/height) < .01
            assert abs(float(source_info['format']['duration']) - float(info['format']['duration'])) < .15
            variants.append({'kind':kind,'path':target.relative_to(ROOT).as_posix(),
                'sha256':digest(target),'bytes':target.stat().st_size,
                'resolution':[video['width'],video['height']], 'fps':video['avg_frame_rate'],
                'duration':info['format']['duration'],'faststart':True,'audio':False,'crf':crf})
        poster = destination / f'{gid}.png'
        subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n',
            '-i',str(source),'-map','0:v:0','-frames:v','1',str(poster)],check=True)
        from PIL import Image
        with Image.open(poster) as frame:
            frame.thumbnail((640,900),Image.Resampling.LANCZOS)
            frame.save(poster.with_suffix('.webp'),'WEBP',quality=90,method=6)
        assert digest(source) == before
        report.append({'id':gid,'status':'prepared_not_integrated','source_file':source.name,
            'source_sha256':before,'source_unchanged':True,'variants':variants,
            'poster':poster.relative_to(ROOT).as_posix(),'poster_sha256':digest(poster)})
        (ROOT/'docs/t19/portrait_preparation.json').write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(gid+': prepared; source unchanged',flush=True)
    (ROOT/'docs/t19/portrait_preparation.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__ == '__main__': main()
