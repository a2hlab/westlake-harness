#!/usr/bin/env python3
"""N10b authorized 5cd transaction: restore verified U8 before releasing its lock."""
import argparse,json,os,subprocess,sys,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/u7_executor.py').is_file())
sys.path.insert(0,str(REPO/'scripts/lab'))
import lab_paths,u7_executor as u
WS=lab_paths.workspaces();MASTER=WS/'westlake-harness'
SERIAL='5cd1e3dd00000000000000000923012c';LANE='cx-t0'
BOARD=MASTER/'.octos/boards/app-lighting.md'
ROOT=HERE/'board5cd-a118aca0-r2';JOURNAL=ROOT/'transaction/journal.json'
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def executor(argv):
    if sys.platform != 'darwin':return u.main(argv)
    import shlex
    env={'MAC_HOME':str(Path.home()),'LAB_HOME':os.environ['LAB_HOME'],'NATIVE_READELF':'/usr/bin/readelf'}
    command=' '.join(f'export {k}={shlex.quote(v)};' for k,v in env.items())
    command+= ' '+shlex.join(['bash',str(REPO/'benchmark/2026-10-01-u7-executor/board61b/run-executor.sh'),*argv])
    return subprocess.run(['orb','-m','a2hlab','bash','-lc',command]).returncode

def read_baseline():
    p=json.loads((HERE/'approved-production-dry-run.json').read_text())
    io=u.DeviceIO(SERIAL,LANE,ROOT/'before-device')
    got,absent=io.snapshot(sorted(p['baseline']));fp=u.fingerprints(got,p['reference_paths'])
    save(ROOT/'before.json',{'boot_id':io.boot,'identity_count':len(got),'matches':got==p['baseline'],'absent':absent,'fingerprints':fp})
    assert got==p['baseline'] and not absent
    assert fp['runtime']['sha256_12']=='e953c0921536'

def finish():
    if not JOURNAL.exists():raise RuntimeError('missing transaction journal; inspect board before releasing lock')
    rc=executor(['--rollback','--journal',str(JOURNAL),'--out',str(ROOT/('transaction/rollback-'+uuid.uuid4().hex+'.json')),'--serial',SERIAL,'--lane',LANE])
    if rc:raise RuntimeError('U8 rollback failed')
    state=json.loads(JOURNAL.read_text());fp=state['rollback_fingerprints']
    assert state['status']=='rolled_back',state['status']
    assert fp['runtime']['sha256_12']=='e953c0921536',fp
    assert fp['boot']['sha256_12']=='4db882a81732',fp
    assert len(state['plan']['baseline'])==312
    save(ROOT/'final-u8.json',{'status':state['status'],'fingerprints':fp,'identity_count':312,'verification':state['rollback_verification']})
    subprocess.run([str(MASTER/'scripts/lab/board_append.sh'),str(BOARD),'PROGRESS(95): cx-t0 N10b已回滚U8，312身份及父子视图/单ART核验通过，双指纹 e953c0921536/4db882a81732；下一步放锁。'],check=True)
def run():
    if ROOT.exists():raise RuntimeError('new window requires a fresh output directory')
    ROOT.mkdir();note=lab_paths.tools()/'board_note.sh'
    subprocess.run([str(note),'lock',str(BOARD),SERIAL,LANE,'#95 N10b a118aca0 ≤30min smoke and six keys, rollback U8'],check=True)
    locked=time.time();save(ROOT/'window.json',{'started_epoch':locked,'deadline_epoch':locked+1800,'serial':SERIAL})
    runner_started=False
    try:
        if sys.platform == 'darwin':
            import shlex
            command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; python3 '+shlex.join([str(HERE/'window.py'),'--read-baseline'])
            subprocess.run(['orb','-m','a2hlab','bash','-lc',command],check=True)
        else:read_baseline()
        subprocess.run([str(MASTER/'scripts/lab/board_append.sh'),str(BOARD),f'PROGRESS(95): cx-t0 5cd占用:N10b a118aca0，窗口起点epoch={locked:.0f}，≤30min；U8只读312身份全同/双指纹一致，先apply→标准冒烟→六key→回滚U8再放锁。'],check=True)
        rc=executor(['--apply','--package',str(WS/'westlake-generation-n10b-deployable-u8-ac59dec0'),'--baseline-native',str(WS/'westlake-generation-u8-j9-t7e/native'),'--oatdump',str(MASTER/'scripts/lab/oatdump_remote.sh'),'--journal',str(JOURNAL),'--out',str(ROOT/'transaction/apply.json'),'--serial',SERIAL,'--lane',LANE])
        if rc:raise RuntimeError('apply failed; no smoke or target shards')
        runner_started=True
        return subprocess.run([sys.executable,str(MASTER/'scripts/lab/board_run.py'),str(HERE/'plan-5cd.json'),'--detach'],cwd=MASTER).returncode
    finally:
        if not runner_started:
            if JOURNAL.exists():finish()
            subprocess.run([str(note),'unlock',str(BOARD),SERIAL,LANE],check=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--finish',action='store_true');ap.add_argument('--read-baseline',action='store_true');a=ap.parse_args()
    if a.read_baseline:read_baseline()
    elif a.finish:finish()
    else:sys.exit(run())
