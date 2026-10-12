#!/usr/bin/env python3
"""Read-only JPEG pixel audit via the local macOS decoder; source bytes unchanged."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2])))
OLD=WS/'westlake-harness/benchmark/2026-10-12-recovery-executor'
R3=WS/'westlake-harness/benchmark/2026-10-12-v1-seal-execution/r3-interaction'

def predicate(name,c):
 r,g,b=c
 return {'white':r>240 and g>240 and b>240,'light':r>210 and g>210 and b>210,
         'red':r>230 and 25<g<130 and 20<b<130,'blue':85<r<160 and 140<g<210 and b>225 and b-r>65,
         'dark':r<100 and g<100 and b<100}[name]

def read_pixels(path):
 with tempfile.TemporaryDirectory(prefix='feed-pixel-audit-') as t:
  out=Path(t)/'decoded.bmp'
  subprocess.run(['/usr/bin/sips','-s','format','bmp',str(path),'--out',str(out)],check=True,capture_output=True)
  b=out.read_bytes()
 offset=struct.unpack_from('<I',b,10)[0];w,h,planes,bits,compression=struct.unpack_from('<iiHHI',b,18)
 assert bits==24 and compression==0 and planes==1
 stride=((w*3+3)//4)*4
 def pixel(x,y):
  pos=offset+(y if h<0 else abs(h)-1-y)*stride+x*3
  return tuple(reversed(b[pos:pos+3]))
 return w,abs(h),pixel

REGIONS={'header_left':('red',5,55,20,60,2),'header_right':('red',1160,1190,110,150,2),
 'search_top':('white',350,950,70,80,3),'recommend_underline':('red',45,85,245,251,1),
 'home_icon':('red',95,170,1830,1875,2),'nav_background':('white',950,1040,1830,1880,3),
 'content':('dark',35,750,275,660,3)}
POINTS=[('white',1100,280),('white',100,1800),('white',1050,1850),('red',120,1840),('red',150,1840),('red',20,30),('red',600,30),('red',1190,140),('white',500,75),('white',900,145),('red',55,248)]

def audit(path,expected):
 w,h,pixel=read_pixels(path);result={'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'expected':expected,'width':w,'height':h,'points':{},'regions':{}}
 if (w,h)!=(1200,1920):return result
 for name,x,y in POINTS:
  c=pixel(x,y);result['points'][f'{name}({x},{y})']={'rgb':c,'passes':predicate(name,c)}
 for key,(name,x0,x1,y0,y1,step) in REGIONS.items():
  samples=[predicate(name,pixel(x,y)) for y in range(y0,y1,step) for x in range(x0,x1,step)]
  result['regions'][key]={'match':sum(samples),'total':len(samples),'fraction':sum(samples)/len(samples)}
 return result

def main():
 old=json.loads((OLD/'evidence/feed-real-samples.json').read_text())
 samples=[(Path(x['source'].replace('$WORKSPACES',str(WS))),x['expected']) for x in old]
 samples += [(R3/p,e) for p,e in [('before.jpeg','feed'),('return/returned.jpeg','feed'),('refresh/refresh.jpeg','feed'),('article/article.jpeg','unknown')]]
 report={'decoder':'macOS sips BMP (analysis only; candidate/source decoder remains stb_image)','samples':[audit(p,e) for p,e in samples]}
 (HERE/'evidence/pixel-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 for r in report['samples']:
  print(Path(r['source']).name,'fails',[k for k,v in r['points'].items() if not v['passes']], 'regions', {k:round(v['fraction'],3) for k,v in r['regions'].items()})
if __name__=='__main__':main()
