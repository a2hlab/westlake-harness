from pathlib import Path
import json,subprocess,sys,time
repo=Path.cwd();base=Path(__file__).parent;w=base/'t17-5cd-window-01';c=json.loads((w/'context.json').read_text());tag=sys.argv[1];o=w/tag;argv=[sys.executable,str(repo/'benchmark/2026-10-20-t17-network-reuse/collect_reader_profile.py'),'--execute','--repo',str(repo),'--hdc',c['hdc'],'--boot','5807db3d-32f6-4d16-a98a-0baad7352fb9','--parent','6067','--parent-birth','14025','--child','7906','--child-birth','15460','--host','5879','--host-birth','13836','--holder',c['holder'],'--start',str(c['start']),'--out',str(o)]
def run(name,argv):
 stem=w/name;stem.with_suffix('.argv.json').write_text(json.dumps(argv))
 with stem.with_suffix('.stdout').open('wb') as so,stem.with_suffix('.stderr').open('wb') as se:r=subprocess.run(argv,stdout=so,stderr=se,timeout=140)
 stem.with_suffix('.rc').write_text(str(r.returncode));print(name,r.returncode,stem.with_suffix('.stdout').read_text()[-1600:],stem.with_suffix('.stderr').read_text()[-1800:]);assert r.returncode==0
run(tag+'-exec',argv)
argv=[sys.executable,str(repo/'benchmark/2026-10-20-t17-network-reuse/read_binding.py'),'--execute','--repo',str(repo),'--profile',str(o/'profile.json'),'--receipt',str(o/'receipt.raw'),'--run-file',str(o/'run.sh'),'--inputs',str(base/'t16-r8-candidate-inputs'),'--net-elf',str(repo.parent/'westlake-inputs/seal-artifacts-20261012/sha256/f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e'),'--hdc',c['hdc'],'--holder',c['holder'],'--start',str(c['start']),'--out',str(w/(tag+'-bindings'))];run(tag+'-reader-exec',argv)
