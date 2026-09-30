import json,collections
from pathlib import Path
H=Path(__file__).resolve().parent
# Source relocation changes line numbers, not the underlying finding; preserve
# original rows and IDs, normalize only presentation fields for comparison.
def normalize(x):
 if isinstance(x,dict):return {k:normalize(v) for k,v in x.items() if k not in ['issue_id','disposition','exception','searched','outside_domain_candidates','line']}
 if isinstance(x,list):return [normalize(v) for v in x]
 return x
def key(g,f):return json.dumps([g,normalize(f)],sort_keys=True)
u=json.loads((H/'u5-gate.json').read_text());n=json.loads((H/'native-gate.json').read_text())
old={key(g,f) for g,v in u['gates'].items() for f in v['findings']};rows=[]
for g,v in n['gates'].items():
 for f in v['findings']:
  baseline=key(g,f) in old
  rows.append(dict(gate=g,issue_id=f['issue_id'],classification='U5-common' if baseline else 'N7-new',finding=f,package_manifest_sha256=n['package_manifest_sha256'],inputs_sha256=n['inputs_sha256'],approval='PENDING',reason='Same semantic finding in signed U5; package binding requires new approval.' if baseline else 'New candidate finding; explicit owner lookup/inherited closure is not proven by this conservative scanner. Inspect row and require short-window maps, actual call-path and controls before acceptance.',evidence=['benchmark/2026-10-01-n7-native/u5-gate.json','benchmark/2026-10-01-n7-native/native-gate.json','benchmark/2026-10-01-n7-native/evidence/u5-aegis-identity.json'],removal_condition='Only a separately scheduled, explicitly approved short window; no persistent exemption. Revoke after rollback or any input drift.'))
counts=dict(collections.Counter(x['classification'] for x in rows));new=[x for x in rows if x['classification']=='N7-new']
report=dict(status='PENDING_OUTER_APPROVAL',counts=counts,normalization='Drop issue_id/disposition/exception/search presentation and source line only; original findings and IDs preserved',entries=rows)
(H/'exception-proposal.json').write_text(json.dumps(report,indent=2)+'\n');(H/'new-findings.json').write_text(json.dumps(new,indent=2)+'\n')
lines=['# N7 exception proposal','','No exceptions installed. No device writes.','',str(counts),'','Only N7-new rows are listed below; candidate-bound U5-common rows remain in JSON.','','| Gate | Kind | Object | Issue |','| --- | --- | --- | --- |']
for x in new:
 f=x['finding'];obj=f.get('library',f.get('profile',f.get('directory',f.get('expression',''))));obj+=(' -> '+f['needed']) if f.get('needed') else '';lines.append(f"| {x['gate']} | {f['kind']} | `{obj}` | `{x['issue_id']}` |")
(H/'EXCEPTION-PROPOSAL.md').write_text('\n'.join(lines)+'\n');print(counts)
