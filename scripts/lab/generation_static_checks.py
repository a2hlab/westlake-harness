#!/usr/bin/env python3
"""Compare changed final artifacts with effective deployed members, never underlays.

Runs deployed_class_diff --frozen for every changed DEX JAR, and open_site_scan
for both versions of every changed ELF. New/removed open sites and namespace
changes remain explicit review items; scans do not constitute an approval.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import generation_bundle as bundle


def effective(root):
    from u7_executor import effective_files
    data, manifest, _ = bundle.validate(root)
    rows = effective_files(manifest, data['native']['directory']+'/')
    rows.update({r['target']:r for r in data['boot_group']['members']+[data['runtime_jar']]})
    return rows


def signature(site):
    # PCs shift on relink; function + arguments + occurrence count define a site.
    return json.dumps({k:site[k] for k in ('function','callee','namespace','path','flags','tail_call')},sort_keys=True)


def site_delta(old, new):
    a,b=Counter(map(signature,old)),Counter(map(signature,new))
    return dict(added=[json.loads(s) for s,n in sorted((b-a).items()) for _ in range(n)],
                removed=[json.loads(s) for s,n in sorted((a-b).items()) for _ in range(n)])


def command(argv):
    proc=subprocess.run(argv,text=True,capture_output=True,timeout=180)
    return dict(exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr)


def scan(elf):
    with tempfile.TemporaryDirectory(prefix='open-site-gate-') as td:
        output=Path(td)/'scan.json'
        result=command([sys.executable,str(Path(__file__).with_name('open_site_scan.py')),str(elf),'--json',str(output)])
        if result['exit_code'] or not output.is_file():raise RuntimeError('open-site scan failed: '+result['stderr'])
        data=json.loads(output.read_text())
        if len(data['binaries'])!=1:raise RuntimeError('unexpected open-site scan output')
        import abi_diff
        calls=abi_diff.call_sets(elf)
        data['namespace_api_calls']={fn:sorted(c for c in values if 'dlns_' in c)
                                     for fn,values in calls.items() if any('dlns_' in c for c in values)}
        import re
        # Include configuration literals: inherit allowlists can change without adding a call.
        data['namespace_literals']=sorted({x.decode('ascii') for x in re.findall(rb'[ -~]{4,}',Path(elf).read_bytes())
            if b'westlake.' in x or (b'.so:' in x and b'lib' in x)})
        return data


def check(root, baseline, policy=None):
    root,baseline=Path(root).resolve(),Path(baseline).resolve()
    policy=policy or {}
    old,new=effective(baseline),effective(root)
    rows=[];cache={}
    for target,row in sorted(new.items()):
        previous=old.get(target)
        if previous and previous['sha256']==row['sha256']:continue
        candidate=bundle.member(root,row)
        # ART images/OAT are covered by G1/G2 and the paired bake receipt, not ELF-native namespace scans.
        if candidate.suffix in ('.art','.oat','.vdex'):continue
        deployed=bundle.member(baseline,previous) if previous else None
        if candidate.suffix!='.jar' and candidate.read_bytes()[:4]!=b'\x7fELF':continue
        item=dict(target=target,candidate_sha256=row['sha256'],deployed_sha256=previous['sha256'] if previous else None)
        if deployed is None:
            item.update(status='REJECT',reason='new native/JAR member has no deployed baseline for this promotion')
        elif candidate.suffix=='.jar':
            allowance=policy.get('jars',{}).get(target,{})
            argv=[sys.executable,str(Path(__file__).with_name('deployed_class_diff.py')),str(candidate),'--deployed',str(deployed),'--frozen']
            for key,flag in [('allow_add','--allow-add'),('allow_drop','--allow-drop'),('allow_reshape','--allow-reshape')]:
                if allowance.get(key):argv += [flag]+allowance[key]
            result=command(argv)
            # A missing DEX / failed dexdump must not become an empty-set PASS.
            import deployed_class_diff as dcd
            nonempty=bool(dcd.classes(candidate)) and bool(dcd.classes(deployed))
            item.update(kind='DEX-JAR',check=result,status='PASS' if result['exit_code']==0 and nonempty else 'REJECT',frozen=True,nonempty_dex=nonempty)
        else:
            key=(previous['sha256'],row['sha256'])
            if key not in cache:
                a,c=scan(deployed),scan(candidate)
                delta=site_delta(a['binaries'][0]['sites'],c['binaries'][0]['sites'])
                delta['namespace_api_changes']={fn:dict(deployed=a['namespace_api_calls'].get(fn,[]),candidate=c['namespace_api_calls'].get(fn,[]))
                    for fn in sorted(a['namespace_api_calls'].keys()|c['namespace_api_calls'].keys())
                    if a['namespace_api_calls'].get(fn)!=c['namespace_api_calls'].get(fn)}
                delta['namespace_literal_changes']=dict(added=sorted(set(c['namespace_literals'])-set(a['namespace_literals'])),removed=sorted(set(a['namespace_literals'])-set(c['namespace_literals'])))
                cache[key]=dict(deployed_scan=a,candidate_scan=c,open_site_delta=delta,delta_sha256=bundle.digest(delta))
            item.update(kind='ELF',**cache[key])
            allowance=policy.get('native',{}).get(target,{})
            delta=item['open_site_delta']
            changed=bool(delta['added'] or delta['removed'] or delta['namespace_api_changes'] or
                         any(delta['namespace_literal_changes'].values()))
            approved=(allowance.get('candidate_sha256')==row['sha256'] and
                      allowance.get('deployed_sha256')==previous['sha256'] and
                      allowance.get('delta_sha256')==item['delta_sha256'] and
                      allowance.get('approved_by')=='outer(claude)' and allowance.get('evidence'))
            item.update(status='REVIEW_REQUIRED' if changed and not approved else 'PASS',review=allowance if approved else None,
                        namespace_changes_included=True)
        rows.append(item)
    return dict(schema='westlake-generation-static-checks/v1',bundle_sha256=bundle.sha(root/'bundle.json'),
                baseline_bundle_sha256=bundle.sha(baseline/'bundle.json'),policy_sha256=bundle.digest(policy),
                status='PASS' if all(r['status']=='PASS' for r in rows) else 'REJECT',members=rows,
                changed_jars=sum(r.get('kind')=='DEX-JAR' for r in rows),changed_native_paths=sum(r.get('kind')=='ELF' for r in rows))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--policy',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();policy=json.loads(args.policy.read_text()) if args.policy else None
    report=check(args.package,args.baseline,policy)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','changed_jars','changed_native_paths')}))
    return 0 if report['status']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())
