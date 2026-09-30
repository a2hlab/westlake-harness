#!/usr/bin/env python3
import collections,json
from pathlib import Path
H=Path(__file__).resolve().parent

def semantic(g,f):
 return json.dumps([g,{k:v for k,v in f.items() if k not in ('issue_id','disposition','searched','outside_domain_candidates')}],sort_keys=True)
def main():
 reports={k:json.loads((H.parent/'2026-10-01-n5-baseline-gates'/f'{k.lower()}-gate.json').read_text()) for k in ['U5','N5']}
 sets={k:{semantic(g,f) for g,v in r['gates'].items() for f in v['findings']} for k,r in reports.items()}
 n=json.loads((H/'native-gate.json').read_text());entries=[]
 for g,v in n['gates'].items():
  for f in v['findings']:
   key=semantic(g,f);kind='U5 baseline' if key in sets['U5'] else 'N5 traversal' if key in sets['N5'] else 'N6 new'
   reason={'U5 baseline':'Same finding exists in signed U5; this does not prove safety.','N5 traversal':'N5 newly traversed dependency; no additional duplicated inode or changed payload set relative to the same app on same-board U5 is required.','N6 new':'Copied R155 owner bookkeeping adds libc++; N5 LocalSend already mapped the exact chipset-sdk-sp libc++ and all new strong imports resolve in those bytes. Namespace/instance reuse still requires device evidence.'}[kind]
   entries.append(dict(gate=g,issue_id=f['issue_id'],package_manifest_sha256=n['package_manifest_sha256'],inputs_sha256=n['inputs_sha256'],classification=kind,finding=f,approval='PENDING',reason=reason,removal_condition='One <=30min 5ea window only; expire and rollback U5. Any package or input drift requires new approval.',evidence=['benchmark/2026-10-01-u5-sweep/results.json','benchmark/2026-10-01-n5-window/duplicate-baseline.json','benchmark/2026-10-01-n6-native/symbol-audit.json']))
 counts=dict(collections.Counter(e['classification'] for e in entries))
 (H/'exception-proposal.json').write_text(json.dumps(dict(schema_version=1,status='PENDING_OUTER_APPROVAL',counts=counts,entries=entries),indent=2)+'\n')
 lines=['# N6 candidate-bound exception proposal','','**PENDING outer approval; none installed. No device writes.**','','Counts: '+str(counts),'','For each app/process, compare five singleton-library `(device,inode)` counts and payload SHA sets with a same-board U5 sample. LocalSend U5 has two liblog inodes. Missing baselines are unknown, not accepted. Also record EGL/GLES/libc++ provider identities and wrapper dispatch evidence.','','| Row | Class | Gate/kind | Object | Issue ID |','| --- | --- | --- | --- | --- |']
 for i,e in enumerate(entries,1):
  f=e['finding'];obj=str(f.get('library',f.get('directory',f.get('profile',f.get('expression','')))));obj+=(' -> '+f['needed']) if f.get('needed') else ''
  lines.append(f"| {i} | {e['classification']} | {e['gate']}/{f['kind']} | `{obj}` | `{e['issue_id']}` |")
 (H/'EXCEPTION-PROPOSAL.md').write_text('\n'.join(lines)+'\n');print(counts)
if __name__=='__main__':main()
