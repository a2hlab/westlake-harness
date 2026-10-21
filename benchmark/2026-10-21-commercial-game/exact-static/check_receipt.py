#!/usr/bin/env python3
"""Validate exact public static evidence; optional private raw integrity, never runs the APK."""
import argparse,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
EXPECTED='abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(p.read_text())
def validate(d,private=None,manifest=True):
 r=load(d/'results.json');e=load(d/'elf-inventory.json');x=load(d/'dex-inventory.json')
 assert r['input']['sha256']==EXPECTED and r['input']['bytes']==513290344 and r['input']['match'] is True
 assert r['runtime']=='NOT_TESTED' and r['first_fatal']=='UNKNOWN' and r['human_review']=='PENDING'
 assert r['device_actions']==r['game_executions']==r['target_binaries_built']==0
 assert r['status']=='STATIC_ANALYSIS_COMPLETE_RUNTIME_NOT_TESTED' and r['rea_methods_consumed']==5
 methods=load(d/'rea-method-findings.json')['records'];assert len(methods)==5 and len({m['evidence_id'] for m in methods})==5
 assert all(m['artifact_sha256']==EXPECTED and m['executed_by']=='outer(codex)' and m['body_status']=='available' and m['source_status']=='complete' for m in methods)
 assert e['apk_sha256']==x['apk_sha256']==EXPECTED
 assert len(e['libraries'])==32 and len({q['member'] for q in e['libraries']})==32
 assert all(q['elf_class']=='ELF64' and q['machine']=='AArch64' and q['member'].startswith('lib/arm64-v8a/') and len(q['sha256'])==64 for q in e['libraries'])
 assert len(x['dexes'])==5 and len(x['native_declarations'])==881
 assert sum(bool(q['short_export_candidates'] or q['long_export_candidates']) for q in x['native_declarations'])==125
 assert all(q['binding_status'] in ['EXPORTED_NAME_CANDIDATE_NOT_RUNTIME','NO_EXPORTED_NAME_MATCH_DYNAMIC_REGISTRATION_UNKNOWN'] for q in x['native_declarations'])
 h=load(d/'evidence/dex-class-counts.json');assert h['sum']==sum(q['class_defs_size'] for q in h['dex_headers'])==x['class_count']==25002
 for stem in ['i04-aapt2-badging','i05-aapt2-manifest-xmltree','i06-apksigner-verify']:assert (d/'evidence'/(stem+'.rc')).read_text().strip()=='0'
 sig=(d/'evidence/i06-apksigner-verify.stdout.txt').read_text();assert 'Verifies' in sig and 'v2 scheme (APK Signature Scheme v2): true' in sig
 ledger=load(d/'rea-ledger.json');assert ledger['successful_package']['executed_by']=='outer(codex)' and ledger['successful_package']['artifact_sha256']==EXPECTED
 assert len(ledger['successful_methods'])==5 and ledger['method_requests_pending']==[]
 for q in load(d/'reuse-map.json')['rows']:assert q['target_runtime']=='NOT_TESTED' and q['runtime_provider']==q['runtime_namespace']=='UNKNOWN'
 assert len(load(d/'reuse-map.json')['rows'])==11
 for q in load(d/'source-index.json'):
  # All exact source snapshots are delivered in-packet, with no dependency on a changing MAIN.
  relative=q['snapshot_path'].split('/exact-static/',1)[1];p=d/relative
  assert p.stat().st_size==q.get('snapshot_bytes',q['bytes']) and sha(p)==q.get('snapshot_sha256',q['sha256']),q['path']
 if manifest:
  for q in load(d/'manifest.json')['files']:
   p=d/q['path'] if not q['path'].startswith('tools/') else d.parents[2]/q['path']
   assert p.stat().st_size==q['bytes'] and sha(p)==q['sha256'],q['path']
 if private:
  for q in load(d/'raw-index.json')['entries']:
   p=private/q['path'];assert p.stat().st_size==q['bytes'] and sha(p)==q['sha256'],q['path']
 return {'status':'PASS_STATIC_RECEIPTS_ONLY','elfs':32,'dexes':5,'native_declarations':881,'runtime':'NOT_TESTED','human':'PENDING','private_rehashed':bool(private)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--private',type=Path);a=p.parse_args();print(json.dumps(validate(D,a.private)))
