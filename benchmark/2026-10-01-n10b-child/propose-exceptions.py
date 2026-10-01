"""Compare to signed U7 and request only exact candidate-bound exceptions."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
d=json.loads((H/'native-gate.json').read_text())
prior=json.loads((H.parent/'2026-10-01-n10-native/approved-production-dry-run.json').read_text())
b=next(t['report'] for t in prior['native_tickets'] if t['report']['package_manifest_sha256']=='7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe')
save(H/'u7-native-baseline.json',b)
def normalize(x):
 if isinstance(x,dict):return {k:normalize(v) for k,v in x.items() if k not in ['issue_id','disposition','exception','line']}
 if isinstance(x,list):return [normalize(v) for v in x]
 return x
key=lambda f:json.dumps(normalize(f),sort_keys=True)
rows=[];comparison={}
for gate,r in d['gates'].items():
 old={key(f) for f in b['gates'][gate]['findings']};new={key(f) for f in r['findings']}
 comparison[gate]={'baseline':len(old),'candidate':len(new),'new_semantic_findings':len(new-old),'removed':len(old-new),'new':[json.loads(x) for x in sorted(new-old)]}
 for f in r['findings']:
  retained=key(f) in old
  rows.append({'gate':gate,'package_manifest_sha256':d['package_manifest_sha256'],'inputs_sha256':d['inputs_sha256'],'issue_id':f['issue_id'],'reason':'Retained signed U7 bounded finding; new binding needs review.' if retained else 'New child namespace bounded-scanner uncertainty: provider first, NOLOAD ART, then owner_paths through sealed.child. Mock confirms order only, device uniqueness unknown.','removal_condition':'Complete owner/initialization proof or verified fix; exact N10b child-only window only.','evidence':[str((H/n).relative_to(H.parents[1])) for n in ['native-gate.json','gate-comparison.json','README.md']],'approval_status':'proposed','classification':'U7-baseline' if retained else 'N10b-new'})
save(H/'gate-comparison.json',comparison);save(H/'exception-proposal.json',{'schema_version':1,'status':'proposal-not-authorized','exceptions':rows});print(json.dumps(comparison))
