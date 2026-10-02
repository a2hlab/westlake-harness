"""Final reviewed donors, fresh unarmed output; no build, board or registry mutation."""
import argparse,copy,json,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb,u7_executor as u,generation_static_checks as static,installation_chain
BASE=W/'westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
DRAFT=W/'westlake-inputs/generations/u12-native-draft-icu1e206531-media8fc0752d-policy2a6ec73f-v4/bundle'
JAVA=W/'westlake-inputs/generations/u12r2-v1'
ZLIB=W/'westlake-harness-bms/benchmark/2026-10-02-u12-private-zlib'
DEST=W/'westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle'
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def portable(p):return str(p).replace(str(W),'$WORKSPACES')
def copy_file(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():dst.chmod(dst.stat().st_mode|0o200)
 shutil.copyfile(src,dst)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=DEST);p.add_argument('--reports-dir',type=Path,default=H);a=p.parse_args();out=a.out.resolve();reportdir=a.reports_dir
 assert gb.sha(BASE/'bundle.json')=='190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736'
 assert not out.exists(),'fresh output required'
 bd,bm,_=gb.validate(BASE);dd,dm,_=gb.validate(DRAFT)
 jc=json.loads((JAVA/'candidate.json').read_text());zr=json.loads((ZLIB/'payload-edit.json').read_text())
 br=json.loads((JAVA/'bake/receipt.json').read_text())
 for name,digest in br['inputs'].items():assert gb.sha(JAVA/'bake/jars9'/name)==digest
 for name,digest in br['outputs_run1'].items():assert gb.sha(JAVA/'bake/run1'/name)==digest
 for name,digest in br['logs'].items():assert gb.sha(JAVA/'bake/logs'/name)==digest
 shutil.copytree(DRAFT,out);n=out/'native';m=copy.deepcopy(dm)
 for rel,row in zr['targets'].items():
  src=Path(row['candidate'].replace('$WORKSPACES',str(W)).replace('$REPO',str(ZLIB.parents[1])))
  assert gb.sha(src)==row['sha256'],rel+' donor drift'
  assert m['files'].get(rel)==row['before'],rel+' baseline drift'
  copy_file(src,n/rel);m['files'][rel]=row['sha256']
 # Effective aliases and the underlying BCP stubs are tied to this bake.
 for row in jc['replace']:
  src=Path(row['source'].replace('$WORKSPACES',str(W)));assert gb.sha(src)==row['u12_sha256']
  rel='payload/android/framework/'+Path(row['target']).name
  copy_file(src,n/rel);m['files'][rel]=row['u12_sha256']
 for target in list(m['live_hashes']):
  rel=u.native.replacement_source(m,target) if target.endswith('.so') or target==u.HOST else None
  if rel:m['live_hashes'][target]=m['files'][rel]
 for rel in zr['targets']:
  target=u.HOST if rel=='payload/runtime/appspawn-x' else '/system/'+rel.removeprefix('payload/')
  m['live_hashes'][target]=m['files'][rel]
 for row in jc['replace']:
  if row['target'] in m['live_hashes']:m['live_hashes'][row['target']]=row['u12_sha256']
 m.update(variant='U12 ICU+mediandk+private zlib+U12r2 Java/paired images',rollout_ready=False,rollout_blocker='Outer final manifest admissions, native/static exceptions and Stage A authorization pending')
 save(n/'package.json',m);manifest=gb.sha(n/'package.json');u.native.validate_upgrade(bm,u.native.load_package(n))
 c=n/'native-checks';scan=json.loads((c/'scan-manifest.json').read_text())
 for name,src in [('n4-host.c',ZLIB/'inputs/candidate-stock-host.c'),('u10-1-resident-compat.h',ZLIB/'inputs/resident-compat.h'),('u12-zlib-route.h',ZLIB/'inputs/zlib-route.h')]:
  copy_file(src,c/name);scan['sources'][name]={'path':name,'sha256':gb.sha(src),'source_sha256':gb.sha(src),'origin':portable(src),'first_line':1}
 scan['profiles'].append({'name':'u12-private-zlib-route','rule':'namespace','source':'u12-zlib-route.h','identity':{'artifact':'payload/runtime/appspawn-x'}})
 for profile in scan['profiles']:profile['identity'].update(package=out.name,manifest_sha256=manifest,artifact_sha256=m['files'][profile['identity']['artifact']])
 save(c/'scan-manifest.json',scan);g=json.loads((c/'native-gates.json').read_text());g['package_manifest_sha256']=manifest;g['initialization']['manifest']['sha256']=gb.sha(c/'scan-manifest.json');save(c/'native-gates.json',g)
 b=copy.deepcopy(dd);b['native']['manifest']['sha256']=manifest
 for row in b['boot_group']['members']+[b['runtime_jar']]:
  name=Path(row['target']).name
  src=JAVA/'bake/run1'/name if row['target'] in gb.IMAGE_TARGETS else JAVA/'bake/jars9'/name
  if name=='oh-adapter-runtime.jar':src=JAVA/'oh-adapter-runtime-u12r2.jar'
  copy_file(src,out/row['source']);row['sha256']=gb.sha(src)
 # Pair real runtime-teed log with exactly run1, never the other boot.art.
 receipt={'status':'verified','input_jars':br['inputs'],'outputs':br['outputs_run1'],'build_command':'bash $LAB_HOME/u12r2-bake/bake_u12.sh 1 (t5 drives dex2oat64-tee.sh)','dex2oat_sha256':br['tools']['dex2oat64 (FZ-005)'],'toolchain_identity_sha256':gb.digest(br['tools']),'build_log_sha256':br['logs']['dex2oat-run1.log'],'build_log':portable(JAVA/'bake/logs/dex2oat-run1.log'),'session_log_sha256':br['logs']['bake-run1.session.log'],'session_log':portable(JAVA/'bake/logs/bake-run1.session.log'),'dex2oat_exit_code':br['dex2oat_rc']['run1'],'t5_reference_comparison':br['t5_rc'],'donor_receipt_sha256':gb.sha(JAVA/'bake/receipt.json'),'origin':portable(JAVA/'bake/run1'),'reproducibility':'run2 differs only known boot.art nondeterministic field; selected run1 is paired with its own actual log'}
 save(out/'receipts/u12-paired-build.json',receipt);b['paired_build_receipt']={'source':'receipts/u12-paired-build.json','sha256':gb.sha(out/'receipts/u12-paired-build.json')}
 policy={'jars':{},'native':{}}
 import deployed_class_diff as dcd
 for row in [b['runtime_jar']]+[r for r in b['boot_group']['members'] if r['target'].endswith('adapter-mainline-stubs.jar')]:
  old=static.effective(BASE)[row['target']];add=sorted(dcd.classes(gb.member(out,row)).keys()-dcd.classes(gb.member(BASE,old)).keys());policy['jars'][row['target']]={'allow_add':add,'candidate_sha256':row['sha256'],'deployed_sha256':old['sha256'],'reason':'Exact added classes from outer-reviewed U12r2 Java donor; no drops or reshapes permitted' if row['target'].endswith('oh-adapter-runtime.jar') else 'Reviewed U12 stubs Predicate addition, all265 effective classes unchanged','evidence':['benchmark/2026-10-02-u12-java-walls/gates/gate-u12r2.txt'] if row['target'].endswith('oh-adapter-runtime.jar') else ['benchmark/2026-10-02-u12-jar-r2-bake/gates/class-diff-stubs-u12.txt']}
 save(out/'static-policy-u12-final.json',policy)
 b['static_checks']={'baseline_bundle_sha256':gb.sha(BASE/'bundle.json'),'policy':{'source':'static-policy-u12-final.json','sha256':gb.sha(out/'static-policy-u12-final.json')}}
 b.update(rollout_ready=False,rollout_blocker=m['rollout_blocker']);b.pop('assembly_pending',None);b.pop('window_authorization',None)
 save(out/'bundle.json',b);_,_,_=gb.validate(out);plan=u.prepare(out,BASE/'native');assert plan['build_receipt']['status']=='verified'
 old,new=static.effective(BASE),static.effective(out);delta={p:{'before':old.get(p,{}).get('sha256'),'after':r['sha256']} for p,r in new.items() if old.get(p,{}).get('sha256')!=r['sha256']}
 assert len([r for r in delta.values() if r['before'] is None])==3
 assert m['files']['payload/zigzag/libmediandk.so']==bm['files']['payload/zigzag/libmediandk.so']
 for rel in ['payload/route/libart.so','payload/runtime/libwestlake_android_child.z.so','payload/route/libbionic_compat.so']:assert m['files'][rel]==bm['files'][rel]
 assert m['files']['payload/route/libnativeloader.so']==dm['files']['payload/route/libnativeloader.so'],'zlib must not replace media policy'
 recovery=json.loads((R/'benchmark/2026-10-02-u12-assembly/recovery-u101t8.json').read_text());boards={}
 native_old=u.effective_files(bm);native_new=u.effective_files(m)
 additions={p for p in native_new if p not in native_old}
 for serial,base in recovery['boards'].items():
  expected=dict(base['expected'])
  for target,row in delta.items():expected[target]=row['after']
  refs={'runtime':sorted(set(plan['reference_paths']['runtime'])|set(installation_chain.PATHS)|{p for p in additions if Path(p).parent==Path('/system/android/lib64')}),'boot':plan['reference_paths']['boot']}
  boards[serial]={'expected':expected,'fingerprints':u.fingerprints(expected,refs),'reference_paths':refs,'unique_paths':len(expected),'identity_assertions':len(expected)+2,'fingerprint_scope':'Conventional bms_batch root/route globs plus installation chain; private zlib separately in complete identity assertions'}
 composition={'state':'FINAL_OFFLINE_UNARMED','package':portable(out),'base_bundle':portable(BASE),'base_bundle_sha256':gb.sha(BASE/'bundle.json'),'base_native_manifest_sha256':gb.sha(BASE/'native/package.json'),'native_manifest_sha256':manifest,'bundle_sha256':gb.sha(out/'bundle.json'),'rollout_ready':False,'execution_enabled':False,'board_changes':delta,'candidate_boards':boards,'deferred_to_U13':['N11h-r2','compat-relocation'],'policy_merge':'No policy collision: zlib donor changes host+two private paths only; 2a6ec73f retained byte-for-byte','paired_build':receipt,'new_native_paths':sorted(additions),'pending':['outer exact new-native rows','outer native/static delta registration','outer Stage A window approval']}
 save(reportdir/'composition.json',composition);save(reportdir/'recovery-u101t8.json',recovery);save(reportdir/'prepare-plan.json',plan)
 save(reportdir/'policy-composition.json',{'candidate_sha256':m['files']['payload/route/libnativeloader.so'],'media_policy_retained':True,'zlib_policy_changes':False,'zlib_donor_sha256':gb.sha(ZLIB/'payload-edit.json'),'before_policy_sha256':bm['files']['payload/route/libnativeloader.so']})
 print(json.dumps({k:v for k,v in composition.items() if k in ['state','package','native_manifest_sha256','bundle_sha256','policy_merge','new_native_paths']},indent=2))
if __name__=='__main__':main()
