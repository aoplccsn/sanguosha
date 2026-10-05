"""Create Web detail/panel variants without changing final source masters.
Panel 360x640 follows the T18A.3 production panel pipeline.
Detail keeps source 720x1280: mobile detail can reach 637px wide before DPR.
"""
from pathlib import Path
import argparse, json, subprocess, hashlib, shutil

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def probe(tool,path):return json.loads(subprocess.check_output([tool,'-v','error','-show_streams','-show_format','-of','json',str(path)],text=True))
def faststart(path):
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from prepare_idle_portraits import faststart as verify
    return verify(path)
def main():
    p=argparse.ArgumentParser();p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True);p.add_argument('--backup',type=Path,required=True)
    p.add_argument('--only', nargs='+', help='Optimize only these registry IDs, preserving existing media and reports')
    args=p.parse_args();args.backup.mkdir(parents=True,exist_ok=True)
    reports=json.loads((ROOT/'docs/t15/media_report.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'assets/idle_portraits.json').read_text(encoding='utf-8'))
    selected=set(args.only) if args.only else {item["id"] for item in reports}
    unknown=selected-set(manifest)
    if unknown: p.error("Unknown registry IDs: " + ", ".join(sorted(unknown)))
    report_path=ROOT/"docs/t15_1/media_report.json"
    previous=json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else []
    output=[item for item in previous if item["id"] not in selected]
    for old in reports:
        if old['id'] not in selected: continue
        source=Path(old['source']);before=sha(source);assert before==old['source_sha256']
        full=ROOT/old['runtime'];backup=args.backup/full.name
        if not backup.exists():shutil.copy2(full,backup)
        entries=[]
        for kind,size,crf in [('detail',(720,1280),20),('panel',(360,640),18)]:
            destination=full if kind=='detail' else full.with_name(full.stem+'.panel.mp4')
            pending=destination.with_suffix('.optimized.pending.mp4')
            assert not pending.exists()
            subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-i',str(source),'-map','0:v:0','-vf',f'scale={size[0]}:{size[1]}:flags=lanczos','-c:v','libx264','-pix_fmt','yuv420p','-crf',str(crf),'-preset','slow','-threads','2','-an','-movflags','+faststart',str(pending)],check=True)
            info=probe(args.ffprobe,pending);v=info['streams'][0]
            assert len(info['streams'])==1 and v['codec_name']=='h264' and v['pix_fmt']=='yuv420p'
            assert v['avg_frame_rate']=='24/1' and abs(float(info['format']['duration'])-10)<.01 and faststart(pending)
            # At native variant pixels, compare every frame with the reference scaled identically.
            comparison=subprocess.run([args.ffmpeg,'-hide_banner','-i',str(source),'-i',str(pending),'-filter_complex',f'[0:v]scale={size[0]}:{size[1]}:flags=lanczos,format=yuv420p[ref];[ref][1:v]ssim','-an','-f','null','-'],capture_output=True,text=True,check=True)
            line=next(line for line in reversed(comparison.stderr.splitlines()) if 'SSIM Y:' in line)
            # Frame captures are visual evidence only, never production assets.
            frames=ROOT/'docs/t15_1/quality';frames.mkdir(parents=True,exist_ok=True)
            for label,input_path in [('reference',source),('optimized',pending)]:
                image=frames/(full.stem+'.'+kind+'.'+label+'.png')
                subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y','-i',str(input_path),'-vf',f'scale={size[0]}:{size[1]}:flags=lanczos','-frames:v','1',str(image)],check=True)
            pending.replace(destination)
            info['format']['filename']=str(destination)
            entries.append({'kind':kind,'path':destination.relative_to(ROOT).as_posix(),'bytes':destination.stat().st_size,'sha256':sha(destination),'probe':info,'faststart':True,'audio_stream_count':0,'crf':crf,'ssim':line})
        assert sha(source)==before
        manifest[old['id']]['panelVideo']='/'+entries[1]['path']
        output.append({'id':old['id'],'source_sha256':before,'before':{'bytes':backup.stat().st_size,'probe':probe(args.ffprobe,backup)},'variants':entries})
        if 'encoded_video_sha256' in old:
            old['t15_stream_copy_encoded_video_sha256']=old.pop('encoded_video_sha256')
        # Refresh current T15 integrity report while preserving before evidence in T15.1.
        old.update(bytes=entries[0]['bytes'],runtime_sha256=entries[0]['sha256'],runtime_probe=entries[0]['probe'],stream_copy=False,video_payload_identical=False,web_optimized=True,bitrate=entries[0]['probe']['streams'][0]['bit_rate'])
    (ROOT/'assets/idle_portraits.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (ROOT/'docs/t15/media_report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'docs/t15_1/media_report.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
