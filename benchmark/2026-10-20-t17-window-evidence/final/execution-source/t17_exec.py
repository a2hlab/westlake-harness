from pathlib import Path
import sys,subprocess,json,time
repo=Path.cwd();base=Path(__file__).parent;out=base/'t17-5cd-window-01';c=json.loads((out/'context.json').read_text());mode,boot,parent,birth,adfile,tag=sys.argv[1:];dest=out/tag
argv=[sys.executable,str(repo/'benchmark/2026-10-20-t17-network-reuse/executor.py'),mode,'--execute','--repo',str(repo),'--inputs',str(base/'t16-r8-candidate-inputs'),'--boot',boot,'--parent',parent,'--birth',birth,'--hdc',c['hdc'],'--holder',c['holder'],'--start',str(c['start']),'--admission',str(out/adfile),'--out',str(dest)]
if mode=='rollback':argv+=['--apply-plan',str(out/'apply/plan.json')]
(out/(tag+'-exec.argv.json')).write_text(json.dumps(argv));t=time.time()
with (out/(tag+'-exec.stdout')).open('wb') as so,(out/(tag+'-exec.stderr')).open('wb') as se:r=subprocess.run(argv,stdout=so,stderr=se,timeout=180)
(out/(tag+'-exec.rc')).write_text(str(r.returncode));print('rc',r.returncode,'seconds',time.time()-t);print((out/(tag+'-exec.stdout')).read_text()[-3000:]);print((out/(tag+'-exec.stderr')).read_text()[-3000:]);sys.exit(r.returncode)
