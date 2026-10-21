#!/usr/bin/env python3
"""U7 bundle validator/planner. Offline only: deliberately no apply or device API."""
import argparse, contextlib, hashlib, importlib.util, io, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import lab_paths
SEGMENTS=['boot','boot-core-libart','boot-core-icu4j','boot-okhttp','boot-bouncycastle','boot-apache-xml','boot-adapter-mainline-stubs','boot-framework','boot-oh-adapter-framework']
JARS=['core-oj','core-libart','core-icu4j','okhttp','bouncycastle','apache-xml','adapter-mainline-stubs','framework','oh-adapter-framework']
FW='/system/android/framework/'
IMAGE_TARGETS={FW+'arm64/'+s+'.'+e for s in SEGMENTS for e in ['art','oat','vdex']}
BCP_TARGETS={FW+j+'.jar' for j in JARS}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(values):return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def safe(root,name):
 p=Path(name)
 if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe member path')
 f=root/p
 if not f.resolve().is_relative_to(root.resolve()):raise ValueError('escaped member')
 if any(x.is_symlink() for x in [f,*f.parents] if x!=root and x.is_relative_to(root)):raise ValueError('symlink member')
 return f

def member(root,row):
 p=safe(root,row['source'])
 if not p.is_file() or sha(p)!=row['sha256']:raise ValueError('missing/changed member: '+row['source'])
 return p

def read_fingerprint(path):
 result={}
 for line in path.read_text().splitlines():
  value,name=line.split(None,1);name=name.strip()
  if name in result or len(value)!=64 or any(c not in '0123456789abcdef' for c in value) or not re.fullmatch(r'/system/[A-Za-z0-9_./+-]+', name) or '..' in Path(name).parts:raise ValueError('invalid reference fingerprint')
  result[name]=value
 if not result:raise ValueError('empty fingerprint')
 return result

def validate(root):
 root=Path(root).resolve();d=json.loads((root/'bundle.json').read_text())
 if d.get('schema')!='westlake-generation-bundle/v1':raise ValueError('unknown bundle schema')
 native_dir=safe(root,d['native']['directory']);native_manifest=member(root,d['native']['manifest'])
 if native_manifest!=native_dir/'package.json':raise ValueError('native manifest location')
 for p in native_dir.rglob('*'):
  if p.is_symlink():raise ValueError('native symlink')
 from deploy_generation import load_package
 native=load_package(native_dir)
 actual={str(p.relative_to(native_dir)) for p in (native_dir/'payload').rglob('*') if p.is_file()}
 if actual!={p for p in native['files'] if p.startswith('payload/')}:raise ValueError('undeclared or missing native payload')
 rows=d['boot_group']['members'];targets=[r['target'] for r in rows]
 expected=IMAGE_TARGETS|{FW+'adapter-mainline-stubs.jar'}
 if set(targets) not in (expected,expected|{FW+'oh-adapter-framework.jar'}) or len(set(targets))!=len(rows):raise ValueError('boot group must be 27 images plus stubs and optional framework JAR')
 if d['runtime_jar']['target']!=FW+'oh-adapter-runtime.jar':raise ValueError('runtime target mismatch')
 for r in rows+[d['runtime_jar']]:member(root,r)
 if len({r['source'] for r in rows+[d['runtime_jar']]})!=len(rows)+1:raise ValueError('duplicate component source')
 refs={k:read_fingerprint(member(root,d['reference'][k])) for k in ['runtime','boot']}
 if 'image_gate_reference' in d:
  reference=d['image_gate_reference']['members']
  required=IMAGE_TARGETS|BCP_TARGETS
  if len(reference)!=len(required) or {r['target'] for r in reference}!=required:raise ValueError('image reference must contain 27 images and nine effective BCP JARs')
  if len({r['source'] for r in reference})!=len(reference):raise ValueError('duplicate image reference source')
  for r in reference:
   member(root,r)
   if refs['boot'].get(r['target'])!=r['sha256']:raise ValueError('image reference differs from effective baseline: '+r['target'])
 if FW+'oh-adapter-framework.jar' in targets and 'image_gate_reference' not in d:raise ValueError('framework swap requires effective image reference')
 if 'static_checks' in d:member(root,d['static_checks']['policy'])
 expected_hashes=dict(refs['runtime'])
 expected_hashes.update(refs['boot']);expected_hashes.update(native['live_hashes'])
 expected_hashes.update({r['target']:r['sha256'] for r in rows+[d['runtime_jar']]})
 return d,native,expected_hashes

