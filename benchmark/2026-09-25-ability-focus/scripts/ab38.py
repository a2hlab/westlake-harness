"""VM-only, serialized no-hiperf four-arm comparison on the sole #38 board."""
from board34 import *
import hashlib
arm,name=sys.argv[1:3];assert arm in ('base','nojit','npth','verify')
origin='warm-b11';d=json.loads((R/origin/'device-report.json').read_text());runtime=d['runtime']
work=R/'ab-config';work.mkdir(exist_ok=True)
assert not dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120).strip(),'live namespace'
def send(p,remote):subprocess.run([H,'-t',S,'file','send',str(p),remote],check=True,timeout=240)
base=work/'original-run.sh'
if not base.exists():
 recv(runtime+'/run.sh',base)
 assert not dev('find '+runtime+'/oat -type f 2>/dev/null').strip(),'Unexpected original app oat'
text=base.read_text();assert 'APPSPAWNX_NO_JIT' not in text
if arm=='nojit':text=text.replace('exec /data/local/tmp/asx/appspawn-x','export APPSPAWNX_NO_JIT=1\nexec /data/local/tmp/asx/appspawn-x')
run=work/(name+'.run.sh');run.write_text(text);send(run,runtime+'/run.sh');dev('chmod 755 '+runtime+'/run.sh')
dev('rm -rf '+runtime+'/oat') # this runner owns only the added application-oat directory
provenance={'arm':arm,'run_sha256':hashlib.sha256(run.read_bytes()).hexdigest(),'consent_age_seconds':60,'hiperf':False,'origin':origin,'changes':[]}
if arm=='verify':
 inp=json.loads((pathlib.Path.home()/'a2hlab/ws/out-aot42/input-files.json').read_text())
 files={k:v for k,v in inp.items() if k.startswith(('fw/','boot/'))}
 actual=dev('sha256sum '+' '.join(runtime+'/'+k for k in files),120)
 values={line.split()[1]:line.split()[0] for line in actual.splitlines() if len(line.split())==2}
 assert all(values.get(runtime+'/'+k)==v['sha256'] for k,v in files.items()),'BCP/boot mismatch'
 provenance['matched_framework_inputs']=len(files)
 dev('mkdir -p '+runtime+'/oat/arm64')
 for ext in ('odex','vdex','art'):
  p=pathlib.Path.home()/'a2hlab/ws/out-aot42/verify-explicit'/('toutiao.'+ext);remote=runtime+'/oat/arm64/'+p.name
  send(p,remote);h=hashlib.sha256(p.read_bytes()).hexdigest();assert dev('sha256sum '+remote).split()[0]==h
  provenance['changes'].append({'path':remote,'sha256':h,'bytes':p.stat().st_size})
 dev('chown -R 20010053:20010053 '+runtime+'/oat; chmod -R a+rX '+runtime+'/oat')
helper=pathlib.Path.home()/'a2hlab/ws/out-ability38/ab/proc38'
provenance['proc_helper_sha256']=hashlib.sha256(helper.read_bytes()).hexdigest()
send(helper,'/data/local/tmp/ability38-proc');dev('chmod 755 /data/local/tmp/ability38-proc')
(work/(name+'.json')).write_text(json.dumps(provenance,indent=2)+'\n')
args=['python3',str(pathlib.Path(__file__).with_name('physical34.py')),name,'article','--candidate','--origin='+origin,'--select-title','--delay-consent=60']
if arm=='base':args+=['--offcpu']
if arm=='npth':args+=['--npth-pause']
try:
 p=subprocess.run(args);print('AB_DONE',arm,name,p.returncode,flush=True)
finally:
 if (R/name).exists():(R/name/'ab-config.json').write_text(json.dumps(provenance,indent=2)+'\n')
 send(base,runtime+'/run.sh');dev('chmod 755 '+runtime+'/run.sh; rm -rf '+runtime+'/oat')

sys.exit(p.returncode)
