"""Disabled-reviewed Stage A: one journal transaction, always restore U10.1T8."""
import argparse,json,os,subprocess,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb,u7_executor as u,lab_paths
M=lab_paths.harness()
def composition():return json.loads((H/'composition.json').read_text())
def path(name):return Path(os.path.expandvars(name.replace('$WORKSPACES',str(W))))
def admission(plan):
 c=composition();b=json.loads((path(c['package'])/'bundle.json').read_text())
 assert plan.get('execution_enabled') is True,'U12 plan not enabled by outer'
 assert c.get('rollout_ready') is True and b.get('rollout_ready') is True,'U12 is not armed'
 assert gb.sha(path(c['package'])/'bundle.json')==c['bundle_sha256']==plan['bundle_sha256'],'bundle drift'
 assert gb.sha(path(c['package'])/'native/package.json')==c['native_manifest_sha256']==plan['package_manifest_sha256'],'manifest drift'
 review=json.loads((H/'admission.json').read_text())
 assert review.get('approved_by')=='outer(claude)' and review.get('status')=='approved','outer window admission absent'
 assert review.get('bundle_sha256')==c['bundle_sha256'] and review.get('native_manifest_sha256')==c['native_manifest_sha256'],'outer admission belongs to another bundle'
 assert plan['phase']=='A' and plan['restore']['state']=='U10.1T8' and plan['restore']['unconditional'],'wrong observation semantics'
def vm(command):
 return subprocess.run(['orb','-m','a2hlab','env','WORKSPACES='+str(W),'MAC_HOME='+os.environ.get('MAC_HOME',str(Path.home())),'LAB_HOME='+os.environ['LAB_HOME'],*map(str,command)],check=True)
def verify(serial,root,candidate=False,process_view=True):
 if sys.platform=='darwin':
  return vm(['python3',Path(__file__).resolve(),'--verify-candidate' if candidate else '--verify-base','--serial',serial,'--root',root])
 c=composition();row=c['candidate_boards'][serial] if candidate else json.loads((H/'recovery-u101t8.json').read_text())['boards'][serial]
 root.mkdir(parents=True,exist_ok=True);io=u.DeviceIO(serial,'cx-t0',root/'device')
 got,absent=io.snapshot(sorted(row['expected']));diff={p:{'expected':v,'actual':got.get(p)} for p,v in row['expected'].items() if got.get(p)!=v}
 refs=c['candidate_boards'][serial]['reference_paths']
 if not candidate:refs={'runtime':[p for p in refs['runtime'] if p in row['expected']],'boot':refs['boot']}
 fp=u.fingerprints(got,refs) if not absent else None
 report={'state':'U12' if candidate else 'U10.1T8','identity_assertions':row['identity_assertions'],'unique_paths':len(got),'diff':diff,'absent':absent,'fingerprints':fp,'boot_id':io.boot}
 (root/'identity.json').write_text(json.dumps(report,indent=2)+'\n')
 assert not diff and not absent and fp==row['fingerprints'],'identity/fingerprint mismatch'
 if process_view:
  generation=gb.validate(path(c['package'] if candidate else c['base_bundle']))[1]['generation']
  view=io.verify(row['expected'],generation);(root/'process-view.json').write_text(json.dumps(view,indent=2)+'\n')
 return report
def executor(serial,root,rollback=False):
 c=composition();command=['bash',M/'benchmark/2026-10-01-u7-executor/board61b/run-executor.sh','--rollback' if rollback else '--apply','--serial',serial,'--lane','cx-t0','--journal',root/'transaction/journal.json','--out',root/('rollback-'+uuid.uuid4().hex+'.json' if rollback else 'apply.json')]
 if not rollback:command += ['--package',path(c['package']),'--baseline-native',path(c['base_bundle'])/'native','--oatdump',M/'scripts/lab/oatdump_remote.sh']
 return vm(command)
def apply(serial,root,plan):
 admission(plan);root.mkdir(parents=True,exist_ok=True);assert not (root/'transaction/journal.json').exists(),'fresh output required'
 verify(serial,root/'baseline');executor(serial,root);verify(serial,root/'post-apply',True)
def finish(serial,root,restored_spec):
 # No successful run/signoff can retain a Stage A overlay.
 journal=root/'transaction/journal.json'
 if journal.exists() and json.loads(journal.read_text()).get('status')!='rolled_back':executor(serial,root,True)
 verify(serial,root/('restored-'+uuid.uuid4().hex))
 subprocess.run([sys.executable,str(M/'scripts/lab/activation_smoke.py'),'--serial',serial,'--lane','cx-t0','--spec',str(restored_spec),'--out',str(root/('recovery-smoke-'+uuid.uuid4().hex))],check=True)
 verify(serial,root/('final-'+uuid.uuid4().hex))
 (root/'finish.json').write_text(json.dumps({'passed':True,'retained':False,'restored':'U10.1T8','identity_assertions':318,'recovery_smoke':'PASS','final':'PASS'},indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',choices=sorted(lab_paths.boards('oh')),required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',type=Path);p.add_argument('--restored-spec',type=Path)
 g=p.add_mutually_exclusive_group(required=True)
 for name in ['apply','finish','verify-base','verify-candidate']:g.add_argument('--'+name,action='store_true')
 a=p.parse_args()
 if a.apply:assert a.plan is not None;apply(a.serial,a.root,json.loads(a.plan.read_text()))
 elif a.finish:assert a.restored_spec is not None;finish(a.serial,a.root,a.restored_spec)
 else:verify(a.serial,a.root,a.verify_candidate)
if __name__=='__main__':main()
