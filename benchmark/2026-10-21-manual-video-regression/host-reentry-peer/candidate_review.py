#!/usr/bin/env python3
"""Capture a new candidate SHA, audit real entry pins, and replay safety assertions.

Existing reviewed watchdog SHAs are refused before replay. All child executions are
local synthetic fixtures; production entry and author test programs never execute.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import assembly_audit
import replay
import replay_candidate

HERE=Path(__file__).resolve().parent
KNOWN=HERE/'reviewed-watchdogs.json'

def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value): path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def functions(path):
    text=path.read_text()
    return '\n'.join(re.findall(r'^\w+\(\)\s*\{[^\n]+\}$',text,re.M) +
                     re.findall(r'^\w+\(\)\s*\{[^\n}]*\n.*?^\}',text,re.M|re.S))

def choose(candidate,payload,expected=None):
    if payload:
        return payload/'watchdog.sh',payload/'reentry-common.sh',payload
    sources=candidate/'src'
    wd=sorted(sources.glob('watchdog-reentry-*.sh'))
    if expected:wd=[p for p in wd if p.is_file() and not p.is_symlink() and assembly_audit.digest(p)==expected]
    cm=sorted(sources.glob('reentry-common-*.sh'))
    if len(wd)!=1 or len(cm)!=1:
        raise ValueError('ambiguous/missing source: pass a unique assembled --payload')
    return wd[0],cm[0],None

def safety(row):
    """Assert required safe behavior, not the old defect's output string."""
    name=row['case'];output=row['stdout']
    if row['rc']!=0 or row['stderr'].strip(): return 'harness_error'
    results=[dict(re.findall(r'(\w+)=([^\s]*)',line)) for line in output.splitlines() if line.startswith('RESULT ')]
    if not results:return 'harness_error'
    last=results[-1]
    if row['kind']=='control':
        return 'pass' if row['expected_observation'] in output else 'fail'
    if name in ('missing_proc_root','missing_fd_directory','failed_fd_readlink','nonlistener_socket_row','malformed_owned_uid'):
        # Partial enumeration output is allowed ONLY with failure status; consumers check rc.
        return 'pass' if last.get('rc') not in (None,'0') else 'fail'
    if name=='recorded_run_inode_changed':
        return 'pass' if last.get('terms')=='0' and last.get('starts')=='0' else 'fail'
    if name in ('birth_read_failure_after_term','pid_reuse_after_term'):
        return 'pass' if last.get('rc') not in (None,'0') and last.get('terms')=='1' and last.get('unlinks')=='0' and last.get('starts')=='0' else 'fail'
    if name in ('malformed_proc_stat','newhost_owned_enum_failure'):
        return 'pass' if all(last.get(x)=='0' for x in ('terms','unlinks','starts')) and 'spawns=1' not in output else 'fail'
    return 'harness_error'

