#!/usr/bin/env python3
"""Offline target coverage using the unchanged U7 effective_files implementation."""
import argparse, hashlib, json, re, sys
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, obj): p.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')
def fingerprint(p):
    out={}
    for line in p.read_text().splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})\s+(/.+)',line)
        if not m: raise ValueError('Invalid fingerprint line')
        if m[2] in out: raise ValueError('Duplicate target')
        out[m[2]]=m[1]
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--main',type=Path,required=True); ap.add_argument('--base',type=Path,required=True); ap.add_argument('--evidence',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    sys.path.insert(0,str(a.main/'scripts/lab')); import u7_executor as u7
    b=json.loads((a.base/'bundle.json').read_text()); m=json.loads((a.base/'native/package.json').read_text())
    effective=u7.effective_files(m)
    old={t:r['sha256'] for t,r in effective.items()}; old.update(m['prerequisites']); old.update({r['target']:r['sha256'] for r in b['boot_group']['members']+[b['runtime_jar']]})
    full=a.evidence/'outer-full-baseline-01'; report=json.loads((full/'results.json').read_text()); observed={}
    for i in range(9):
        values=fingerprint_raw(full/f'hashes-{i}.stdout')
        for t,h in values.items():
            if t in observed and observed[t]!=h: raise ValueError('Conflicting batch SHA')
            observed[t]=h
    if observed!=report['observed'] or report['missing'] or any(str(rc)!='0' for rc in report['remote_rc']): raise ValueError('Full baseline report mismatch')
    fp=a.evidence/'outer-fingerprint-01'; refs={k:fingerprint(fp/'fingerprints'/f'{n}-fingerprint.txt') for k,n in [('runtime','runtime'),('boot','boot-image')]}
    boot=(full/'boot-before.stdout').read_text().strip()
    for p in [full/'boot-after.stdout',fp/'before-boot.stdout',fp/'after-boot.stdout',a.evidence/'outer-readonly-01/boot-before.stdout',a.evidence/'outer-readonly-01/boot-after.stdout']:
        if p.read_text().strip()!=boot: raise ValueError('Boot disagreement')
    for v in refs.values():
        for t,h in v.items():
            if t in observed and observed[t]!=h: raise ValueError('Current receipts disagree: '+t)
            observed[t]=h
    targets=set(old).union(*[set(v) for v in refs.values()]); missing=sorted(targets-set(observed))
    overlays=[]
    for line in (a.evidence/'outer-readonly-01/mountinfo.stdout').read_text().splitlines():
        f=line.split()
        if 'boat-v2-20261013-r4/' in f[3]: overlays.append({'mount_id':f[0],'root':f[3],'target':f[4],'sha256':observed.get(f[4]),'in_u7_target_table':f[4] in targets})
    rows=[{'target':t,'old_package_sha256':old.get(t),'observed_sha256':observed.get(t),'reference_only':t not in old,'native_source':effective.get(t,{}).get('source')} for t in sorted(targets)]
    a.out.mkdir(parents=True,exist_ok=True); save(a.out/'target-coverage.json',{'boot':boot,'old_package_targets':len(old),'reference_union_targets':len(targets),'observed_targets':len(set(observed)&targets),'missing':missing,'differences':[r for r in rows if r['old_package_sha256'] and r['old_package_sha256']!=r['observed_sha256']],'rows':rows,'boat_r4_mounts':overlays,'device_io':False})
    (a.out/'missing-targets.txt').write_text(''.join(t+'\n' for t in missing))
    save(a.out/'next-reads.json',{'execution_enabled':False,'serial':'5ea34a45','missing_u7_targets':missing,'argv':[['hdc','-t','5ea34a45','shell','sha256sum',*missing]] if missing else [],'boat_private_targets_outside_u7':[r['target'] for r in overlays if not r['in_u7_target_table']]})
    pins={}
    for directory in [full,fp,a.evidence/'outer-readonly-01']:
        for p in sorted(directory.rglob('*')):
            if p.is_file(): pins['$HOME/.local/share/westlake/commercial-game-20261021/loader-deployment-admission/'+str(p.relative_to(a.evidence))]={'sha256':sha(p),'size':p.stat().st_size}
    pins['$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4/bundle.json']={'sha256':sha(a.base/'bundle.json')}
    pins['$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4/native/package.json']={'sha256':sha(a.base/'native/package.json')}
    save(a.out/'input-pins.json',pins)
    print(json.dumps({'old_package_targets':len(old),'reference_union_targets':len(targets),'covered':len(targets&set(observed)),'missing':missing,'differences':len([r for r in rows if r['old_package_sha256'] and r['old_package_sha256']!=r['observed_sha256']]),'boat_extra_targets':sum(not r['in_u7_target_table'] for r in overlays)}))

def fingerprint_raw(p):
    out={}
    for line in p.read_text().splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})\s+(/.+)',line)
        if m: out[m[2]]=m[1]
    return out
if __name__=='__main__': main()
