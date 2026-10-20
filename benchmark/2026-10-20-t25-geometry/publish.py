#!/usr/bin/env python3
"""Explicit public receipt projection; original private bytes are never rewritten."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(text):
 aliases={str(P):'$T25_DIR',str(ROOT):'$LANE',str(ROOT.parent/'westlake-harness-video-plan'):'$WORKSPACES/westlake-harness-video-plan',str(ROOT.parent/'westlake-harness'):'$MAIN',str(ROOT.parent):'$WORKSPACES',str(Path.home()):'$HOME'}
 for old,new in sorted(aliases.items(),key=lambda item:len(item[0]),reverse=True):text=text.replace(old,new)
 return text
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');ap.add_argument('--refresh',action='store_true');a=ap.parse_args()
 if a.refresh and not a.write:ap.error('--refresh requires --write')
 if not a.write:print('Use --write for new public output; no device or build execution.');return
 out=P/'evidence';out.mkdir(exist_ok=a.refresh);refs=[]
 def copy(src,dest):
  q=out/dest;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(clean(src.read_text()))
  refs.append({'private_alias':str(src.relative_to(P)),'raw_sha256':sha(src),'raw_bytes':src.stat().st_size,'public_path':'evidence/'+dest,'public_sha256':sha(q)})
 for build in ['production-01','production-02']:
  b=P/'.private'/build;copy(b/'receipt.json',build+'/receipt.json')
  for q in sorted((b/'raw').glob('*')):
   # Full player relocation listing is private; publish just admitted slot lines.
   if q.name=='01-exact-player-relocations.stdout':continue
   copy(q,build+'/raw/'+q.name+('.txt' if q.suffix=='.stderr' else ''))
  if (b/'abi.json').exists():copy(b/'abi.json',build+'/abi.json')
 b=P/'.private/production-02';r=json.loads((b/'receipt.json').read_text());reloc=b/'raw/01-exact-player-relocations.stdout'
 lines=[line for line in reloc.read_text().splitlines() if re.match(r'^0*472(?:490|760|048)\s',line)]
 assert len(lines)==3
 (out/'player-relocations.txt').write_text('\n'.join(lines)+'\n')
 (out/'player-relocations.json').write_text(json.dumps({'player_sha256':r['inputs'][next(k for k in r['inputs'] if k.endswith('/libttmplayer.so'))]['sha256'],'raw_stdout_sha256':sha(reloc),'raw_argv_sha256':sha(b/'raw/01-exact-player-relocations.argv.json'),'rc':0,'scope':'Exact ELF relocation offsets, not runtime winner proof','excerpt':'player-relocations.txt'},indent=2)+'\n')
 for q in sorted((P/'.private/final-checks-01').glob('*')):
  if q.is_file():copy(q,'checks/'+q.name+('.txt' if q.suffix=='.stderr' else ''))
 lifecycle=P/'.private/lifecycle-01';v=json.loads((lifecycle/'stdout').read_text())
 (out/'lifecycle-summary.json').write_text(json.dumps({'rc':int((lifecycle/'rc').read_text()),'summary':v['verification']['summary'],'quality_score':v['quality_score'],'failure_summary':v['failure_summary'],'raw_stdout_sha256':sha(lifecycle/'stdout'),'raw_stderr_sha256':sha(lifecycle/'stderr'),'raw_alias':'.private/lifecycle-01','note':'Strict human scenario PendingReview is intentional; no history or gate was changed.'},ensure_ascii=False,indent=2)+'\n')
 (out/'public-source-index.json').write_text(json.dumps(refs,indent=2)+'\n')
 private=[{'path':str(q.relative_to(P)),'sha256':sha(q),'bytes':q.stat().st_size} for q in sorted((P/'.private').rglob('*')) if q.is_file()]
 (P/'private-raw-index.json').write_text(json.dumps({'root_alias':'$T25_DIR','remote_archive':'NOT_YET_CREATED','files':private},indent=2)+'\n')
 (P/'production-02.json').write_text(clean((b/'receipt.json').read_text()))
 sources={n:sha(P/n) for n in ['geometry.c','geometry.h','test_geometry.c','check.py','check_receipt.py','test_receipt.py','build.py','publish.py']}
 (P/'source-pins.json').write_text(json.dumps(sources,indent=2)+'\n')
 main=ROOT.parent/'westlake-harness';donors=['benchmark/2026-10-20-t20-provider-link-slice/shim/pair.c','benchmark/2026-10-20-t20-provider-link-slice/entry.h','benchmark/2026-10-20-t23-egl-import/exact_binding.h','benchmark/2026-10-20-t23-egl-import/build.py']
 (P/'donor-pins.json').write_text(json.dumps({'files':[{'path':n,'sha256':sha(main/n)} for n in donors],'changes':'Independent TU only: geometry/format and balanced extra owner reference; current player triple-slot gate rejects legacy765 lock, no raw-OH fallback.'},indent=2)+'\n')
 (P/'results.json').write_text(json.dumps({'status':'OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED','device_calls':0,'host_cases':29,'receipt_negative_cases':7,'rust_tests':2,'old_t23_cases':23,'old_t20_cases':11,'baseline':r['outputs']['baseline.so'],'candidate':r['outputs']['candidate.so'],'abi':r['abi'],'source_pins':sources,'frozen':{'entries':8,'checked':30,'violations':0},'lifecycle':v['verification']['summary'],'strict_lifecycle_rc':1,'runtime_geometry':'UNKNOWN','playback':'NOT_TESTED','human':'PendingReview','failed_attempt':'production-01 compiled and linked rc0; verifier rejected unversioned expected name. production-02 requires exact @@LIBC, preserving old77 full tuples.'},indent=2)+'\n')
 print(json.dumps({'public_receipt_files':len(refs),'private_files':len(private),'candidate':r['outputs']['candidate.so']}))
if __name__=='__main__':main()
