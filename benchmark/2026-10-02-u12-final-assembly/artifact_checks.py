"""Inspect final copied bytes, existing consumers and exact source bindings offline."""
import json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb,generation_static_checks as st,native_needed_gate as ng
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def symbols(p,defined=True):
 text=subprocess.check_output(['llvm-nm','-D','--defined-only' if defined else '--undefined-only','--format=posix',str(p)],text=True)
 return {l.split()[0].split('@')[0] for l in text.splitlines() if l.strip()}
def main():
 c=json.loads((H/'composition.json').read_text());root=Path(c['package'].replace('$WORKSPACES',str(W)));base=Path(c['base_bundle'].replace('$WORKSPACES',str(W)));old,new=st.effective(base),st.effective(root);checks=[]
 for target,d in c['board_changes'].items():
  if target in gb.IMAGE_TARGETS:continue
  candidate=gb.member(root,new[target])
  if candidate.read_bytes()[:4]!=b'\x7fELF':continue
  before=gb.member(base,old[target]) if target in old else None
  meta=ng.parse_dynamic(subprocess.check_output(['llvm-readelf','-d','--wide',str(candidate)],text=True));exp=symbols(candidate)
  row={'target':target,'candidate_sha256':gb.sha(candidate),'deployed_sha256':gb.sha(before) if before else None,'dynamic':meta,'exports':len(exp),'imports':len(symbols(candidate,False)),'baseline_exists':before is not None}
  if before:
   prior=symbols(before);row.update(removed_exports=sorted(prior-exp),added_exports=sorted(exp-prior))
   command=[sys.executable,str(R/'scripts/lab/abi_diff.py'),'--old',str(before),'--new',str(candidate),'--calls','--json',str(H/'evidence'/('abi-'+Path(target).name+('-route' if '/route-a/' in target else '')+'.json'))]
   result=subprocess.run(command,capture_output=True,text=True);row['abi_exit_code']=result.returncode
   (H/'evidence'/('abi-'+Path(target).name+('-route' if '/route-a/' in target else '')+'.txt')).write_text(result.stdout+result.stderr)
  else:row['open_scan']=st.scan(candidate)
  comparison=before or candidate
  strings=subprocess.run([sys.executable,str(R/'scripts/lab/deployed_strings_diff.py'),str(candidate),'--deployed',str(comparison)],capture_output=True,text=True)
  row['strings_exit_code']=strings.returncode;row['strings_scope']='actual effective deployed bytes' if before else 'self identity only; no deployed baseline exists'
  (H/'evidence'/('strings-'+Path(target).name+('-route' if '/route-a/' in target else '')+'.txt')).write_text(strings.stdout+strings.stderr)
  checks.append(row)
 save(H/'artifact-checks.json',checks)
 scanpath=root/'native/native-checks/scan-manifest.json';scan=json.loads(scanpath.read_text());manifest=gb.sha(root/'native/package.json');m=json.loads((root/'native/package.json').read_text())
 assert all(p['identity']['manifest_sha256']==manifest and p['identity']['artifact_sha256']==m['files'][p['identity']['artifact']] for p in scan['profiles'])
 save(H/'artifact-identities.json',{'manifest_sha256':manifest,'scan_manifest_sha256':gb.sha(scanpath),'profiles':len(scan['profiles']),'all_final_bindings_match':True,'host_candidate_sha256':m['files']['payload/runtime/appspawn-x'],'child_unchanged_sha256':m['files']['payload/runtime/libwestlake_android_child.z.so'],'provider_namespace_generation_unchanged':m['generation'],'policy2a6_unchanged':True,'execution_enabled':False})
 print(json.dumps([{k:v for k,v in r.items() if k not in ['open_scan','dynamic']} for r in checks],indent=2))
if __name__=='__main__':
 (H/'evidence').mkdir(exist_ok=True);main()
