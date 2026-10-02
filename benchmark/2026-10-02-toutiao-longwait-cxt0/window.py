"""Approved capture-only window: exact base readback, two existing batch calls, final readback."""
import argparse, datetime, hashlib, importlib.util, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
W = REPO.parent
MASTER = W / 'westlake-harness'
TOOLS = W / 'westlake-inputs/tools'
SERIAL = '61b0657200000000000000000324012c'
BOARD = MASTER / '.octos/boards/app-lighting.md'
ENV = dict(os.environ, WORKSPACES=str(W), MAC_HOME=str(Path.home()))

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def vm(args, **kw):
    return subprocess.run(['orb', '-m', 'a2hlab', 'env',
        'WORKSPACES='+str(W), 'MAC_HOME='+ENV['MAC_HOME'], *map(str, args)], **kw)

def note(text):
    subprocess.run(['bash', TOOLS/'board_note.sh', 'progress', BOARD, '90', 'cx-t0', text], check=True)

def identity(root):
    # No DeviceIO.verify(): it launches a control. This task asks only for unchanged 318 bytes.
    code = '''
import importlib.util,sys,json
from pathlib import Path
p=Path(sys.argv[1])/'benchmark/2026-10-02-u12-final-assembly/window_hook.py'
s=importlib.util.spec_from_file_location('capture_identity',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=m.verify(sys.argv[2],Path(sys.argv[3]),candidate=False,process_view=False)
assert r['identity_assertions']==318 and not r['diff'] and not r['absent']
print(json.dumps(r))
'''
    with (root.parent/(root.name+'.log')).open('w') as log:
        vm(['python3', '-c', code, REPO, SERIAL, root], stdout=log, stderr=subprocess.STDOUT,
           check=True, timeout=180)
    return json.loads((root/'identity.json').read_text())

def prelock(root):
    subprocess.run([sys.executable, REPO/'benchmark/2026-10-02-u12-final-assembly/window4/sample_infra.py',
                    root/'infra-before.json'], check=True)
    infra=json.loads((root/'infra-before.json').read_text())
    assert infra['orb']['rc']==0 and not infra['restart_required_before_lock'], 'VM pre-lock health refused'
    held=subprocess.run(['bash',TOOLS/'board_note.sh','held',SERIAL],capture_output=True,text=True)
    assert held.returncode in (0,1) and not held.stdout.strip(), 'board is held'
    p=vm(['bash',TOOLS/'hdc_mac.sh','list','targets'],capture_output=True,text=True,timeout=25,check=True)
    assert SERIAL in p.stdout.split(), 'board offline'
    bind=vm(['python3','-c','import pathlib,hashlib,sys; p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest())',
             MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'],capture_output=True,text=True,timeout=25,check=True)
    expected=hashlib.sha256((MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py').read_bytes()).hexdigest()
    assert bind.stdout.strip()==expected, 'workspace bind drift'
    p=vm(['bash',TOOLS/'hdc_mac.sh','-t',SERIAL,'shell',
          'cat /proc/sys/kernel/random/boot_id; pidof appspawn-x; hilog -g; param get hilog.private.on; date +%s'],
         capture_output=True,text=True,timeout=30,check=True)
    (root/'prelock-device.txt').write_text(p.stdout+p.stderr)
    save(root/'prelock.json',{'hdc':'PASS','workspace_bind':'PASS','bms_batch_sha256':expected,'held':held.stdout})

def run(root):
    root.mkdir(exist_ok=True)
    prelock(root)
    lock=subprocess.run(['bash',TOOLS/'board_note.sh','lock',BOARD,SERIAL,'cx-t0',
                         '90 U10.1T8 toutiao capture-only 2x t20/t45/t90 <=30min'],check=True)
    started=time.time()
    save(root/'window.json',{'started_epoch':started,'deadline_epoch':started+1800,'serial':SERIAL,
                           'base':'U10.1T8','variable':'capture offsets only','runtime_changes':False})
    failure=None
    try:
        held=subprocess.run(['bash',TOOLS/'board_note.sh','held',SERIAL],capture_output=True,text=True,check=True)
        assert held.stdout.startswith('cx-t0 '), 'wrong lock holder'
        (root/'held.txt').write_text(held.stdout)
        before=identity(root/'before318')
        note('1/4 61b LOCK+U10.1T8 318/双指纹通过；只跑头条2次 --wait95 --hilog95 --shots20,45,90，无运行时替换/JIT。')
        home=vm(['sh','-c','printf "%s" "$HOME"'],capture_output=True,text=True,timeout=25,check=True).stdout
        for trial in (1,2):
            assert time.time()<started+1200, 'reserve final verification time'
            out=root/('trial-'+str(trial));out.mkdir()
            args=['python3',MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py',
                  '--execute','--serial',SERIAL,'--lane','cx-t0',
                  '--manifest',MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json',
                  '--input-root',home+'/a2hlab/app-inputs','--keys','toutiao','--reinstall',
                  '--wait','95','--hilog','95','--shots','20,45,90','--hdc-cmd',str(TOOLS/'hdc_mac.sh'),
                  '--lock-cmd','mac '+str(TOOLS/'board_note.sh'),'--out',out,
                  '--run-id',root.name+'-trial'+str(trial)]
            save(out/'command.json',{'argv':list(map(str,args))})
            with (out/'batch.log').open('w') as log:
                p=vm(args,stdout=log,stderr=subprocess.STDOUT,timeout=600)
            records=list(out.glob('*/*/toutiao/record.json'))
            assert len(records)==1, 'batch did not wrap exactly one record'
            rec=json.loads(records[0].read_text())
            save(out/'exit.json',{'return_code':p.returncode,'status':rec.get('status')})
            assert p.returncode in (0,1) and rec.get('status') not in ('started','batch_interrupted'), 'batch infrastructure failed'
            facts=subprocess.run([sys.executable,MASTER/'scripts/lab/run_facts.py',records[0].parent.parent],
                                 capture_output=True,text=True,check=True)
            (out/'facts-verbatim.txt').write_text(facts.stdout)
            print(f'TRIAL {trial}\n'+facts.stdout,flush=True)
            note(f'{trial+1}/4 61b toutiao trial{trial}收尾 rc={p.returncode}；facts与t20/t45/t90落盘，交外环读图。')
    except Exception as exc:
        failure=str(exc)
        save(root/'failure.json',{'error':failure})
        print('WINDOW ERROR',failure,flush=True)
    finally:
        # Nothing was deployed. Never unconditionally unlock without exact final base readback.
        after=identity(root/'final318')
        assert after['fingerprints']==before['fingerprints'] and after['boot_id']==before['boot_id'], 'base drift'
        save(root/'finish.json',{'passed':True,'deployed':False,'identity_assertions':318,
                               'fingerprints':after['fingerprints'],'error':failure})
        subprocess.run(['bash',TOOLS/'board_note.sh','unlock',BOARD,SERIAL,'cx-t0'],check=True)
        subprocess.run([sys.executable,REPO/'benchmark/2026-10-02-u12-final-assembly/window4/sample_infra.py',
                        root/'infra-after.json'],check=True)
        note('4/4 61b头条长等待窗结束：final318 diff/absent空、双指纹/boot_id不变；无部署无需回滚，已UNLOCK。截图外环终判。')
    return bool(failure)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run(a.root))
