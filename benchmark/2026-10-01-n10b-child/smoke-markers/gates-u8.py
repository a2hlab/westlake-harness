"""Strict candidate checks and semantic differences against the signed U8 report."""
import hashlib,json,os,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if (p/"scripts/lab/u7_executor.py").is_file());sys.path.insert(0,str(R/'scripts/lab'))
import native_predeploy as gate
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
records=json.loads((H/'u8-package.json').read_text());approved=json.loads((H.parent/'2026-10-01-u8-rollout/approved-production-dry-run.json').read_text());baseline=next(x['report'] for x in approved['native_tickets'] if x['report']['package_manifest_sha256']=='7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe');save(H/'u8-native-baseline.json',baseline)
def normalize(x):
 if isinstance(x,dict):return {k:normalize(v) for k,v in x.items() if k not in ['issue_id','disposition','exception','line','sequence']}
 if isinstance(x,list):return [normalize(v) for v in x]
 return x
key=lambda f:json.dumps(normalize(f),sort_keys=True)
summary={}
for mode,row in records.items():
 package=R.parent/row['native'];c=package/'native-checks'
 if mode=='batch':
  # Include the new JNI source explicitly, with the real runtime identity.
  scan=json.loads((c/'scan-manifest.json').read_text());src='emboss-emboss-registration.cpp'
  scan['sources'][src]={'path':src,'sha256':sha(c/src),'origin':str((H/'src/emboss/emboss-registration.cpp').relative_to(R)),'source_sha256':sha(c/src),'first_line':1}
  scan['profiles']=[p for p in scan['profiles'] if p['name']!='emboss-registration']
  scan['profiles'].append({'name':'emboss-registration','rule':'jni-order','sources':[src],'entry_source':src,'entry_function':'register_n10b_Emboss','identity':{'package':package.name,'manifest_sha256':row['native_manifest_sha256'],'artifact':'payload/android/lib64/liboh_android_runtime.so','artifact_sha256':row['runtime_sha256']}})
  added=['android_graphics_Typeface.cpp','asset-offsets-init.cpp']
  for name in added:
   scan['sources'][name]={'path':name,'sha256':sha(c/name),'origin':str((H/'src'/name).relative_to(R)),'source_sha256':sha(c/name),'first_line':1}
   profile=name.removesuffix('.cpp')
   scan['profiles']=[p for p in scan['profiles'] if p['name']!=profile]
   scan['profiles'].append({'name':profile,'rule':'jni-order','sources':[name],'entry_source':name,'entry_function':'register_android_graphics_Typeface' if name==added[0] else 'initialize_n10b_asset_offsets','identity':{'package':package.name,'manifest_sha256':row['native_manifest_sha256'],'artifact':'payload/android/lib64/liboh_android_runtime.so','artifact_sha256':row['runtime_sha256']}})
  next(p for p in scan['profiles'] if p['name']=='runtime')['sources'] = ['n4-order-runtime.cpp','egl.cpp','gl-register.cpp','gl-wrapper.cpp',src]+added
  save(c/'scan-manifest.json',scan);g=json.loads((c/'native-gates.json').read_text());g['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');save(c/'native-gates.json',g)
  # Sidecars do not alter native package identity, but both native copies must agree.
  import shutil
  dst=R.parent/row['bundle']/'native/native-checks';shutil.rmtree(dst);shutil.copytree(c,dst)
 d=gate.check_package(package,c/'native-gates.json',readelf='/usr/bin/readelf');save(H/(mode+'-u8-native-gate.json'),d)
 assert not d['errors'],d['errors']
 comparison={};exceptions=[]
 for name,value in d['gates'].items():
  old={key(f) for f in baseline['gates'][name]['findings']};new={key(f) for f in value['findings']}
  comparison[name]={'baseline':len(old),'candidate':len(new),'retained':len(old&new),'new_semantic_findings':len(new-old),'removed':len(old-new),'new':[json.loads(s) for s in sorted(new-old)]}
  for f in value['findings']:
   retained=key(f) in old
   exceptions.append({'gate':name,'package_manifest_sha256':d['package_manifest_sha256'],'inputs_sha256':d['inputs_sha256'],'issue_id':f['issue_id'],'approval_status':'proposed','classification':'U8-baseline' if retained else 'N10b-new','reason':'Retained signed U8 bounded finding; exact candidate binding requires outer review.' if retained else 'Bounded registration/namespace analysis; exact source mock proves VM-before-registration and two cache assignments. Board DSO uniqueness and rendering remain unverified.','removal_condition':'Complete namespace/initialization proof; approved exact N10b single-variable window only.','evidence':[str((H/n).relative_to(R)) for n in [mode+'-u8-native-gate.json',mode+'-u8-gate-comparison.json','README.md']]})
 save(H/(mode+'-u8-gate-comparison.json'),comparison);save(H/(mode+'-u8-exception-proposal.json'),{'schema_version':1,'status':'proposal-not-authorized','exceptions':exceptions});summary[mode]={'status':d['status'],'counts':{k:{x:v[x] for x in ['rejected','excepted']} for k,v in d['gates'].items()},'comparison':{k:{a:v[a] for a in ['baseline','candidate','new_semantic_findings','removed']} for k,v in comparison.items()}}
save(H/'u8-gate-summary.json',summary);print(json.dumps(summary,indent=2))
