#!/usr/bin/env python3
"""Compose immutable t10 plus an explicitly pinned ARM classifier, offline/disabled."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re

D=Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def compose(base, plan, plan_sha, worker_preimage, worker_sha, classifier, classifier_sha, out):
    classifier=Path(classifier).resolve();out=Path(out).resolve()
    if not re.fullmatch('[0-9a-f]{64}',classifier_sha) or sha(classifier)!=classifier_sha:
        raise ValueError('explicit classifier SHA mismatch')
    data=classifier.read_bytes()
    if len(data)<20 or data[:6]!=b'\x7fELF\x02\x01' or int.from_bytes(data[18:20],'little')!=183:
        raise ValueError('classifier must be the pinned ELF64 little-endian AArch64 artifact')
    original=json.loads(Path(plan).read_text())
    if len(original['members'])!=24 or len({m['target'] for m in original['members']})!=24:
        raise ValueError('exact current 24-member base required')
    gates=[m for m in original['members'] if m['target'].endswith('/screen-gate') and '/recovery-attempts/' in m['target']]
    if len(gates)!=1 or gates[0]['source']!='$PACKAGE/payload/screen-gate-feed':
        raise ValueError('exact existing classifier member required; no new scope')
    spec=importlib.util.spec_from_file_location('frozen_t10_compose',D.parent/'compose.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    result=frozen.compose(base,plan,plan_sha,worker_preimage,worker_sha,out)
    payload=out/'payload';(payload/'screen-gate-feed').write_bytes(data)
    manifest=payload/'members.tsv';rows=[]
    for line in manifest.read_text().splitlines():
        digest,name,mode=line.split()
        if name=='screen-gate':digest=classifier_sha
        rows.append(f'{digest} {name} {mode}')
    if sum(line.split()[1]=='screen-gate' for line in rows)!=1:
        raise ValueError('exact existing boot classifier member required')
    manifest.write_text('\n'.join(rows)+'\n')
    policy=payload/'startup.env';text=policy.read_text()
    for field,value in [('STARTUP_DECODER_SHA',classifier_sha),('STARTUP_MEMBERS_SHA',sha(manifest))]:
        text,n=re.subn(r'^'+field+r"='[^']*'",field+'='+repr(value),text,flags=re.M)
        if n!=1:raise ValueError('exact startup binding absent or duplicate: '+field)
    policy.write_text(text);(payload/'startup.expected.sha256').write_text(sha(policy)+'\n')
    output_plan=out/'plan.disabled.json';final=json.loads(output_plan.read_text())
    # Frozen worker composition validates the separate target pin; preserve the
    # current base plan's exact before object instead of inserting that target
    # again inside before. All real preimage fields must still agree.
    for before,after in zip(original['members'],final['members']):
        if before['target'].endswith('/readiness-probe.sh'):
            measured={k:v for k,v in after['before'].items() if k!='target'}
            if measured!=before['before']:raise ValueError('current worker preimage differs from base plan')
            after['before']=before['before']
    for member in final['members']:
        member['sha256']=sha(out/member['source'].removeprefix('$PACKAGE/'))
    final['execution_enabled']=False
    # Only member SHA values and explicit proven worker before may differ.
    for before,after in zip(original['members'],final['members']):
        for field in set(before)|set(after):
            if field=='sha256':continue
            if before.get(field)!=after.get(field):raise ValueError('base member scope/metadata changed: '+before['target']+'/'+field)
    output_plan.write_text(json.dumps(final,indent=2)+'\n')
    inventory=[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size}
               for p in sorted(out.rglob('*')) if p.is_file() and p.name!='composition.json']
    receipt={'schema':'t10-classifier-composition/v1','base_plan_sha256':plan_sha,
             'worker_preimage_sha256':worker_sha,'classifier_sha256':classifier_sha,
             't10_watchdog_sha256':sha(payload/'watchdog.sh'),'files':inventory,
             'members':24,'execution_enabled':False,'device_calls':0,
             'admission':'none; requires separate outer review and fresh authorization'}
    (out/'composition.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return {**result,'plan_sha256':sha(output_plan),'composition_sha256':sha(out/'composition.json'),
            'classifier_sha256':classifier_sha,'execution_enabled':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','base-plan','base-plan-sha256','worker-preimage','worker-preimage-sha256',
                 'classifier','classifier-sha256','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args()
    try:print(json.dumps(compose(a.base,a.base_plan,a.base_plan_sha256,a.worker_preimage,
                                a.worker_preimage_sha256,a.classifier,a.classifier_sha256,a.out)))
    except (ValueError,OSError,KeyError,TypeError) as e:raise SystemExit('COMPOSITION REJECT: '+str(e))
