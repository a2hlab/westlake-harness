"""Root-channel wrapper around the inherited read-only admission frame."""
import argparse,json,subprocess,time
from pathlib import Path
from window_paths import WINDOW,context,budget,tag
import fill_admission,rollback_core

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['apply','rollback']);p.add_argument('parent',type=int);p.add_argument('host',type=int);p.add_argument('tag');a=p.parse_args()
 c=context();deadline=time.monotonic()+budget(c,a.mode=='rollback');tag(a.tag);out=WINDOW/a.tag;out.mkdir(exist_ok=False)
 def run(name,argv):
  left=deadline-time.monotonic();assert left>0
  (out/(name+'.argv.json')).write_text(json.dumps(argv))
  try:r=subprocess.run(argv,capture_output=True,timeout=min(40,left),cwd=c['repo'])
  except subprocess.TimeoutExpired as e:
   (out/(name+'.stdout')).write_bytes(e.stdout or b'');(out/(name+'.stderr')).write_bytes(e.stderr or b'');(out/(name+'.rc')).write_text('timeout');raise
  (out/(name+'.stdout')).write_bytes(r.stdout);(out/(name+'.stderr')).write_bytes(r.stderr);(out/(name+'.rc')).write_text(str(r.returncode)+'\n');assert r.returncode==0
  return r
 r=run('held',['bash',str(Path(c['repo'])/'scripts/lab/board_note.sh'),'held',c['serial']]);assert r.stdout.decode().strip()==c['holder']
 source=fill_admission if a.mode=='apply' else rollback_core
 script=source.read_script(a.parent,a.host);(out/'read.sh').write_text(script)
 run('read',[c['hdc'],'-t',c['serial'],'shell',script])
 print(json.dumps({'out':str(out),'status':'RAW_CAPTURED_LOCAL_FILL_MUST_VALIDATE_REMOTE_RC'}))
if __name__=='__main__':main()
