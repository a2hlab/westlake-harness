#!/usr/bin/env python3
"""Pin exact U13 inputs and stage only two reviewed policy edits in this card."""
import difflib, hashlib, json, os, shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
WS=Path(os.environ.get('WORKSPACES',REPO.parent))
MAIN=WS/'westlake-harness'
AUTHOR=WS/'westlake-harness-bms'
REL=Path('benchmark/2026-10-02-u13-single-native')
BASELINE='b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def expand(s):return s.replace('$REPO',str(AUTHOR)).replace('$WORKSPACES',str(WS))
def alias(s):return str(s).replace(str(HERE),'$G18').replace(str(WS),'$WORKSPACES').replace(str(Path.home()),'$HOME')
def main():
 src=MAIN/REL; receipt=json.loads((src/'policy-build-receipt.json').read_text()); identity=json.loads((src/'source-identity.json').read_text())
 report={'source':[],'old_logs':[],'tools':[],'headers':[],'reused':[],'artifacts':[],'missing_or_drift':[]}
 def pin(group,p,expected):
  p=Path(p);actual=sha(p) if p.is_file() else None;row={'path':alias(p),'expected':expected,'actual':actual,'match':actual==expected};report[group].append(row)
  if actual!=expected:report['missing_or_drift'].append(row)
 for name,h in identity['files'].items():
  if name.startswith('sources/candidate/policy/'):pin('source',src/name,h)
 for rec in receipt['commands']:pin('old_logs',expand(rec['raw_path']),rec['raw_sha256']);assert rec['exit_code']==0
 for group,key in [('tools','toolchain'),('headers','headers'),('reused','reused_inputs')]:
  for name,h in receipt[key].items():pin(group,expand(name),h)
 for variant in ['candidate1','candidate2']:
  rec=receipt['artifacts'][variant];assert rec['sha256']==BASELINE;pin('artifacts',expand(rec['path']),BASELINE)
 report['counts']={k:len(v) for k,v in report.items() if isinstance(v,list)}
 report['private_storage']='$G18/.private (persistent card directory inside writable workspace; no shared tree outputs)'
 save(HERE/'input-review.json',report)
 assert not report['missing_or_drift'],report['missing_or_drift']
 for name in ['build.py','policy-build-receipt.json','source-identity.json','test_owner.cpp','test_platform.h','test_analysis.py']:
  reference_name='u13-analysis-tests.reference.txt' if name=='test_analysis.py' else name
  target=HERE/'upstream'/reference_name;target.parent.mkdir(exist_ok=True);shutil.copyfile(src/name,target)
 for name in ['baseline','candidate']:
  shutil.copytree(src/'sources/candidate/policy',HERE/'sources'/name)
 baseline=HERE/'sources/baseline';candidate=HERE/'sources/candidate'
 p=candidate/'policy/native_bridge_policy.v1.json';data=json.loads(p.read_text());assert len(data['shared_sonames'])==7 and len(data['system_libraries'])==7;data['shared_sonames'].append('libGLESv2.so');save(p,data)
 p=candidate/'include/nativeloader/native_bridge_policy.h';s=p.read_text();anchor='    "libstdc++.so",';assert s.count(anchor)==1;s=s.replace('std::array<std::string_view, 7> kBridgeSharedSonames','std::array<std::string_view, 8> kBridgeSharedSonames').replace(anchor,anchor+'\n    "libGLESv2.so",');p.write_text(s)
 diff=[];changed=[]
 for p in sorted(baseline.rglob('*')):
  if p.is_file():
   name=p.relative_to(baseline);q=candidate/name
   if p.read_bytes()!=q.read_bytes():changed.append(str(name));diff.extend(difflib.unified_diff(p.read_text().splitlines(True),q.read_text().splitlines(True),fromfile='baseline/'+str(name),tofile='candidate/'+str(name)))
 assert set(changed)=={'include/nativeloader/native_bridge_policy.h','policy/native_bridge_policy.v1.json'}
 (HERE/'shared-gles.patch').write_text(''.join(diff))
 save(HERE/'source-pins.json',{'source':alias(src),'baseline':BASELINE,'upstream':{str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'upstream').rglob('*')) if p.is_file()},'files':{str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'sources').rglob('*')) if p.is_file()},'reference_files':{'upstream/u13-analysis-tests.reference.txt':{'original_path':str(REL/'test_analysis.py'),'sha256':sha(src/'test_analysis.py'),'purpose':'Verbatim historical U13 policy/host/evidence test reference; requires the complete old U13 directory and is not a G18 executable test.'}},'changed':changed,'predicted_key':'genshin','scope':'GLES SONAME visibility only; no errno/media/system policy change; no deployment'})
 print(json.dumps(report['counts']));print(''.join(diff))
if __name__=='__main__':main()