def replay_new(snapshot,out):
    # Only function definitions enter the fixture: no boot/entry/top-level author code.
    w=functions(snapshot/'watchdog-reentry-r4.sh')
    dependencies=re.findall(r'^\. "\$HERE/([A-Za-z0-9_.-]+)"',(snapshot/'watchdog-reentry-r4.sh').read_text(),re.M)
    helpers='\n'.join(functions(snapshot/name) for name in dependencies
                      if name not in ('reentry-common.sh','reentry-seams.sh'))
    prod=helpers+'\n'+w+'\n'+functions(snapshot/'reentry-common-r4.sh')+'\n'+(snapshot/'reentry-seams.sh').read_text()
    rows=[]
    cases=list(replay_candidate.CASES)
    if 'rc_record_bootstrap_epoch()' in w:
        cases += [
          ('malformed_owned_uid','rc_owned_pids_strict',
           'for pid in "$$" 5177; do echo "Uid: 0 0 0 0" > "$PROC/$pid/status"; done; mkdir -p "$PROC/9000"; echo "Uid: 20011206 20011206 20011206" > "$PROC/9000/status"; found=$(rc_owned_pids_strict); echo RESULT rc=$? owned=$found',
           'RESULT rc=0 owned=','counterexample'),
          ('recorded_run_inode_changed','parent_owned',
           'run_inode=20; readlink() { case "$1" in */exe) echo /data/local/tmp/asx/appspawn-x;; */1/ns/mnt) echo "mnt:[1]";; *) command readlink "$1";; esac; }; rb_uid() { echo 0:0:0:0; }; sha256sum() { echo "$RB_SPAWNER_SHA  fixture"; }; stat() { case "$*" in *run.sh*) echo "1:$run_inode";; *) echo 1:20;; esac; }; rc_record_bootstrap_epoch; before=$(cat "$F/parent-epoch"); run_inode=21; rc_parent_epoch_switch 31; r=$?; echo BEFORE "$before"; summary',
           'rc=0 terms=1 unlinks=1 starts=1','counterexample'),
        ]
    for name,restore,body,expected,kind in cases:
        restored=''
        if restore:
            found=re.search(r'^'+restore+r'\(\)\s*\{[^\n]*\n.*?^\}',w,re.M|re.S)
            if not found:
                rows.append(dict(case=name,safety_verdict='harness_error',reason='production interface changed: '+restore));continue
            restored=found.group(0)
        adapter=''
        if 'rc_record_bootstrap_epoch()' in w:
            adapter=(HERE/'epoch_fixture.sh').read_text()
            body=body.replace('starts=$((starts+1)); echo 9090 > "$1";', 'fixture_start 9090 "$1";')
        script=prod+'\n'+replay.SETUP+'\n'+replay_candidate.EXTRA+'\n'+adapter+'\n'+restored+'\n'+body+'\n'
        # Block every unanticipated signal as well as recording the intended seam.
        script=script.replace(replay_candidate.EXTRA,replay_candidate.EXTRA+'\nkill() { echo UNEXPECTED_DIRECT_SIGNAL >&2; return 99; }\n')
        with tempfile.TemporaryDirectory(prefix='t37-new-sha-') as td:
            root=Path(td);(root/'case.sh').write_text(script)
            proc=subprocess.run(['/bin/sh','case.sh','fixture'],cwd=root,capture_output=True,text=True,timeout=10)
        row=dict(case=name,kind=kind,rc=proc.returncode,stdout=proc.stdout,stderr=proc.stderr,
                 expected_observation=expected,script_sha256=sha(script.encode()))
        row['safety_verdict']=safety(row)
        row['historical_observation_matches']=proc.returncode==0 and expected in proc.stdout
        (out/(name+'.sh')).write_text(script)
        write(out/(row['case']+'.receipt.json'),row)
        rows.append(row)
    report=dict(schema='t37-new-candidate-safety/v2',cases=rows,source_pins=json.loads((snapshot/'pins.json').read_text()),
                passed=all(x['safety_verdict']=='pass' for x in rows),candidate_accepted=False,
                scope='Production functions with disclosed synthetic OS seams. Controls must execute successfully; refusal-only is insufficient. No deployment acceptance.')
    write(out/'results.json',report)
    return report

