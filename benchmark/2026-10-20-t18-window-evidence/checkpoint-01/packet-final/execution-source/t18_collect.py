from pathlib import Path
import json,subprocess,sys,time
repo=Path.cwd();base=Path(__file__).parent;w=base/'t18-5cd-window-01';c=json.loads((w/'context.json').read_text());tag=sys.argv[1];o=w/tag;argv=[sys.executable,str(repo/'benchmark/2026-10-20-t17-network-reuse/collect_reader_profile.py'),'--execute','--repo',str(repo),'--hdc',c['hdc'],'--boot','6b99680b-3d15-476a-a229-dc3591e34add','--parent','6538','--parent-birth','18965','--child','8315','--child-birth','20337','--host','6333','--host-birth','18732','--holder',c['holder'],'--start',str(c['start']),'--out',str(o)]
def run(name,argv):
 stem=w/name;stem.with_suffix('.argv.json').write_text(json.dumps(argv))
 with stem.with_suffix('.stdout').open('wb') as so,stem.with_suffix('.stderr').open('wb') as se:r=subprocess.run(argv,stdout=so,stderr=se,timeout=140)
 stem.with_suffix('.rc').write_text(str(r.returncode));print(name,r.returncode,stem.with_suffix('.stdout').read_text()[-1600:],stem.with_suffix('.stderr').read_text()[-1800:]);assert r.returncode==0
run(tag+'-exec',argv)
