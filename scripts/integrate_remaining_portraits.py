"""Integrate reviewed T18B ordinary portraits at the T18A production dimensions."""
from pathlib import Path
import hashlib,json,shutil
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
mapping=json.loads((ROOT/'docs/t18b/generated_portraits.json').read_text(encoding='utf-8-sig'))
from sanguosha.content.characters.remaining import REMAINING_DEV_GENERALS
catalogue={c.id:c for c in REMAINING_DEV_GENERALS if '_god_' not in c.id}
assert len(mapping)==len(catalogue)==23
manifest_path=ROOT/'assets/manifest.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
inventory=[];qa=[]
for key,source_path in mapping.items():
 gid=('yj2012_' if 'yj2012_'+key in catalogue else 'yj2013_')+key
 general=catalogue[gid]
 source=Path(source_path); assert source.is_file()
 master=ROOT/'assets/source_art'/general.metadata['pack']/(gid+'.png')
 runtime=ROOT/'assets/generals'/general.kingdom.value/(gid+'.png')
 web=runtime.with_suffix('.webp')
 for p in (master,runtime,web): p.parent.mkdir(parents=True,exist_ok=True)
 if master.exists(): assert hashlib.sha256(master.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
 else: shutil.copyfile(source,master)
 with Image.open(master) as im:
  im.load(); assert im.size==(1024,1536)
  rgb=im.convert('RGB')
  if not runtime.exists(): rgb.resize((768,1152),Image.Resampling.LANCZOS).save(runtime,'PNG',optimize=True)
  if not web.exists(): rgb.resize((600,900),Image.Resampling.LANCZOS).save(web,'WEBP',quality=86,method=6)
 manifest['general.'+gid]=runtime.relative_to(ROOT/'assets').as_posix()
 inventory.append({'id':gid,'name':general.name,'source':master.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(master.read_bytes()).hexdigest(),'runtime':runtime.relative_to(ROOT).as_posix(),'web':web.relative_to(ROOT).as_posix(),'dimensions':{'source':[1024,1536],'runtime':[768,1152],'web':[600,900]}})
 qa.append({'id':gid,'status':'visual_pass','attempts':1,'checks':'full head; character dominant; distinct scene; face and hands coherent; no obvious extra limbs, broken weapon, fused armor, watermark or modern objects; paired generals remain one coherent asset'})
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for filename,data in [('portrait_inventory.json',inventory),('portrait_qa.json',qa)]:
 (ROOT/'docs/t18b'/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
sheet=Image.new('RGB',(1200,1480),'#181b1c');draw=ImageDraw.Draw(sheet)
for i,item in enumerate(inventory):
 x=(i%6)*200; y=(i//6)*370
 with Image.open(ROOT/item['source']) as im: sheet.paste(ImageOps.contain(im,(198,330)),(x,y+28))
 draw.text((x+5,y+3),item['name'],font=font,fill='#eee6d4')
sheet.save(ROOT/'docs/t18b/ordinary_contact_sheet.png')
print('23 ordinary portrait source/runtime/web sets integrated')