def capture(candidate,payload,baseline,expected,out):
    wd,common,payload=choose(candidate,payload,expected)
    selected={'watchdog-reentry-r4.sh':wd,'reentry-common-r4.sh':common}
    helper_root=payload or baseline
    for path in sorted(helper_root.glob('*.sh')):
        if path.name not in ('watchdog.sh','reentry-common.sh'):
            selected[path.name]=path
    if payload is None:
        for path in sorted((candidate/'src').glob('*.sh')):
            if path not in (wd,common) and not path.name.startswith(('watchdog-reentry-','reentry-common-')):selected[path.name]=path
    else:
        for name in ('members.tsv','startup.env','startup.expected.sha256'):
            selected[name]=payload/name
        selected['package-MANIFEST.sha256']=payload.parent/'MANIFEST.sha256'
    for name in ('reentry-seams.sh','route-b-owner.sh','exit-verdict.sh'):
        if name not in selected:raise ValueError('missing helper '+name)
    data={}
    for name,path in selected.items():
        if path.is_symlink() or not path.is_file():raise ValueError('missing/symlink source: '+name)
        data[name]=path.read_bytes()
    observed=sha(data['watchdog-reentry-r4.sh'])
    if observed!=expected:raise ValueError('watchdog SHA mismatch; expected '+expected+' observed '+observed)
    known=json.loads(KNOWN.read_text()) if KNOWN.exists() else {}
    if observed in known:
        return dict(status='already_reviewed_no_replay',watchdog_sha256=observed,reference=known[observed])
    assembly=assembly_audit.audit(payload,observed,sha(data['reentry-common-r4.sh']))
    out.mkdir(parents=True,exist_ok=False)
    snap=out/'snapshot';snap.mkdir()
    files=[]
    for name,content in data.items():
        (snap/name).write_bytes(content)
        files.append(dict(path=name,sha256=sha(content),bytes=len(content)))
    pins=dict(observed_at=datetime.now(timezone.utc).isoformat(),files=files,watchdog_sha256=observed,
              assembly_mode='complete_payload' if payload else 'source_only_with_explicit_baseline_helpers',
              source_unchanged=all(p.read_bytes()==data[n] for n,p in selected.items()))
    if payload:
        pins['assembly_unchanged']=assembly==assembly_audit.audit(payload,observed,sha(data['reentry-common-r4.sh']))
        pins['source_unchanged']=pins['source_unchanged'] and pins['assembly_unchanged']
    write(snap/'pins.json',pins);write(out/'assembly.json',assembly)
    if not pins['source_unchanged']:raise ValueError('source changed during capture; do not replay mixed revision')
    return dict(status='captured',snapshot=snap,pins=pins,assembly=assembly)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--payload',type=Path)
    ap.add_argument('--baseline-payload',type=Path,default=replay.BASE)
    ap.add_argument('--expect-watchdog-sha',required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--assembly-only',action='store_true',help='Audit a final package without re-executing reviewed functions')
    a=ap.parse_args()
    if not re.fullmatch(r'[0-9a-f]{64}',a.expect_watchdog_sha):ap.error('exact 64-character SHA required')
    try:
        if a.assembly_only:
            wd,common,payload=choose(a.candidate,a.payload,a.expect_watchdog_sha)
            if assembly_audit.digest(wd)!=a.expect_watchdog_sha:raise ValueError('watchdog SHA mismatch')
            report=assembly_audit.audit(payload,a.expect_watchdog_sha,assembly_audit.digest(common))
            a.out.mkdir(parents=True,exist_ok=False);write(a.out/'assembly.json',report)
            print(json.dumps(report,ensure_ascii=False));return 0 if report['passed'] else 1
        result=capture(a.candidate,a.payload,a.baseline_payload,a.expect_watchdog_sha,a.out)
        if result['status']!='captured':print(json.dumps(result,ensure_ascii=False));return 3
        # Replay parser helper must come from this capture, never silently from r3.
        old_base=replay.BASE;replay.BASE=result['snapshot']
        try:
            dest=a.out/'replay';dest.mkdir();report=replay_new(result['snapshot'],dest)
        finally:replay.BASE=old_base
        summary=dict(status='review_required',watchdog_sha256=a.expect_watchdog_sha,
                     safety_passed=report['passed'],assembly_passed=result['assembly']['passed'],
                     counts={v:sum(x['safety_verdict']==v for x in report['cases']) for v in ('pass','fail','harness_error')},
                     candidate_accepted=False,manual_video='pending',device_access=False,
                     limitations=['Entry audit is static. Exact parent signal authority, socket creation provenance and race exclusion still require independent source review.'])
        write(a.out/'summary.json',summary);print(json.dumps(summary,indent=2));return 0 if report['passed'] and result['assembly']['passed'] else 1
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(status='refused',error=str(exc))));return 2

if __name__=='__main__':raise SystemExit(main())
