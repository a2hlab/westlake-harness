#!/usr/bin/env python3
import collections,json
from pathlib import Path
H=Path(__file__).resolve().parent
p=json.loads((H/'exception-proposal.json').read_text());d=json.loads((H/'delta.json').read_text())
lines=['# Native baseline exception proposal','','Status: **PENDING outer review; no entries installed, no N5 device deployment.**','', 'Every row below is separately bound to a package manifest, complete sidecar input hash and strict issue ID in `exception-proposal.json`. Approval of a group must explicitly enumerate its rows. Baseline evidence: `benchmark/2026-10-01-u5-sweep/{results.json,facts-all.txt}`; outer signed 24 own-UI outcomes. This is bounded test eligibility, not proof that unresolved initialization or namespace visibility is safe.','','N5-only edges are 57 newly traversed dependencies of unchanged U5 library bytes. All 57 dependency basenames exist in the read-only device snapshot. The strict checker does not follow direct inheritance or change owner while traversing a dependency. Physical existence therefore does not discharge its visibility finding. Owner reuse / one initialization remains the device experiment, with U5 rollback required.','','## Per-object decisions requested','','| Row | Package | Relation | Gate/kind | Object | Strict issue ID |','| --- | --- | --- | --- | --- | --- |']
for i,x in enumerate(p['entries'],1):
 f=x['finding'];obj=f.get('library',f.get('directory',f.get('expression',f.get('profile',''))))
 if f.get('needed'):obj+=' → '+f['needed']
 if x['gate']=='N1':obj+=' / '+str(f.get('detail',''))[:220].replace('|','/')
 lines.append(f"| {i} | {x['package']} | {x['classification']} | {x['gate']}/{f['kind']} | `{obj}` | `{f['issue_id']}` |")
(H/'EXCEPTION-PROPOSAL.md').write_text('\n'.join(lines)+'\n')
results=dict(status='pending_outer_exception_review',device_writes=0,n5_deployed=False,board='5ea',snapshot=dict(paths=3278,unique_elf=3129,fetch_or_hash_errors=0,system_files_per_sidecar=3180,boot_id='f828d689-82ab-4bc8-8e15-421332d63721'),gates={label:{g:r['rejected'] for g,r in json.loads((H/(label.lower()+'-gate.json')).read_text())['gates'].items()} for label in ['U5','N5']},delta={k:d[k] for k in ['shared','n5_only','u5_only']},n5_only=dict(count=57,all_unchanged_library_bytes=True,all_needed_basenames_physically_present=True,namespace_visibility_proven=False),exception_entries_installed=0,proposal_entries=len(p['entries']),u5_signed_sweep='benchmark/2026-10-01-u5-sweep',next='Outer review each bound finding; only then register and qualify both N5 deployment and U5 rollback before a locked <=30min window.')
(H/'results.json').write_text(json.dumps(results,indent=2)+'\n')