def bcp_members(root,data,manifest):
 """The exact nine JARs visible after native aliases and explicit boot overlays."""
 from u7_executor import effective_files
 rows=effective_files(manifest,data['native']['directory']+'/')
 rows.update({r['target']:r for r in data['boot_group']['members']})
 return {j:member(Path(root),rows[FW+j+'.jar']) for j in JARS}

def probe_fingerprint(values):
 return hashlib.sha256('\n'.join(sorted(f'{v}  {k}' for k,v in values.items())).encode()).hexdigest()[:12]

def plan(root):
 d,native,expected=validate(root)
 refs={k:read_fingerprint(member(Path(root),d['reference'][k])) for k in ['runtime','boot']}
 fingerprints={k:dict(value=probe_fingerprint({p:expected[p] for p in v}),files=len(v)) for k,v in refs.items()}
 groups={'boot_image_and_stubs':{r['target']:r['sha256'] for r in d['boot_group']['members']},'runtime_jar':{d['runtime_jar']['target']:d['runtime_jar']['sha256']},'native':native['live_hashes']}
 return dict(schema='westlake-generation-plan/v1',bundle_sha256=sha(Path(root)/'bundle.json'),device_writes=False,deployable=False,groups={k:dict(identity=digest(v),members=v) for k,v in groups.items()},expected_hashes=expected,expected_fingerprint=digest(expected),probe_fingerprints=fingerprints,required_gates=['G1','G2','N1','N2','frozen','deployed_classes_frozen','native_open_sites','paired_build_receipt','board_baseline_identity','post_activation_child_identity'],steps=['verify all member hashes and all required gates before lock','read and verify live U5/current baseline and original mount/JAR receipts','stage every component and a complete rollback copy before stopping parent','stop receipt-owned Android apps and verify children gone; stop appspawn-x once with begetctl; keep stopped throughout transaction','activate native mounts without restarting parent','activate every declared boot-group image and JAR as one stopped-parent transaction','activate runtime JAR; verify entire target hash map before start','start appspawn-x once; verify child view, single ART, bridge, full hashes and images','run approved controls; on failure execute complete rollback'],rollback=['stop parent with begetctl','restore original native mounts','restore every original boot-group image and JAR','restore original runtime JAR and exact overlay stack','verify full baseline hashes and absent-file ledger before restart','start parent; verify parent/child identity and both baseline fingerprints; unlock only after success'],blocked_reasons=['offline planner only; execution requires u7_executor production preflight','U7 composition and rollout require independent outer acceptance'])

BCP_SWAP_DEFAULT=('adapter-mainline-stubs','oh-adapter-framework')
BCP_SWAP_EXCEPTIONS='knowledge/gates/bcp-swap-exceptions.json'
def bcp_swap_exceptions(path=None):
 """{(segment, reference sha256, candidate sha256): id} for approved rows. Any other segment swap stays refused."""
 path=Path(path) if path else lab_paths.harness()/BCP_SWAP_EXCEPTIONS
 if not path.is_file():return {}
 return {(r['segment'],r['reference_sha256'],r['candidate_sha256']):r['id'] for r in json.loads(path.read_text())['exceptions'] if r.get('status')=='approved'}
def bcp_swap_verdict(pairs,excepted):
 """pairs {segment: (segment, reference sha256, candidate sha256)} -> ({segment: exception id}, [undeclared segments])."""
 matched={j:excepted[p] for j,p in pairs.items() if p in excepted}
 return matched,[j for j in pairs if j not in BCP_SWAP_DEFAULT and j not in matched]

