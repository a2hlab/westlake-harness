"""Disabled-reviewed Stage A: one journal transaction, always restore U13."""
import argparse,json,os,subprocess,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3];W=R.parent
M=W/'westlake-harness'
sys.path.insert(0,str(M/'scripts/lab'))
import generation_bundle as gb,u7_executor as u,lab_paths,deployment_native_gate as native_gate
def composition():return json.loads((H/'composition.json').read_text())
def path(name):return Path(os.path.expandvars(name.replace('$WORKSPACES',str(W))))
def admission(plan):
 c=composition();b=json.loads((path(c['package'])/'bundle.json').read_text())
 assert plan.get('execution_enabled') is True and c.get('execution_enabled') is True,'U14 execution disabled'
 assert c.get('rollout_ready') is True and b.get('rollout_ready') is True,'U14 not armed'
 assert gb.sha(path(c['package'])/'bundle.json')==c['bundle_sha256']==plan['bundle_sha256'],'bundle drift'
 assert gb.sha(path(c['package'])/'native/package.json')==c['native_manifest_sha256']==plan['package_manifest_sha256'],'manifest drift'
 auth=json.loads((M/'benchmark/2026-10-03-u14-stage-a-plan/outer-window-authorization.json').read_text())
 review=json.loads((M/'benchmark/2026-10-03-u14-stage-a-plan/outer-smoke-review.json').read_text())
 assert auth['signer']==review['signer']=='outer(claude)' and review['armed']['decision']=='accept'
 serial=plan['serial'];a=auth['per_board'][serial]
 assert c['approved_unarmed_bundle_sha256']==a['bundle_sha256'] and c['base_bundle_sha256']==a['effective_baseline_bundle_sha256']
 assert auth['native_manifest_sha256']==c['native_manifest_sha256'] and auth['native_inputs_sha256']==c['native_inputs_sha256']
 assert gb.sha(path(c['base_bundle'])/'bundle.json')==c['base_bundle_sha256'],'actual armed U13 base drift'
 proof=json.loads((H/'arming-proof.json').read_text());assert proof['armed_sha256']==c['bundle_sha256'] and proof['unarmed_sha256']==a['bundle_sha256']
 assert set(proof['bundle_field_diff'])=={'rollout_ready','rollout_blocker'} and proof['other_files_byte_identical']
 assert plan['phase']=='A' and plan['restore']['state']=='U13' and plan['restore']['unconditional'],'wrong observation semantics'
 assert plan['window_limit_minutes']==45 and plan['stop_new_tests_by_minute']==35
 table=path(plan['key_table_path']);assert gb.sha(table)==plan['key_table_sha256'] and plan['key_table_sha256'].startswith('024c1f7f'),'v5 not bound'
 spec=json.loads(path(plan['smoke_spec']).read_text());assert spec.get('control_selftest') is True
 assert spec['probe']['copy_limits']=={'liboh_adapter_bridge.so':{'min':1,'max':2},'liboh_android_runtime.so':{'min':1,'max':2},'libjavacore.so':{'min':1,'max':2},'libicu74compat.so':{'min':0,'max':1}}
 assert gb.sha(M/'scripts/lab/activation_smoke.py')==plan['activation_smoke_sha256'],'required production smoke implementation not landed / drift'
 for surface in ['mac','vm']:
  g=json.loads((H/f'gate-{surface}-pass.json').read_text())
  assert g['bundle_sha256']==c['bundle_sha256'] and g['gates_passed'] and g['production_dry_run_exit_code']==0
  current=u.policy_binding(path(c['package']));assert g['policy_binding']==current,'fresh gate policy drift'
  report=json.loads((H/'gates'/surface/'executor').read_text())
  assert report['deployable'] and report['gates_passed']
  for ticket in report['native_tickets']:native_gate.assert_unchanged(ticket)
def vm(command):
 return subprocess.run(['orb','-m','a2hlab','env','WORKSPACES='+str(W),'MAC_HOME='+os.environ.get('MAC_HOME',str(Path.home())),'LAB_HOME='+os.environ['LAB_HOME'],*map(str,command)],check=True)
def verify(serial,root,candidate=False,process_view=True):
 if sys.platform=='darwin':
  return vm(['python3',Path(__file__).resolve(),'--verify-candidate' if candidate else '--verify-base','--serial',serial,'--root',root])
 c=composition();row=c['candidate_boards'][serial] if candidate else json.loads((H/'recovery-u13.json').read_text())['boards'][serial]
 root.mkdir(parents=True,exist_ok=True);io=u.DeviceIO(serial,'cx-t0',root/'device')
 got,absent=io.snapshot(sorted(row['expected']));diff={p:{'expected':v,'actual':got.get(p)} for p,v in row['expected'].items() if got.get(p)!=v}
 refs=row['reference_paths']
 fp=u.fingerprints(got,refs) if not absent else None
 report={'state':'U14' if candidate else 'U13','identity_assertions':row['identity_assertions'],'unique_paths':len(got),'diff':diff,'absent':absent,'fingerprints':fp,'boot_id':io.boot}
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
 (root/'finish.json').write_text(json.dumps({'passed':True,'retained':False,'restored':'U13','identity_assertions':321,'recovery_smoke':'PASS','final':'PASS'},indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',choices=sorted(lab_paths.boards('oh')),required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',type=Path);p.add_argument('--restored-spec',type=Path)
 g=p.add_mutually_exclusive_group(required=True)
 for name in ['apply','finish','verify-base','verify-candidate']:g.add_argument('--'+name,action='store_true')
 a=p.parse_args()
 if a.apply:assert a.plan is not None;apply(a.serial,a.root,json.loads(a.plan.read_text()))
 elif a.finish:assert a.restored_spec is not None;finish(a.serial,a.root,a.restored_spec)
 else:verify(a.serial,a.root,a.verify_candidate)
if __name__=='__main__':main()
