from pathlib import Path
from PIL import Image, ImageDraw
H=Path(__file__).resolve().parent;E=H/'evidence';R=E/'rendered'
for name in ['classified','selected']:
 files=sorted(R.glob(name+'-*.jpg'))
 for start in range(0,len(files),9):
  page=Image.new('RGB',(1920,1140),'#e3e7ef');draw=ImageDraw.Draw(page)
  for i,p in enumerate(files[start:start+9]):
   im=Image.open(p);im.thumbnail((630,355));x=(i%3)*640;y=(i//3)*380
   draw.text((x+5,y+3),p.stem,fill='black');page.paste(im,(x,y+22))
  page.save(E/f'{name}-review-{start//9+1:02}.jpg')
 print(name,len(files),'rendered pages')
