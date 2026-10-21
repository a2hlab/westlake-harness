#!/usr/bin/env python3
"""Export compact sanitized metadata; immutable raw receipts stay private."""
import json,sys
from pathlib import Path
from inspect_inputs import sha,save
D=Path(__file__).resolve().parent;W=D.parents[2].parent;A=D/'.private/assembly-01';R=D/'.private/gates-01'
def clean(v):return json.loads(json.dumps(v).replace(str(W),'$WORKSPACES').replace(str(Path.home()),'$HOME'))
def write(name,v):save(D/name,clean(v))
def pin(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def main():
 sys.dont_write_bytecode=True;sys.path.insert(0,str(W/'westlake-harness/scripts/lab'));import u7_executor as u7
 plan=json.loads((A/'transaction-plan.raw.json').read_text());receipt=json.loads((A/'assembly-receipt.json').read_text());write('transaction-plan.json',plan);write('assembly.json',receipt)
 gates={};findings=[];packages={}
 for side in ['baseline','candidate']:
  native=A/side/'native';manifest=json.loads((native/'package.json').read_text());rows=u7.effective_files(manifest);scan=json.loads((native/'native-checks/scan-manifest.json').read_text());g=json.loads((R/('native-'+side+'.stdout')).read_text())
  packages[side]={'metadata':[pin(A/side/'bundle.json')]+[pin(native/x) for x in ['package.json','native-checks/native-gates.json','native-checks/scan-manifest.json','native-checks/namespace-manifest.json']], 'native_files':[pin(native/name) for name in sorted(manifest['files'])]}
  for p in packages[side]['native_files']:
   relative=str(Path(p['path']).relative_to(native));assert p['sha256']==manifest['files'][relative]
  gates[side]={'rc':g['exit_code'],'status':g['status'],'errors':g['errors'],'package_manifest_sha256':g['package_manifest_sha256'],'inputs_sha256':g['inputs_sha256'],'exceptions_sha256':g['exceptions_sha256'],'gates':{k:{n:v[n] for n in ['rejected','excepted','stale']} for k,v in g['gates'].items()}}
  profiles={x['name']:x for x in scan['profiles']}
  for gate,result in g['gates'].items():
   for f in result['findings']:
    binding={}
    if gate=='N1':binding={'profile_identity':profiles[f['profile']]['identity'],'scan_manifest_sha256':sha(native/'native-checks/scan-manifest.json')}
    else:
     # Bind every explicit affected path to current bytes, including directory members.
     objects={t:v['sha256'] for t,v in rows.items() if t==f.get('library') or (f.get('directory') and str(Path(t).parent)==f['directory'])}
     binding={'objects':objects,'namespace_manifest_sha256':sha(native/'native-checks/namespace-manifest.json')}
    findings.append({'side':side,'gate':gate,'package_manifest_sha256':g['package_manifest_sha256'],'inputs_sha256':g['inputs_sha256'],'finding':f,'binding':binding,'signature':None,'approval_inherited':False})
 s=json.loads((R/'static.json').read_text());gates['static']={k:s[k] for k in ['status','bundle_sha256','baseline_bundle_sha256','policy_sha256']};gates['static']['members']=[{k:x[k] for k in ['target','candidate_sha256','deployed_sha256','status','delta_sha256','review']} for x in s['members']]
 for x in s['members']:
  if x['status']!='PASS':findings.append({'side':'candidate','gate':'static','finding':{k:x[k] for k in ['target','candidate_sha256','deployed_sha256','status','delta_sha256','review']},'signature':None,'approval_inherited':False})
 records=json.loads((R/'records.json').read_text());gates['rc']={r['name']:r['rc'] for r in records};gates['G1']='NOT_REACHED';gates['G2']='NOT_REACHED';write('gates.json',gates);write('gate-commands.json',records)
 write('findings.unsigned.json',{'status':'UNSIGNED_NOT_ADMITTED','generated_from':'actual gates-01 outputs; no historical approval inherited','native_rows':sum(x['gate'] in ['N1','N2'] for x in findings),'static_rows':sum(x['gate']=='static' for x in findings),'rows':findings})
 write('package-index.json',packages)
 evidence=[]
 for p in sorted(R.rglob('*')):
  if p.is_file():evidence.append(pin(p))
 for sub in ['assembly-command-01']:
  for p in sorted((D/'.private'/sub).iterdir()):
   if p.is_file():evidence.append(pin(p))
 evidence.extend([pin(A/'assembly-receipt.json'),pin(A/'transaction-plan.raw.json'),pin(A/'candidate/native/native-checks/g30-abi-source-binding.json')]);write('evidence-index.json',evidence)
 write('six-targets.json',[{'target':t,'baseline_sha256':plan['baseline'][t],'candidate_sha256':v} for t,v in plan['expected'].items() if v!=plan['baseline'][t]])
 write('current-abi-aliases.json',[{'target':t,'baseline_sha256':plan['baseline'][t],'candidate_sha256':v,'changed':v!=plan['baseline'][t]} for t,v in plan['expected'].items() if Path(t).name=='libwestlake_native_abi.so'])
 write('current-source-profiles.json',{side:json.loads((A/side/'native/native-checks/scan-manifest.json').read_text())['profiles'] for side in ['baseline','candidate']})
 write('results.json',dict(receipt,deployable=False,candidate_assembled=True,acceptance_scope='OFFLINE_UNSIGNED_ASSEMBLY_ONLY',native_findings=sum(x['gate'] in ['N1','N2'] for x in findings),static_review_rows=sum(x['gate']=='static' for x in findings),gate_rc=gates['rc'],pending=['Exact current N1/N2/static outer review and signatures (none issued here)','G1/G2 full original preflight after static review; not reached here','Fresh device/window admission and deployment authorization (no device use here)','G30 final public documentation is supplementary; accepted20 pins already used']))
 print(json.dumps({'targets':receipt['targets'],'writes':receipt['planned_writes'],'native_findings':sum(x['gate'] in ['N1','N2'] for x in findings),'static_review_rows':sum(x['gate']=='static' for x in findings)}))
if __name__=='__main__':main()
