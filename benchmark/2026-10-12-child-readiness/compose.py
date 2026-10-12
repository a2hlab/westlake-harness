#!/usr/bin/env python3
"""Offline composition from an explicitly pinned real base plan; no devices.
Copies into a NEW package, preserves base startup values, inserts the worker in
plan+boot member manifest, refreshes all digests. Never signs/enables deployment.
The new worker's exact preimage/absence evidence must be supplied by outer.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,re
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def compose(base,planpath,plansha,preimage,preimagesha,out):
 base=Path(base).resolve();planpath=Path(planpath).resolve();out=Path(out).resolve()
 if sha(planpath)!=plansha or sha(preimage)!=preimagesha:raise ValueError('explicit input pin mismatch')
 if out.exists() or out.is_relative_to(base):raise ValueError('new independent output required')
 plan=json.loads(planpath.read_text());before=json.loads(Path(preimage).read_text())
 def member(name):
  hits=[m for m in plan['members'] if m['target'].endswith('/'+name) and '/recovery-attempts/' in m['target']]
  if len(hits)!=1:raise ValueError('ambiguous actual attempt member '+name)
  return hits[0]
 root=str(Path(member('watchdog.sh')['target']).parent);target=root+'/readiness-probe.sh'
 if before.get('target')!=target or type(before.get('exists')) is not bool:raise ValueError('new worker preimage target/status missing')
 if before['exists'] or not before.get('proof'):raise ValueError('only proven new worker absence allowed')
 # Verify every original payload source before copying, no speculative template.
 sources={}
 for m in plan['members']:
  if not m['source'].startswith('$PACKAGE/'):raise ValueError('nonlocal base member source')
  suffix=m['source'].removeprefix('$PACKAGE/');p=base/suffix
  if sha(p)!=m['sha256']:raise ValueError('base member drift '+m['target'])
  sources[suffix]=p
 out.mkdir();(out/'payload').mkdir()
 for suffix,p in sources.items():
  q=out/suffix;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 shutil.copyfile(base/'executor.py',out/'executor.py')
 for name in ('watchdog.sh','route-b-owner.sh','readiness-probe.sh'):
  shutil.copyfile(D/'candidate'/name,out/'payload'/name)
 entry=out/'payload/entry.sh';text=entry.read_text()
 for name in ('watchdog.sh','route-b-owner.sh'):
  old=member(name)['sha256']
  if text.count(old)!=1:raise ValueError('actual entry old pin not unique '+name)
  text=text.replace(old,sha(out/'payload'/name))
 entry.write_text(text)
 manifest=out/'payload/members.tsv';lines=[]
 mapping={'start-parent.sh':'start-parent-prepared.sh','spawn.sh':'spawn-prepared.sh','screen-gate':'screen-gate-feed'}
 for line in manifest.read_text().splitlines():
  _,name,mode=line.split();lines.append(sha(out/'payload'/mapping.get(name,name))+' '+name+' '+mode)
 lines.append(sha(out/'payload/readiness-probe.sh')+' readiness-probe.sh 550');manifest.write_text('\n'.join(lines)+'\n')
 policy=out/'payload/startup.env';text=policy.read_text();text,n=re.subn(r"^STARTUP_MEMBERS_SHA='[^']*'",'STARTUP_MEMBERS_SHA='+repr(sha(manifest)),text,flags=re.M)
 if n!=1:raise ValueError('actual startup member pin missing')
 policy.write_text(text);(out/'payload/startup.expected.sha256').write_text(sha(policy)+'\n')
 new=dict(member('watchdog.sh'));new.update(source='$PACKAGE/payload/readiness-probe.sh',target=target,before=before)
 plan['members'].append(new)
 for m in plan['members']:m['sha256']=sha(out/m['source'].removeprefix('$PACKAGE/'))
 plan['execution_enabled']=False
 (out/'plan.disabled.json').write_text(json.dumps(plan,indent=2)+'\n')
 files=[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file()]
 (out/'composition.json').write_text(json.dumps({'schema':'child-readiness-composition/v1','base_plan_sha256':plansha,'preimage_sha256':preimagesha,'files':files,'execution_enabled':False,'device_calls':0},indent=2)+'\n')
 return {'members':len(plan['members']),'worker_target':target,'plan_sha256':sha(out/'plan.disabled.json'),'device_calls':0,'execution_enabled':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',required=True);p.add_argument('--base-plan',required=True);p.add_argument('--base-plan-sha256',required=True);p.add_argument('--worker-preimage',required=True);p.add_argument('--worker-preimage-sha256',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 try:print(json.dumps(compose(a.base,a.base_plan,a.base_plan_sha256,a.worker_preimage,a.worker_preimage_sha256,a.out)))
 except (OSError,ValueError,KeyError,TypeError) as e:raise SystemExit('COMPOSITION REJECT: '+str(e))
