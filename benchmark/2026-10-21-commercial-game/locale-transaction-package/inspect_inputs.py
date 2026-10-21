#!/usr/bin/env python3
"""Read G28 pinned assembly and enumerate ABI paths/profiles, without candidate assembly."""
import argparse,hashlib,json,sys,subprocess,re
from pathlib import Path
D=Path(__file__).resolve().parent
BASE='d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--workspaces',type=Path,required=True);a=a.parse_args();w=a.workspaces.resolve();main=w/'westlake-harness';pub=main/'benchmark/2026-10-21-commercial-game/native-route-admission/public-v2';root=w/'westlake-harness-t37-peer/benchmark/2026-10-21-commercial-game/native-route-admission/.private/assembly-01'
 def alias(p):return str(p).replace(str(w),'$WORKSPACES').replace(str(Path.home()),'$HOME')
 pins=json.loads((pub/'input-pins.json').read_text());checked=[]
 for name,r in pins.items():
  p=Path(name.replace('$WORKSPACES',str(w)).replace('$HOME',str(Path.home())));assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'],name;checked.append({'path':alias(p),**r})
 sys.path.insert(0,str(main/'scripts/lab'));sys.dont_write_bytecode=True;import u7_executor as u7
 plan=u7.prepare(root/'candidate',root/'baseline/native');assert len(plan['baseline'])==len(plan['expected'])==319 and not plan['rollout_ready']
 aliases=[];profiles=[];sources=[];owners=[];elfs={}
 for side in ['baseline','candidate']:
  native=root/side/'native';m=json.loads((native/'package.json').read_text());ph=sha(native/'package.json');rows=u7.effective_files(m)
  for target,row in rows.items():
   if Path(target).name=='libwestlake_native_abi.so':
    p=native/row['source'];assert sha(p)==row['sha256']==BASE;aliases.append({'side':side,**row,'bytes':p.stat().st_size,'source_profile':'none: G28 scan profiles do not include ABI source; G30 fixed source/build binding required','replacement_selected':False})
  scan=json.loads((native/'native-checks/scan-manifest.json').read_text())
  for x in scan['profiles']:
   ident=x['identity'];assert ident['manifest_sha256']==ph and sha(native/ident['artifact'])==ident['artifact_sha256'];profiles.append({'side':side,**x})
  for k,x in scan['sources'].items():
   p=native/'native-checks'/x['path'];assert sha(p)==x['sha256'];sources.append({'side':side,'key':k,'path':alias(p),**x})
  ng=json.loads((native/'native-checks/native-gates.json').read_text());ns=json.loads((native/'native-checks/namespace-manifest.json').read_text());assert ng['package_manifest_sha256']==ph
  assert sha(native/'native-checks'/ng['initialization']['manifest']['path'])==ng['initialization']['manifest']['sha256']
  assert sha(native/'native-checks'/ng['namespaces']['manifest']['path'])==ng['namespaces']['manifest']['sha256']
  for x in ns['config_sources']:assert sha(native/'native-checks'/x['path'])==x['sha256']
  owners.append({'side':side,'owner':ng['namespaces']['owner_artifact'],'config_sources':ns['config_sources'],'host_source':scan['sources']['n4-host.c'],'namespace_manifest_sha256':sha(native/'native-checks/namespace-manifest.json')})
  if side=='candidate':
   for n,h in m['files'].items():
    p=native/n
    with p.open('rb') as f:magic=f.read(4)
    if magic==b'\x7fELF':elfs.setdefault(h,{'path':p,'members':[]})['members'].append(n)
 save(D/'abi-aliases.json',aliases);save(D/'source-profiles.json',profiles);save(D/'source-files.json',sources);save(D/'namespace-owners.json',owners);save(D/'baseline-319.json',plan['baseline'])
 save(D/'input-pins.json',checked)
 save(D/'prepared-inputs.json',{'status':'PENDING_G30_FIXED_CANDIDATE','assembly_source':alias(root),'baseline_targets':319,'G28_control_targets':319,'G28_control_logical_changes':sum(v!=plan['baseline'][t] for t,v in plan['expected'].items()),'G28_control_write_count':len(plan['changes']),'candidate_write_count':None,'abi_aliases_per_side':len(aliases)//2,'source_profiles':len(profiles),'source_binding_checks':'PASS on unchanged G28 inputs, not G30','candidate_sha256':None,'candidate_assembled':False,'rollout_ready':False,'deployable':False,'G28_exceptions_inherited':0,'pending':['G30 fixed candidate SHA, raw rc0/build/source/toolchain records and explicit outer acceptance','explicit replacement target set: three same-SHA paths have distinct consumers/domains; do not select by basename','G30 ABI source profile/attestation absent from G28; must add exact source binding','fresh per-window review/signatures and device baseline (no device action here)']})
 # Persist original readelf calls for complete native-payload DT_NEEDED enumeration.
 raw=D/'.private/elf-needed-01';raw.mkdir(exist_ok=False);consumers=[];commands=[]
 for h,x in sorted(elfs.items()):
  argv=['/opt/homebrew/bin/llvm-readelf','-d','--wide',str(x['path'])];r=subprocess.run(argv,capture_output=True);(raw/(h+'.stdout')).write_bytes(r.stdout);(raw/(h+'.stderr')).write_bytes(r.stderr);save(raw/(h+'.json'),{'argv':argv,'rc':r.returncode,'input_sha256':h});assert r.returncode==0
  needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',r.stdout.decode());consumers.append({'sha256':h,'members':x['members'],'needed':needed,'direct_native_abi_needed':'libwestlake_native_abi.so' in needed});commands.append({'path':alias(raw/(h+'.json')),'sha256':sha(raw/(h+'.json'))})
 save(D/'needed-consumers.json',{'scope':'all distinct candidate native-package ELF payloads, direct DT_NEEDED only; dlopen/global consumers separately source-bound','objects':len(elfs),'members':sum(len(x['members']) for x in elfs.values()),'direct_native_abi_consumers':sum(x['direct_native_abi_needed'] for x in consumers),'rows':consumers});save(D/'command-index.json',commands)
 print(json.dumps({'status':'PENDING','verified_G28_pins':len(checked),'ABI_paths':len(aliases)//2,'profiles':len(profiles),'ELF_objects':len(elfs),'direct_native_abi_needed':sum(x['direct_native_abi_needed'] for x in consumers)}))
if __name__=='__main__':main()
