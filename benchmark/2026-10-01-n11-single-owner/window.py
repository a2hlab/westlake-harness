"""after_lock / before_unlock; all board writes guarded by the master Mac lock."""
import argparse,json,os,shlex,subprocess,sys,time,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import lab_paths,u7_executor as u
WS=lab_paths.workspaces();M=WS/'westlake-harness';SERIAL='61b0657200000000000000000324012c';ROOT=H/'board61b';JOURNAL=ROOT/'transaction/journal.json'
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2)+'\n')
def vm(argv):
 env={'MAC_HOME':str(Path.home()),'LAB_HOME':os.environ['LAB_HOME'],'NATIVE_READELF':'/usr/bin/readelf'}
 command=' '.join('export '+k+'='+shlex.quote(v)+';' for k,v in env.items())+' '+shlex.join(['bash',str(R/'benchmark/2026-10-01-u7-executor/board61b/run-executor.sh'),*argv])
 return subprocess.run(['orb','-m','a2hlab','bash','-lc',command]).returncode

def read_baseline():
 row=json.loads((H/'approved-production-dry-run.json').read_text());io=u.DeviceIO(SERIAL,'cx-t0',ROOT/'before-device');got,absent=io.snapshot(sorted(row['baseline']));fp=u.fingerprints(got,row['reference_paths']);save(ROOT/'before.json',{'boot_id':io.boot,'identity_count':len(got),'matches':got==row['baseline'],'absent':absent,'fingerprints':fp});assert got==row['baseline'] and not absent

def apply():
 if JOURNAL.exists():raise RuntimeError('new window requires a fresh journal')
 save(ROOT/'window.json',{'started_epoch':time.time(),'deadline_epoch':time.time()+2700,'serial':SERIAL})
 subprocess.run(['orb','-m','a2hlab','bash','-lc','export MAC_HOME='+shlex.quote(str(Path.home()))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--read-baseline'])],check=True)
 row=json.loads((H/'production-package.json').read_text());rc=vm(['--apply','--package',str(WS/row['bundle']),'--baseline-native',str(WS/'westlake-generation-u8-j9-t7e/native'),'--oatdump',str(M/'scripts/lab/oatdump_remote.sh'),'--journal',str(JOURNAL),'--out',str(ROOT/'transaction/apply.json'),'--serial',SERIAL,'--lane','cx-t0']);return rc

def finish():
 if not JOURNAL.exists():
  # Before-read failed: no apply was invoked and no board writes occurred.
  if (ROOT/'before.json').is_file():assert json.loads((ROOT/'before.json').read_text())['matches']
  save(ROOT/'no-apply.json',{'no_journal':True,'no_candidate_applied':True});return 0
 rc=vm(['--rollback','--journal',str(JOURNAL),'--out',str(ROOT/('transaction/rollback-'+uuid.uuid4().hex+'.json')),'--serial',SERIAL,'--lane','cx-t0'])
 if rc:return rc
 j=json.loads(JOURNAL.read_text());fp=j['rollback_fingerprints'];assert j['status']=='rolled_back';assert fp['runtime']['sha256_12']=='e953c0921536' and fp['boot']['sha256_12']=='4db882a81732'
 save(ROOT/'final-u8.json',{'status':j['status'],'identity_count':len(j['plan']['baseline']),'fingerprints':fp,'verification':j['rollback_verification']});return 0
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--finish',action='store_true');p.add_argument('--read-baseline',action='store_true');a=p.parse_args()
 if a.read_baseline:read_baseline()
 else:sys.exit(apply() if a.apply else finish())