def image_checks(root,oatdump=None):
 """Run the existing trusted G1/G2 implementations, never bundle-supplied code."""
 root=Path(root).resolve();d,_,_=validate(root);master=lab_paths.harness();module=master/'knowledge/toolchains/art-r155/image_predeploy_gate.py'
 spec=importlib.util.spec_from_file_location('trusted_image_gate',module);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 native=root/d['native']['directory'];log=io.StringIO()
 with tempfile.TemporaryDirectory(prefix='u7-image-check-') as td:
  temp=Path(td);image=temp/'image/arm64';image.mkdir(parents=True);bcp=temp/'bcp';bcp.mkdir()
  if 'image_gate_reference' in d:
   ref=temp/'reference';(ref/'arm64').mkdir(parents=True)
   for r in d['image_gate_reference']['members']:
    dest=ref/('arm64/' if r['target'] in IMAGE_TARGETS else '')/Path(r['target']).name
    shutil.copyfile(member(root,r),dest)
  else:ref=native/'payload/android/framework'
  for r in d['boot_group']['members']:
   if r['target'] in IMAGE_TARGETS:shutil.copyfile(member(root,r),image/Path(r['target']).name)
  _,manifest,_=validate(root)
  for j,p in bcp_members(root,d,manifest).items():shutil.copyfile(p,bcp/(j+'.jar'))
  swaps=[j for j in JARS if sha(ref/(j+'.jar'))!=sha(bcp/(j+'.jar'))]
  matched,undeclared=bcp_swap_verdict({j:(j,sha(ref/(j+'.jar')),sha(bcp/(j+'.jar'))) for j in swaps},bcp_swap_exceptions())
  if undeclared:raise ValueError('undeclared BCP segment swap: '+','.join(undeclared))
  with contextlib.redirect_stdout(log):
   g1=g.gate_g1(image.parent,ref,swaps)
   g2=g.gate_g2(image.parent,ref,oatdump,str(ref),str(bcp),None,'java.lang.String#hashCode',True)
 return dict(G1=bool(g1),G2=g2 is True,checker_sha256=sha(module),swapped_segments=swaps,bcp_swap_exceptions=matched,reference_kind='effective-baseline' if 'image_gate_reference' in d else 'legacy-native-payload',log=log.getvalue(),limitation='G1 exempts exactly the changed BCP segments; a paired build receipt binds all nine effective inputs to all 27 outputs.')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--dry-run',action='store_true',required=True);p.add_argument('--run-image-gates',action='store_true');p.add_argument('--oatdump');p.add_argument('--run-native-gates',action='store_true');p.add_argument('--readelf',default='readelf');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 report=plan(a.package)
 if a.run_image_gates:report['image_gates']=image_checks(a.package,a.oatdump)
 master=lab_paths.harness();d,_,expected=validate(a.package)
 spec=importlib.util.spec_from_file_location('trusted_frozen',master/'scripts/lab/check_frozen.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
 entries=f.active(f.load(master/'knowledge/frozen/frozen.json'));lines,bad=f.check_artifacts(entries,expected,'U7 composed')
 report['frozen']=dict(violations=bad,lines=lines,registry_sha256=sha(master/'knowledge/frozen/frozen.json'))
 report['native_gate']={'status':'REQUIRED_SEPARATELY','package_sha256':d['native']['manifest']['sha256'],'old_window_grants_valid':False}
 if a.run_native_gates:
  sys.path.insert(0,str(master/'scripts/lab'));import native_predeploy
  native=a.package/d['native']['directory']
  report['native_gate']=native_predeploy.check_package(native,native/'native-checks/native-gates.json',exceptions=master/'knowledge/gates/native-predeploy-exceptions.json',readelf=a.readelf)
 report['requested_checks_passed']=not bad and (not a.run_image_gates or all(report['image_gates'][k] for k in ['G1','G2'])) and (not a.run_native_gates or report['native_gate']['status']=='PASS')
 a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['bundle_sha256','device_writes','deployable','requested_checks_passed','blocked_reasons']}))
 return 0 if report['requested_checks_passed'] else 2
if __name__=='__main__':raise SystemExit(main())
