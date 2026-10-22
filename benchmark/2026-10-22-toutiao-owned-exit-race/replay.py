#!/usr/bin/env python3
"""T49: actual pinned main/identity branches, synthetic external reads only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PINS = {
    'baseline/watchdog.sh': '2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a',
    'baseline/route-b-owner.sh': '6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c',
    'candidate/watchdog.sh': 'bcae2c697ae5ee6e31c836cd38d322d5120a87ffa74f1d35d2c88acca7be818e',
    'candidate/route-b-owner.sh': 'fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58',
}
CASES = ('first_missing', 'second_missing', 'second_missing_existing', 'normal')
OLD_BYTES = b'{"evidence":"synthetic earlier refusal; preserve exactly"}\n'

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

def run_case(out, source_root, variant, mode):
    c = out/variant/mode
    c.mkdir(parents=True, exist_ok=False)
    for path in ('state', 'runtime/app-data', 'runtime/data', 'runtime/webview-t-data',
                 'proc/42', 'proc/sys/kernel/random'):
        (c/path).mkdir(parents=True, exist_ok=True)
    (c/'proc/42/stat').write_text('42 (synthetic) S 43 '+'0 '*17+'200\n')
    (c/'proc/42/status').write_text('Uid: 12345 12345 12345 12345\n')
    (c/'proc/sys/kernel/random/boot_id').write_text('fixture-boot\n')
    (c/'proc/uptime').write_text('100.00 200.00\n')
    (c/'stat-count').write_text('0\n')
    (c/'trace.jsonl').write_text('')
    diag = c/'state/guardian-refusal-1.jsonl'
    if mode == 'second_missing_existing':
        diag.write_bytes(OLD_BYTES)
    before = sha(diag) if diag.exists() else None
    (c/'diagnostic-before.json').write_text(json.dumps({'sha256': before})+'\n')
    (c/'functions.sh').write_text(library(source_root, variant))
    shutil.copyfile(source_root/variant/'route-b-owner.sh', c/'route-b-owner.sh')
    shutil.copyfile(ROOT/'fixture.sh', c/'driver.sh')
    (c/'source-pins.json').write_text(json.dumps({k: v for k, v in PINS.items() if k.startswith(variant+'/')}, indent=2)+'\n')
    logged(['/bin/sh', './driver.sh'], c/'raw', cwd=c,
           env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'MODE': mode})

def validate_case(out, source_root, variant, mode):
    c = out/variant/mode
    require((c/'functions.sh').read_text() == library(source_root, variant), 'actual main library drift')
    require(sha(c/'route-b-owner.sh') == PINS[variant+'/route-b-owner.sh'], 'actual owner drift')
    require((c/'driver.sh').read_bytes() == (ROOT/'fixture.sh').read_bytes(), 'fixture drift')
    require(json.loads((c/'source-pins.json').read_text()) == {k:v for k,v in PINS.items() if k.startswith(variant+'/')}, 'source receipt drift')
    raw = c/'raw'
    require(json.loads((raw/'argv.json').read_text()) == ['/bin/sh','./driver.sh'], 'wrong actual invocation')
    require(float((raw/'end').read_text()) >= float((raw/'start').read_text()), 'missing/invalid times')
    trace = [json.loads(line) for line in (c/'trace.jsonl').read_text().splitlines()]
    require(not any('FORBIDDEN' in e['event'] for e in trace), 'unexpected process/device action')
    birth = [e for e in trace if e['event'] == 'birth' and e['pid'] == '42']
    want_rcs = ([0]*4+[1] if mode == 'first_missing' else
                [0]*5+[1] if mode.startswith('second_missing') else [0]*9)
    require([e['rc'] for e in birth] == want_rcs, 'required adjacent birth sequence not covered')
    require(all(e['value'] == ('200' if e['rc']==0 else '') for e in birth), 'numeric mismatch used in place of read failure')
    expected_disappear = 5 if mode == 'first_missing' else 6
    disappeared = [e for e in trace if e['event'] == 'fixture_disappeared']
    require(disappeared == ([] if mode == 'normal' else [{'event':'fixture_disappeared','after_stat':expected_disappear}]), 'fixture disappearance boundary not covered')
    reads = [e for e in trace if e['event'] == 'stat_read']
    count = 11 if mode == 'normal' else expected_disappear
    require(reads == [{'event':'stat_read','ordinal':i,'rc':0} for i in range(1,count+1)], 'unexpected stat reads')
    # Require the removal after the successful stat read, then success from the
    # in-flight rb_birth, then the next real rb_birth failure; not just counts.
    if mode != 'normal':
        pos = next(i for i,e in enumerate(trace) if e['event']=='fixture_disappeared')
        require(trace[pos-1] == {'event':'stat_read','ordinal':expected_disappear,'rc':0}, 'removal not bound to actual stat read')
        following = [e for e in trace[pos+1:] if e['event']=='birth' and e['pid']=='42']
        require([e['rc'] for e in following] == [0,1], 'failure not immediately after successful birth')
    state = (c/'state/state').read_text().strip()
    events = (c/'state/events.log').read_text()
    rc = int((raw/'rc').read_text())
    expected_rc, expected_state = (4,'RETRY_LIMIT') if mode=='first_missing' else (0,'UI_UNVERIFIED') if mode=='normal' else (5,'IO_FAILED') if mode=='second_missing_existing' and variant=='candidate' else (2,'OWNER_REFUSED')
    require((rc,state)==(expected_rc,expected_state), 'wrong main rc/state: '+str((variant,mode,rc,state)))
    require('transition_target=BOOTSTRAP' in events, 'main bootstrap not executed')
    if mode=='first_missing':
        require('reason=process_exit' in events and 'transition_target=RECOVERING' in events and 'transition_target=RETRY_LIMIT' in events, 'exit/recovery path absent')
        require('OWNER_REFUSED' not in events, 'exit incorrectly terminal refusal')
    elif mode=='normal':
        require('observation_limit_no_app_control' in events and any(e['event']=='capture_frame_seam' for e in trace), 'normal continuation absent')
    elif expected_rc==2:
        reason = 'child_owner_check_failed_no_signal' if variant=='candidate' else 'child_identity_changed_no_signal'
        require('transition_target=OWNER_REFUSED '+reason in events and 'reason=process_exit' not in events, 'terminal owner path absent')
    else:
        require('diagnostic_already_exists' in (raw/'stderr').read_text(), 'diagnostic collision not executed')
        require((c/'state/lock/owner').exists(), 'io_fail did not retain lock')
    diag = c/'state/guardian-refusal-1.jsonl'
    before = json.loads((c/'diagnostic-before.json').read_text())['sha256']
    after = sha(diag) if diag.exists() else None
    record = None
    if mode=='second_missing_existing':
        require(before == hashlib.sha256(OLD_BYTES).hexdigest() == after and diag.read_bytes()==OLD_BYTES, 'old diagnostic overwritten')
    else:
        require(before is None, 'unexpected historical diagnostic')
        if variant=='candidate' and mode=='second_missing':
            record=json.loads(diag.read_text())
            require(record=={'phase':'strict','pid':'42','birth':'200','field':'birth','actual':'<read-error-or-exited>','expected':'200'}, 'wrong refusal detail')
        else:
            require(after is None, 'unexpected diagnostic file')
    raw_hashes={n:{'sha256':sha(raw/n),'size':(raw/n).stat().st_size} for n in ('argv.json','start','end','stdout','stderr','rc')}
    return {'variant':variant,'case':mode,'rc':rc,'state':state,'birth_trace':birth,'diagnostic':record,
            'old_diagnostic_sha256':before,'final_diagnostic_sha256':after,'trace_sha256':sha(c/'trace.jsonl'),
            'events_sha256':sha(c/'state/events.log'),'raw':raw_hashes}

def validate(out, source_root):
    pin_sources(source_root)
    rows=[validate_case(out,source_root,v,m) for m in CASES for v in ('baseline','candidate')]
    return {'passed':True,'case_count':4,'executions':8,'source_pins':PINS,
            'fixture_sha256':sha(ROOT/'fixture.sh'),'rows':rows,
            'limit':'Synthetic monitor timing only; TT_MAX_ATTEMPTS=1, TT_MAX_POLLS=1; no T48 reclassification.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--sources',type=Path,default=ROOT);ap.add_argument('--verify-only',action='store_true')
    a=ap.parse_args();source=a.sources.resolve();out=a.out.resolve()
    pin_sources(source)
    if not a.verify_only:
        out.mkdir(parents=True,exist_ok=False)
        for mode in CASES:
            for variant in ('baseline','candidate'):
                run_case(out,source,variant,mode)
    result=validate(out,source)
    if not a.verify_only:
        (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':4,'executions':8,'verify_only':a.verify_only}))

if __name__=='__main__':
    main()
