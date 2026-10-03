"""Actual master production gates; fresh window reports, no board operations."""
import importlib.util,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
W=Path(os.environ['WORKSPACES']);M=W/'westlake-harness'
sys.path.insert(0,str(M/'scripts/lab'))
spec=importlib.util.spec_from_file_location('master_u12_gates',M/'benchmark/2026-10-02-u12-final-assembly/offline_gates.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.H=HERE;m.R=M;m.W=W
c=json.loads((HERE/'composition.json').read_text())
auth=json.loads((M/'benchmark/2026-10-03-u13-stage-a-plan/outer-window-authorization.json').read_text())
for serial in c['candidate_boards']:
 approved=auth['per_board'][serial]
 assert c['approved_unarmed_bundle_sha256']==approved['bundle_sha256']
 assert c['base_bundle_sha256']==approved['effective_baseline_bundle_sha256']
 package=Path(c['package'].replace('$WORKSPACES',str(W)));base=Path(c['base_bundle'].replace('$WORKSPACES',str(W)))
 assert m.gb.sha(base/'bundle.json')==c['base_bundle_sha256']
 prepared=m.u.prepare(package,base/'native')
 expected=json.loads((HERE/'recovery-u101t8.json').read_text())['boards'][serial]['expected']
 assert prepared['baseline']==expected, 'actual effective baseline full identity differs'
 assert prepared['expected']==c['candidate_boards'][serial]['expected']
 assert not any(x['target'].endswith('libinstalls.z.so') for x in prepared['changes']), 'service action forbidden'
rc=m.main()
surface=sys.argv[sys.argv.index('--surface')+1]
s=json.loads((HERE/'gates'/surface/'summary.json').read_text())
c=json.loads((HERE/'composition.json').read_text());p=Path(c['package'].replace('$WORKSPACES',str(W)))
executor=json.loads((HERE/'gates'/surface/'executor').read_text())
assert rc==0 and s['production_dry_run_exit_code']==0 and executor['gates_passed'] and executor['deployable'],s
assert s['native_gate']=='PASS' and s['static']=='PASS' and not s['native_errors'],s
assert s['RB_exit_code']==s['T4b_exit_code']==s['frozen_exit_code']==s['frozen_composed_violations']==0 and s['G1'] and s['G2'],s
summary={'surface':surface,'production_dry_run_exit_code':0,'gates_passed':True,'deployable':True,'rollout_ready':json.loads((p/'bundle.json').read_text())['rollout_ready'],'bundle_sha256':c['bundle_sha256'],'native_manifest_sha256':c['native_manifest_sha256'],'policy_binding':executor['policy_binding'],'native_findings':s['native_findings'],'static':s['static'],'G1':s['G1'],'G2':s['G2'],'frozen_composed_violations':s['frozen_composed_violations'],'device_io':executor['device_io']}
(HERE/('gate-'+surface+'-pass.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
