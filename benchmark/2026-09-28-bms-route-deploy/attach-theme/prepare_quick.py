"""Materialize quick-only reproducers pinned to B5+B6, retaining every upstream check."""
from pathlib import Path
import json,shutil,hashlib,re,subprocess
r=Path(__file__).resolve().parent
suite=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite');out=suite/'var/state/b6-quick';out.mkdir(exist_ok=True)
old=suite/'.bridge-payload/zigzag-persisted/strict-20260809T160651Z-21101'
root=out/'candidates';candidate=root/'b5-alias-b6-context';
if not candidate.exists():shutil.copytree(old,candidate)
for p in [candidate/"files/oh-adapter-runtime.jar",candidate/"manifest.env",candidate/"files.sha256"]:p.chmod(0o644)
newsha='250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146'
with (candidate/'files/oh-adapter-runtime.jar').open('wb') as f:subprocess.run(['orb','-m','a2hlab','cat','/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b5/build/oh-adapter-runtime.jar'],stdout=f,check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(candidate/'files/oh-adapter-runtime.jar')==newsha
p=candidate/'manifest.env';s=p.read_text();s=re.sub(r'(?m)^RUNTIME_JAR_SHA=.*$', 'RUNTIME_JAR_SHA='+newsha,s);s=re.sub(r'(?m)^CANDIDATE_ID=.*$', 'CANDIDATE_ID=b5-alias-b6-context',s);p.write_text(s)
p=candidate/'files.sha256';s=p.read_text().replace('9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea',newsha);p.write_text(s)
(root/'current').write_text(str(candidate)+'\n')
changes=[]
for app in ['helloworld','zigzag-apk']:
 source=suite/f'.agents/skills/reproduce-{app}/scripts/reproduce.sh';s=source.read_text()
 if app=='helloworld':
  s=s.replace('ZIGZAG_JAR_SHA="9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea"','ZIGZAG_JAR_SHA="'+newsha+'"').replace('zigzag-accepted-superset','b5-alias-b6-context-test')
 else:
  s=s.replace('CANDIDATE_ID="strict-20260809T160651Z-21101"','CANDIDATE_ID="b5-alias-b6-context"')
  s=s.replace('PERSISTED_ROOT="$REPO_ROOT/.bridge-payload/zigzag-persisted"','PERSISTED_ROOT="'+str(root)+'"')
  s=re.sub(r'(?m)^FILES_MANIFEST_SHA=.*$', 'FILES_MANIFEST_SHA="'+sha(candidate/'files.sha256')+'"',s)
  s=re.sub(r'(?m)^CANDIDATE_MANIFEST_SHA=.*$', 'CANDIDATE_MANIFEST_SHA="'+sha(candidate/'manifest.env')+'"',s)
  s=s.replace('9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea',newsha)
 dest=out/(app+'-quick.sh');dest.write_text(s);dest.chmod(0o755)
 changes.append({'upstream':str(source),'upstream_sha256':sha(source),'output':str(dest),'output_sha256':sha(dest),'purpose':'Pin quick to the exact tested B5 runtime; B6 framework/cohort separately guarded. No validation removed.'})
# Other 12 payload files must remain byte-identical. Candidate is quick-only;
# the untouched persisted recovery script is NOT an authorized B6 restore path.
changed=[p.name for p in (old/'files').iterdir() if p.is_file() and sha(p)!=sha(candidate/'files'/p.name)]
assert changed==['oh-adapter-runtime.jar'],changed
(r/'quick-provenance.json').write_text(json.dumps({'wrappers':changes,'candidate':str(candidate),'changed_payload_files':changed,'framework_expected':json.loads((r/'build-framework.json').read_text())['output_sha256'],'usage':'quick only; do not restore or persist this derived candidate'},indent=2)+'\n')
print(out)
