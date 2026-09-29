#!/usr/bin/env python3
"""Local-only contact sheet helper. Requires Pillow; never modifies source captures."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--keys',nargs='+',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
for stage in ('t5','t20'):
 sheet=Image.new('RGB',(960,430*((len(a.keys)+3)//4)),(220,220,220));draw=ImageDraw.Draw(sheet)
 for i,key in enumerate(a.keys):
  path=a.run/key/(stage+'.jpeg');x=i%4*240;y=i//4*430;draw.text((x+2,y+4),key,fill='black')
  if path.exists():
   im=Image.open(path);im.thumbnail((240,400));sheet.paste(im,(x,y+30))
  else:draw.text((x+2,y+35),'NO CAPTURE',fill='red')
 sheet.save(str(a.out)+'-'+stage+'.jpg')
Path(str(a.out)+'.json').write_text(json.dumps(a.keys,indent=2)+'\n')
