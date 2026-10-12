#!/usr/bin/env python3
"""Local source validation and disabled5cd t9 binding; no board access."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
WS=HERE.parents[3]
MAIN=WS/'westlake-harness'
E=MAIN/'benchmark/2026-10-12-v1-seal-execution'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':'$WORKSPACES/'+str(p.relative_to(WS)), 'sha256':sha(p)}
def read(p):return json.loads(p.read_text())
def write(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2);f.write('\n')
def main():
 b=read(HERE.parent/'restore-v3/binding.5cd.disabled.json')
 assert b['startup_enabled'] is False and b['serial'].startswith('5cd')
 b.pop('exe_alias_manifest',None)
 package=E/'readiness-package'
 b['control_source']={'plan':ref(package/'plan.enabled.json'),'composition':ref(package/'composition.json'),
   'base_plan':ref(E/'inputs/readiness-base-plan.json'),'worker_preimage':ref(E/'inputs/readiness-worker-preimage.json')}
 donor=read(package/'plan.enabled.json');worker=next(r for r in donor['members'] if r['target'].endswith('/readiness-probe.sh'))
 # Do not project the donor61b worker absence. Verify actual target ancestor proof.
 raw=E/'restore-5cd-preimages/028-directories.stdout';record=raw.with_suffix('.json');j=read(record)
 text=raw.read_text().replace('\r','');lines=text.splitlines();root=b['attempt_root']
 assert j['exit']==0 and j['argv'][2]==b['serial'] and j['stdout_sha256']==sha(raw) and lines[-1]=='RE_REMOTE_RC=0'
 assert lines.count('PATH='+root)==1 and lines[lines.index('PATH='+root)+1]=='ABSENT'
 pre=read(E/'restore-5cd-preimages/results.json');assert pre['stable'] and pre['serial']==b['serial'] and pre['boot_id']==b['boot_id']
 target=root+'/readiness-probe.sh'
 b['before'][target]={'exists':False,'proof':'5cd actual candidate ancestor absent; no61b preimage reuse',
   'ancestor':root,'evidence':{'record':ref(record),'stdout':ref(raw),'summary':ref(E/'restore-5cd-preimages/results.json')}}
 b['after'][target]=worker['after']
 # The three unchanged guardian programs must match the explicitly landed commit.
 provenance=[]
 for name in ('watchdog.sh','route-b-owner.sh','readiness-probe.sh'):
  source='benchmark/2026-10-12-child-readiness/candidate/'+name
  blob=subprocess.check_output(['git','show','ee50b0cd6c:'+source],cwd=MAIN)
  assert hashlib.sha256(blob).hexdigest()==sha(package/'payload'/name)
  provenance.append({'commit':'ee50b0cd6c','path':source,'sha256':sha(package/'payload'/name)})
 b['observation_provenance']['t9_guardian']=provenance
 b['observation_provenance']['control_after_policy']=ref(package/'plan.enabled.json')
 write(HERE/'binding.5cd.disabled.json',b)
 write(HERE/'source-control-audit.json',{'controls':len(donor['members']),'source':b['control_source'],
  'guardian_commit_pins':provenance,'target_worker_preimage':b['before'][target],
  'no_donor_authorization_copied':True,'device_calls':0})
 print('DISABLED_BINDING: 24controls +460runtime +3stage =487; readiness target ancestor absence measured on5cd')
if __name__=='__main__':main()
