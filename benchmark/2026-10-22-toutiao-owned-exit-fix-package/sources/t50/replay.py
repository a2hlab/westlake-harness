#!/usr/bin/env python3
"""T50: actual pinned main/identity branches, synthetic external reads only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PINS = {'baseline/route-b-owner.sh': 'fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58', 'baseline/watchdog.sh': 'bcae2c697ae5ee6e31c836cd38d322d5120a87ffa74f1d35d2c88acca7be818e', 'candidate/route-b-owner.sh': 'fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58', 'candidate/watchdog.sh': 'd45a8d36794d3927c0c03f19d71fa632a0b9cec18944d9d9f92a3406b49f64f0'}
OLD_BYTES = b'{"evidence":"earlier committed sequence; preserve exactly"}\n'

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pin_sources(root):
    for name, expected in PINS.items():
        require(sha(root/name) == expected, 'source pin mismatch: '+name)

def library(root, variant):
    w = (root/variant/'watchdog.sh').read_text()
    o = (root/variant/'route-b-owner.sh').read_text()
    require(w.endswith('main "$@"\n'), 'main entry is not exact')
    # T46 seam: defer only automatic main; keep every production function intact.
    b = o[o.index('rb_birth(){'):o.index('rb_uid(){')]
    return w[:-len('main "$@"\n')] + b.replace('rb_birth(){', 'fixture_original_rb_birth(){', 1)

def logged(argv, out, cwd=None, env=None):
    out.mkdir(parents=True, exist_ok=False)
    (out/'argv.json').write_text(json.dumps(argv)+'\n')
    (out/'start').write_text(str(time.time())+'\n')
    rc = None
    try:
        with (out/'stdout').open('wb') as stdout, (out/'stderr').open('wb') as stderr:
            try:
                rc = subprocess.run(argv, cwd=cwd, env=env, stdout=stdout,
                                    stderr=stderr, timeout=30).returncode
            except subprocess.TimeoutExpired:
                rc = 124
    finally:
        (out/'end').write_text(str(time.time())+'\n')
        (out/'rc').write_text(str(rc)+'\n')
    return rc

# Each mutation is applied AFTER an actual successful local stat read.
# Counts: attach 1..5; monitor 6; child_owned first 7, rb_owned 8/9,
# ppid 10, last 11; first capture context 12..16.
CONFIG = {
 'transient_live':(0,''), 'normal':(0,''), 'stop':(5,'stop'),
 'first_missing':(5,'absent'), 'first_birth_missing':(6,'absent'),
 'last_birth_missing':(10,'absent'), 'zombie':(6,'replace'),
 'monitor_zombie':(5,'replace'), 'monitor_reused_zombie':(5,'replace'),
 'monitor_stat_missing':(5,'stat_missing'), 'monitor_parent_bad':(5,'absent'),
 'existing_exit':(6,'absent'), 'stat_missing':(6,'stat_missing'),
 'malformed':(6,'replace'), 'parent_unreadable':(6,'absent'),
 'parent_bad':(6,'absent'), 'parent_missing':(6,'absent'),
 'zombie_reused':(6,'replace'), 'birth_changed':(6,'replace'),
 'ppid_changed':(6,'replace'), 'rb_internal':(7,'absent'),
 'plain_refusal':(6,'uid'), 'existing':(6,'uid'), 'occupied':(6,'uid'),
 'symlink':(6,'uid'), 'dangling':(6,'uid'), 'directory':(6,'uid'),
 'exhaustion':(6,'uid'), 'write_failure':(6,'uid'), 'read_failure':(6,'uid'),
 'init_attach':(0,''), 'init_spawn':(1,'absent'), 'init_refusal_existing':(0,''),
 'capture_first':(11,'absent'), 'capture_last':(15,'absent'),
}
CASES=tuple(CONFIG)
EXIT_CASES={'first_missing','first_birth_missing','last_birth_missing','zombie','monitor_zombie','existing_exit'}
INIT={'init_attach','init_spawn','init_refusal_existing'}
COLLISIONS={'existing','occupied','symlink','dangling','directory','exhaustion','init_refusal_existing'}
IO={'symlink','dangling','directory','exhaustion','write_failure','read_failure'}

def stat_row(pid=42,state='S',birth=200,ppid=43):
    fields=[state,str(ppid)]+['0']*48
    fields[19]=str(birth)
    return str(pid)+' (synthetic local process) '+' '.join(fields)+'\n'

def diagnostic_snapshot(c):
    rows={}
    for p in sorted((c/'state').glob('guardian-refusal-*')):
        if p.is_symlink(): rows[p.name]={'kind':'symlink','target':p.readlink().as_posix()}
        elif p.is_dir(): rows[p.name]={'kind':'directory','entries':sorted(x.name for x in p.iterdir())}
        else: rows[p.name]={'kind':'file','sha256':sha(p),'size':p.stat().st_size}
    return rows

def run_case(out,source_root,variant,mode):
    c=out/variant/mode;c.mkdir(parents=True,exist_ok=False)
    for path in ('state','runtime/app-data','runtime/data','runtime/webview-t-data','proc/42','proc/43','proc/sys/kernel/random'):
        (c/path).mkdir(parents=True,exist_ok=True)
    (c/'stat-live').write_text(stat_row())
    (c/'status-live').write_text('Uid: 12345 12345 12345 12345\n')
    shutil.copyfile(c/'stat-live',c/'proc/42/stat');shutil.copyfile(c/'status-live',c/'proc/42/status')
    (c/'proc/43/stat').write_text(stat_row(43,birth=90,ppid=1))
    if mode in ('parent_bad','monitor_parent_bad'):(c/'proc/43/stat').write_text(stat_row(43,birth=91,ppid=1))
    if mode=='parent_missing':(c/'proc/43/stat').unlink()
    replacement=stat_row()
    if mode in ('zombie','monitor_zombie'):replacement=stat_row(state='Z')
    if mode in ('zombie_reused','monitor_reused_zombie'):replacement=stat_row(state='Z',birth=201)
    if mode=='birth_changed':replacement=stat_row(birth=201)
    if mode=='ppid_changed':replacement=stat_row(ppid=99)
    if mode=='malformed':replacement='42 (malformed) Z 43 0\n'
    (c/'stat-replacement').write_text(replacement)
    (c/'proc/sys/kernel/random/boot_id').write_text('fixture-boot\n')
    (c/'proc/uptime').write_text('100.00 200.00\n')
    (c/'stat-count').write_text('0\n');(c/'trace.jsonl').write_text('')
    if mode in ('init_attach','init_spawn'):shutil.rmtree(c/'proc/42')
    if mode=='init_refusal_existing':
        (c/'proc/42/status').write_text('Uid: 9 9 9 9\n')
        (c/'state/sequence').write_text('1\n')
    if mode in COLLISIONS or mode=='existing_exit':
        (c/'state/guardian-refusal-1.jsonl').write_bytes(OLD_BYTES)
    slots=3 if mode=='occupied' else 16 if mode=='exhaustion' else 0
    for slot in range(1,slots+1):(c/f'state/guardian-refusal-1.{slot}.jsonl').write_bytes(OLD_BYTES+str(slot).encode()+b'\n')
    slot=c/'state/guardian-refusal-1.1.jsonl'
    if mode=='symlink':
        (c/'state/link-target').write_bytes(OLD_BYTES);slot.symlink_to('link-target')
    if mode=='dangling':slot.symlink_to('absent-target')
    if mode=='directory':slot.mkdir()
    (c/'diagnostic-before.json').write_text(json.dumps(diagnostic_snapshot(c),indent=2)+'\n')
    (c/'functions.sh').write_text(library(source_root,variant))
    shutil.copyfile(source_root/variant/'route-b-owner.sh',c/'route-b-owner.sh')
    shutil.copyfile(ROOT/'fixture.sh',c/'driver.sh')
    trigger,mutation=CONFIG[mode]
    env={'PATH':'/usr/bin:/bin','LC_ALL':'C','MODE':mode,'TRIGGER':str(trigger),'MUTATION':mutation}
    (c/'synthetic-env.json').write_text(json.dumps(env,indent=2)+'\n')
    (c/'source-pins.json').write_text(json.dumps(PINS,indent=2)+'\n')
    logged(['/bin/sh','./driver.sh'],c/'raw',cwd=c,env=env)

def expected(variant,mode):
    if mode in IO:
        # Original persistence is not using the candidate's printf boundary.
        if mode in ('write_failure','read_failure') and variant=='baseline':return 2,'OWNER_REFUSED'
        return 5,'IO_FAILED'
    if variant=='baseline' and mode in COLLISIONS:return 5,'IO_FAILED'
    if mode=='normal':return 0,'UI_UNVERIFIED'
    if mode=='stop':return 0,'STOPPED'
    if mode in ('first_missing','monitor_zombie') or mode.startswith('capture_'):return 4,'RETRY_LIMIT'
    if variant=='baseline' and mode in ('monitor_reused_zombie','monitor_parent_bad'):return 4,'RETRY_LIMIT'
    if variant=='candidate' and mode in EXIT_CASES:return 4,'RETRY_LIMIT'
    if mode in ('init_attach','init_spawn') and variant=='candidate':return 3,'START_FAILED'
    if mode=='existing_exit' and variant=='baseline':return 5,'IO_FAILED'
    return 2,'OWNER_REFUSED'

def validate_case(out,source_root,variant,mode):
    c=out/variant/mode;raw=c/'raw'
    require((c/'functions.sh').read_text()==library(source_root,variant),'actual production body drift')
    require(sha(c/'route-b-owner.sh')==PINS[variant+'/route-b-owner.sh'],'owner drift')
    require((c/'driver.sh').read_bytes()==(ROOT/'fixture.sh').read_bytes(),'fixture drift')
    require(json.loads((c/'source-pins.json').read_text())==PINS,'receipt source drift')
    trigger,mutation=CONFIG[mode]
    require(json.loads((c/'synthetic-env.json').read_text())=={'PATH':'/usr/bin:/bin','LC_ALL':'C','MODE':mode,'TRIGGER':str(trigger),'MUTATION':mutation},'seam input drift')
    require(json.loads((raw/'argv.json').read_text())==['/bin/sh','./driver.sh'],'wrong actual entry')
    require(float((raw/'end').read_text())>=float((raw/'start').read_text()),'missing times')
    trace=[json.loads(x) for x in (c/'trace.jsonl').read_text().splitlines()]
    require(not any('FORBIDDEN' in e['event'] for e in trace),'real process/device boundary reached')
    mutations=[x for x in trace if x['event']=='mutation']
    require(mutations==([{'event':'mutation','after_stat':trigger,'kind':mutation}] if trigger else []),'actual mutation absent')
    if trigger:
        pos=trace.index(mutations[0]);require(trace[pos-1]=={'event':'stat_read','ordinal':trigger,'rc':0},'not after actual successful read')
    reads=[e for e in trace if e['event']=='stat_read']
    require([e['ordinal'] for e in reads]==list(range(1,len(reads)+1)), 'actual stat trace incomplete')
    child_reads=[e for e in trace if e['event']=='birth' and e['pid']=='42']
    failed=[e for e in child_reads if e['rc']!=0]
    read_failure_modes=EXIT_CASES|{'transient_live','stat_missing','malformed','parent_unreadable','parent_bad','parent_missing','zombie_reused','rb_internal','monitor_reused_zombie','monitor_stat_missing','monitor_parent_bad','init_attach','init_spawn','capture_first','capture_last'}
    if mode in read_failure_modes:
        require(failed and all(e['value']=='' for e in failed), 'actual empty failed birth trace missing')
    if mode in ('normal','stop','plain_refusal','existing','occupied','symlink','dangling','directory','exhaustion','init_refusal_existing','write_failure','read_failure'):
        require(not failed, 'control case had birth read failure')
    rc=int((raw/'rc').read_text());state=(c/'state/state').read_text().strip()
    require((rc,state)==expected(variant,mode),'wrong main rc/state: '+str((variant,mode,rc,state,expected(variant,mode))))
    events=(c/'state/events.log').read_text()
    require('SUPERVISOR_STARTING' in events,'main absent')
    before=json.loads((c/'diagnostic-before.json').read_text());after=diagnostic_snapshot(c)
    for name,value in before.items():require(after.get(name)==value,'old diagnostic changed: '+name)
    if mode=='symlink':require((c/'state/link-target').read_bytes()==OLD_BYTES,'symlink target changed')
    if mode=='dangling':require(not (c/'state/absent-target').exists(),'followed dangling symlink')
    added=set(after)-set(before)
    end=json.loads((c/'main-end.json').read_text()) if (c/'main-end.json').exists() else None
    if rc==5:require((c/'state/lock/owner').is_file(),'IO failure released lock')
    else:
        require(end is not None and end['parent']=='43','parent/return evidence absent')
        require(end['attempt']==('0' if mode in INIT else '1'),'attempt budget changed')
        require(end['seq']==('1' if mode=='init_refusal_existing' or mode not in INIT else '0'),'sequence changed')
    if mode in INIT:
        require((c/'sequence-at-validation').read_bytes()==(c/'state/sequence').read_bytes(),'initial sequence increment')
        require((c/'instance-at-validation').read_bytes()==(c/'state/instance.txt').read_bytes(),'initial instance rewrite after validation')
        require('BOOTSTRAP' not in events,'initial reject continued supervision')
    if mode=='init_spawn':require(sum(e['event']=='synthetic_spawn' for e in trace)==1,'spawn count differs')
    else:require(not any(e['event']=='synthetic_spawn' for e in trace),'unexpected launch')
    classification=[]
    if variant=='candidate' and (mode in EXIT_CASES or mode in ('init_attach','init_spawn') or mode.startswith('capture_')):
        kind='zombie' if 'zombie' in mode else 'gone'
        phase='monitor_birth' if mode in ('first_missing','monitor_zombie') else 'last_birth' if mode in ('last_birth_missing','capture_last') else 'first_birth'
        require('classified='+kind+' phase='+phase in events,'required classification evidence missing')
        witness=[e for e in trace if e['event']=='birth' and e['pid']=='43']
        require(witness and all(e['rc']==0 and e['value']=='90' for e in witness),'positive parent witness missing')
        if kind=='gone':require(any(e['event']=='classification_parent_listing' for e in trace),'required classification trace missing')
        require(not added,'confirmed exit consumed diagnostic slot')
        require('"field"' not in (raw/'stderr').read_text(),'confirmed exit called rb_deny')
        classification=[line.split('reason=',1)[-1] for line in events.splitlines() if 'classified=' in line]
    if rc==4:
        require('reason=process_exit' in events and 'transition_target=RECOVERING' in events and 'attempts_exhausted_no_cleanup' in events,'original recovery missing')
        require('retry_backoff' not in events,'attempt limit changed')
    if mode.startswith('capture_'):
        reason='child_exited_during_capture' if variant=='candidate' else 'child_identity_during_capture'
        require(reason in events and events.index(reason)<events.index('reason=process_exit'),'capture exit/monitor order missing')
    if variant=='candidate' and mode in ('existing','occupied','init_refusal_existing','plain_refusal'):
        slot=4 if mode=='occupied' else 0 if mode=='plain_refusal' else 1
        name='guardian-refusal-1'+('' if slot==0 else '.'+str(slot))+'.jsonl'
        require(added=={name},'wrong diagnostic slot')
        record=json.loads((c/'state'/name).read_text())
        require(record=={'phase':'strict','pid':'42','birth':'200','field':'uid','actual':'9:9:9:9','expected':'12345:12345:12345:12345'},'wrong denial payload')
    if mode=='transient_live':
        require(any(e['event']=='transient_read_fault' for e in trace),'transient I/O failure absent')
        require(any(e['event']=='stat_read' and e['rc']!=0 for e in trace),'real read failure absent')
        require((c/'proc/42/stat').read_text()==stat_row(),'live same-birth evidence changed')
        require('RECOVERING' not in events,'live process classified as exited')
    if mode in ('normal','stop'):require(not added,'normal/stop wrote refusal')
    return {'variant':variant,'case':mode,'rc':rc,'state':state,'end':end,'classification':classification,
            'old_diagnostics':before,'new_diagnostics':sorted(added),'diagnostics':after,
            'trace_sha256':sha(c/'trace.jsonl'),'events_sha256':sha(c/'state/events.log'),
            'raw':{n:{'sha256':sha(raw/n),'size':(raw/n).stat().st_size} for n in ('argv.json','start','end','stdout','stderr','rc')}}

def validate(out,source):
    pin_sources(source)
    rows=[validate_case(out,source,v,m) for m in CASES for v in ('baseline','candidate')]
    b=out/'baseline/plain_refusal/state/guardian-refusal-1.jsonl'
    c=out/'candidate/plain_refusal/state/guardian-refusal-1.jsonl'
    require(b.read_bytes()==c.read_bytes(),'slot zero encoding differs from baseline')
    require(PINS['baseline/route-b-owner.sh']==PINS['candidate/route-b-owner.sh'],'owner changed')
    return {'passed':True,'case_count':len(CASES),'executions':len(rows),'source_pins':PINS,'rows':rows,'slot0_equal_sha256':sha(b),
            'limits':['Synthetic filesystem/process metadata and device boundaries only.','No device shell O_EXCL or visibility claim.','rb_owned, namespace and ppid read-error exits remain terminal.','Initial validation no-rewrite measured after original startup persistence checks.']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);ap.add_argument('--sources',type=Path,default=ROOT);ap.add_argument('--verify-only',action='store_true')
    a=ap.parse_args();source=a.sources.resolve();out=a.out.resolve();pin_sources(source)
    if not a.verify_only:
        out.mkdir(parents=True,exist_ok=False)
        for mode in CASES:
            for variant in ('baseline','candidate'):run_case(out,source,variant,mode)
    result=validate(out,source)
    if not a.verify_only:(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'executions':result['executions'],'cases':len(CASES),'verify_only':a.verify_only}))
if __name__=='__main__':main()
