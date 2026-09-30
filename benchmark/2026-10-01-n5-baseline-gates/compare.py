#!/usr/bin/env python3
"""Attach an identical physical snapshot, run strict gates, draft unapproved findings."""
import collections,json,shutil,sys,gzip
from pathlib import Path
from collect import HERE,ROOT
sys.path.insert(0,str(ROOT/'scripts/lab'))
import lab_paths
from native_gate_common import Package,sha256
from native_predeploy import check_package
EVIDENCE=['benchmark/2026-10-01-u5-sweep/results.json','benchmark/2026-10-01-u5-sweep/facts-all.txt']
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def semantic(g,f):
 d={k:v for k,v in f.items() if k not in ('issue_id','disposition','searched','outside_domain_candidates')}
 return json.dumps([g,d],sort_keys=True)
def run():
 snapshot_path=HERE/'snapshot.json'
 snapshot=json.loads(snapshot_path.read_text() if snapshot_path.exists() else gzip.decompress((HERE/'snapshot.json.gz').read_bytes()));reports={};packages={}
 for label,name in [('U5','westlake-generation-n4-order-216b68fb'),('N5','westlake-generation-n5-6d001bb8')]:
  package=lab_paths.workspaces()/name;p=Package(package);packages[label]=p
  side=package/'native-checks';original=side/'native-gates.json'
  backup=HERE/(label.lower()+'-sidecar-before')
  if not backup.exists():shutil.copytree(side,backup)
  inputs=json.loads((backup/'native-gates.json').read_text());files=[];virtual=p.virtual_files();cache=side/'system-elf';cache.mkdir(exist_ok=True)
  for row in snapshot:
   if row['target'] in virtual:continue
   if not row['metadata'] or 'error' in row['metadata']:continue
   src=HERE/'elf'/row['sha256'];dest=cache/row['sha256']
   if not dest.exists():shutil.copyfile(src,dest)
   assert sha256(dest)==row['sha256']
   files.append(dict(target=row['target'],path='system-elf/'+row['sha256'],sha256=row['sha256']))
  inputs['namespaces']['system_files']=files;write(original,inputs)
  report=check_package(package,original);reports[label]=report;write(HERE/(label.lower()+'-gate.json'),report)
  assert not report['errors'],report['errors']
  print(label,report['status'],{k:v['rejected'] for k,v in report['gates'].items()},'system_files',len(files),flush=True)
 rows={label:{semantic(g,f):(g,f) for g,v in r['gates'].items() for f in v['findings']} for label,r in reports.items()}
 shared=rows['U5'].keys() & rows['N5'].keys();new=rows['N5'].keys()-rows['U5'].keys();removed=rows['U5'].keys()-rows['N5'].keys()
 proposals=[];views={label:p.virtual_files() for label,p in packages.items()}
 for label in ['U5','N5']:
  for key,(g,f) in rows[label].items():
   candidates=[]
   if f.get('needed'):
    candidates=[dict(target=s['target'],sha256=s['sha256'],soname=s['metadata'].get('soname')) for s in snapshot if Path(s['target']).name==f['needed'] and s['metadata'] and 'error' not in s['metadata']]
   reason=('The same object/finding exists in signed U5, whose three-board full sweep was reviewed as 24 own-UI results. This does not prove this finding harmless.' if key in rows['U5'] else 'N5-only traversal finding; requires separate outer review, not covered by the baseline exception.')
   library=f.get('library');base_library=views['U5'].get(library);candidate_library=views['N5'].get(library)
   unchanged_library=bool(base_library and candidate_library and base_library['sha256']==candidate_library['sha256'])
   if label=='N5' and key in new and unchanged_library:
    reason += ' The inspected library is byte-identical in U5/N5; it is newly traversed after resolving the Flutter runtime edge. This is a new traversal/visibility risk, not new library bytes.'
   proposals.append(dict(library_unchanged_from_u5=unchanged_library,package=label,classification='shared' if key in shared else ('u5-only' if label=='U5' else 'n5-only'),gate=g,finding=f,physical_candidates=candidates,reason=reason,evidence=EVIDENCE,approval='PENDING',removal_condition='Replace this exception with complete initialization/owner/namespace proof or a verified fix; any package, sidecar or finding drift requires new review.',package_manifest_sha256=reports[label]['package_manifest_sha256'],inputs_sha256=reports[label]['inputs_sha256']))
 diff=dict(shared=len(shared),n5_only=len(new),u5_only=len(removed),n5_only_findings=[dict(gate=rows['N5'][k][0],finding=rows['N5'][k][1]) for k in sorted(new)],u5_only_findings=[dict(gate=rows['U5'][k][0],finding=rows['U5'][k][1]) for k in sorted(removed)],normalization='Remove issue_id/disposition and search/candidate evidence only; retain gate, domain, library, needed, kind and all N1 semantic/evidence fields. Search changes remain in full reports/proposal.')
 write(HERE/'delta.json',diff);write(HERE/'exception-proposal.json',dict(schema_version=1,status='PENDING_OUTER_APPROVAL',entries=proposals))
 print({k:v for k,v in diff.items() if isinstance(v,int)},flush=True)
if __name__=='__main__':run()
