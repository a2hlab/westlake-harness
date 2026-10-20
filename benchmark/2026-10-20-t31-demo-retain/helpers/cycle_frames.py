#!/usr/bin/env python3
"""Capture only; root performs a visually selected action before this call."""
import argparse,json,subprocess,sys,time
from window_paths import WINDOW,HELPERS,context,budget,tag

def offsets(phase):return {'play':[0,5,10,20],'pause':[0,3],'resume':[0,5,10]}[phase]
def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['play','pause','resume']);p.add_argument('tag');p.add_argument('boot');a=p.parse_args()
 tag(a.tag);c=context();start=time.monotonic();deadline=start+budget(c);out=WINDOW/a.tag;out.mkdir(exist_ok=False);result=[]
 for target in offsets(a.phase):
  time.sleep(max(0,start+target-time.monotonic()));left=deadline-time.monotonic();assert left>0,'experiment deadline'
  argv=[sys.executable,str(HELPERS/'t31_outer.py'),'capture','candidate',a.boot];(out/(str(target)+'.argv.json')).write_text(json.dumps(argv))
  try:r=subprocess.run(argv,capture_output=True,timeout=min(20,left))
  except subprocess.TimeoutExpired as e:
   (out/(str(target)+'.stdout')).write_bytes(e.stdout or b'');(out/(str(target)+'.stderr')).write_bytes(e.stderr or b'');(out/(str(target)+'.rc')).write_text('timeout\n');raise
  (out/(str(target)+'.stdout')).write_bytes(r.stdout);(out/(str(target)+'.stderr')).write_bytes(r.stderr);(out/(str(target)+'.rc')).write_text(str(r.returncode)+'\n');result.append({'phase':a.phase,'requested_offset':target,'actual_elapsed':time.monotonic()-start,'rc':r.returncode});(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');assert r.returncode==0
if __name__=='__main__':main()
