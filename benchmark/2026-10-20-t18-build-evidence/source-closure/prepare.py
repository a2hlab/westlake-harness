#!/usr/bin/env python3
"""Read-only input verification; --write records a new source-closure preflight."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates preflight files, no archive.');return
 mainrepo=ROOT.parent/'westlake-harness';build=Path.home()/'.local/share/westlake/t18-production';argv=json.loads((build/'production-02/baseline-compile.argv.json').read_text());ws=Path(next(x.split('=',1)[1] for x in argv if x.startswith('--sysroot='))).parents[3]
 artifact=ws/'out-touch21/fd/bridge15/artifacts.json';art=json.loads(artifact.read_text());rows=[]
 for kind in ['sources','headers']:
  for rel,expected in art[kind].items():
   mapped='westlake-touch21/'+rel[len('westlake/'):] if rel.startswith('westlake/') else 'out-touch21/fd/bridge15/'+rel if rel.startswith('compat/') else rel
   p=ws/mapped;actual=sha(p) if p.is_file() else None
   rows.append(dict(role=kind,recorded_path=rel,mapped_path='$ORB_WS/'+mapped,expected_sha256=expected,actual_sha256=actual,bytes=p.stat().st_size if p.is_file() else None,match=actual==expected))
 assert len(art['sources'])==50 and len(art['headers'])==900 and all(r['match'] for r in rows)
 pinfile=mainrepo/'benchmark/2026-10-20-d4fa-bridge-closure/input-pins.json';pins=json.loads(pinfile.read_text());direct=[]
 for r in pins['files']:
  assert r['path'].startswith('$ORB_WS/');p=ws/r['path'][8:];assert p.is_file() and sha(p)==r['sha256'] and p.stat().st_size==r['bytes'];direct.append(r)
 reused=[]
 for r in pins['reused_objects']:
  s=r['mounted_path_alias'];assert s.startswith('$ORB_WS/');p=ws/s[8:];assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'];reused.append(dict(path=s,sha256=r['sha256'],bytes=r['bytes']))
 out=HERE/'preflight';out.mkdir(exist_ok=False)
 def dump(n,x):(out/n).write_text(json.dumps(x,indent=2)+'\n')
 dump('touch21-source-header-check.json',dict(artifact_sha256=sha(artifact),sources=50,headers=900,all_match=True,files=rows))
 dump('closure-pins-check.json',dict(main_pin_path=str(pinfile.relative_to(mainrepo)),main_pin_sha256=sha(pinfile),files=direct,reused_objects=reused))
 dump('plan.json',dict(status='SEPARATE_SOURCE_CLOSURE_BUNDLE_PREPARATION',first_archive_immutable='c6d4f34f8af201d12bb8e53000fe58eec6043d5f6197e36bfe608691e943305b',exact_sources_headers='touch21-source-header-check.json',explicit_selections=['out-touch21/fd/bridge15/{artifacts.json,objects,source-adapter_bridge.cpp,compat}','out-touch21/{build-fd.sh,build-fd.log,fd/bridge15.log}','out-focus34/incremental/{build.json,build-history.jsonl,*.log,objects}','out-ability38/{native-policy,native-stack}/artifacts.json + objects + compile/link logs','westlake-mc46 actual source and LICENSE','out-mc46/{relink,repro,patched}','toolchains/ohos-sdk/native/llvm/bin/{clang-15,lld}','TRIAGE46/benchmark/2026-09-26-toutiao-crash-triage/scripts/build_bridge_mc.py'],pending='Evolution independent actual-source/license git snapshot final listing; preserve separately without modifying first archive.',limits=['Original final mc46 full stdout/stderr/rc not found; remains unknown','Historical scripts retain original bytes privately; never rewritten as portable original logs','No rebuild or device action','No claim of whole-bridge source rebuild merely from source presence']))
 print(json.dumps(dict(source_match=50,header_match=900,direct_pins=len(direct),reused_objects=len(reused),device_calls=0,archive_created=False)))
if __name__=='__main__':main()
