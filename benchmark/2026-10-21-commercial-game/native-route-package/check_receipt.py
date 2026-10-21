#!/usr/bin/env python3
"""G27 package evidence check, not deployment admission."""
import argparse,copy,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def validate(b,p,rows,artifacts):
 if len(b)!=319 or len(p['expected'])!=319:raise ValueError('319 required')
 if p['baseline']!=b or p['additions'] or p['rollout_ready']:raise ValueError('baseline/unsigned state drift')
 changed={t for t,v in p['expected'].items() if b[t]!=v}
 if changed!={r['target'] for r in rows} or len(changed)!=5:raise ValueError('five exact targets required')
 if [sum(r['role']==k for r in rows) for k in ['host','anl','policy']]!=[1,2,2]:raise ValueError('role cardinality')
 for role in ['host','anl','policy']:
  if not artifacts.get(role):raise ValueError('candidate artifact not fixed: '+role)
  for r in rows:
   if r['role']==role and (r['candidate_sha256']!=artifacts[role] or p['expected'][r['target']]!=artifacts[role]):raise ValueError('alias/candidate mismatch')
 if len(p['changes'])!=35 or sum(b[r['target']]==r['sha256'] for r in p['changes'])!=30:raise ValueError('actual writes drift')
 for t in b:
  if '/74e6f759' in t and b[t]!=p['expected'][t]:raise ValueError('old route changed')
def check(private=False):
 load=lambda n:json.loads((D/n).read_text())
 b=load('baseline-319.json');p=load('transaction-plan.json');rows=load('five-targets.json');res=load('results.json');a={r['role']:r['candidate_sha256'] for r in rows};validate(b,p,rows,a)
 assert not res['rollout_ready'] and not res['deployable'] and res['g26_independent_accepted']
 assert res['device_calls']==res['builds']==0 and not res['owned_state_created']
 cases=0
 for kind in ['missing_host','alias_drift','old_route']:
  pp=copy.deepcopy(p);aa=dict(a)
  if kind=='missing_host':aa.pop('host')
  if kind=='alias_drift':pp['expected'][next(r['target'] for r in rows if r['role']=='anl')]='0'*64
  if kind=='old_route':pp['expected'][next(t for t in b if '/74e6f759' in t)]='0'*64
  try:validate(b,pp,rows,aa)
  except ValueError:cases+=1
  else:raise AssertionError(kind+' not refused')
 verified=0
 if (D/'manifest.json').exists():
  for f in load('manifest.json')['files']:assert sha(D/f['path'])==f['sha256'],f['path']
  for f in load('manifest.json').get('external_files',[]):assert sha(D.parents[2]/f['path'])==f['sha256'],f['path']
 if private:
  ws=D.parents[3];c=Path.home()/'.local/share/westlake/commercial-game-20261021'
  for f in load('evidence-index.json'):
   q=Path(f['path'].replace('$COMMERCIAL',str(c)).replace('$WORKSPACES',str(ws)))
   assert sha(q)==f['sha256'] and q.stat().st_size==f['bytes'],q;verified+=1
  for side in ['baseline','candidate']:
   root=D/'.private/assembly-02'/side;m=json.loads((root/'native/package.json').read_text())
   for n,h in m['files'].items():assert sha(root/'native'/n)==h;verified+=1
 return {'status':'PASS','scope':'unsigned package consistency, not original gate acceptance','targets':319,'logical_changes':5,'actual_writes':35,'negative_cases':cases,'raw_or_payload_hashes':verified,'rollout_ready':False}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--private',action='store_true');args=a.parse_args();print(json.dumps(check(args.private)))
