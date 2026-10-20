#!/usr/bin/env python3
"""Compile/run the actual pair lifecycle with explicit loader/OH fixture seams."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=Path(os.environ.get('T20_SOURCE_REPO',HERE.parents[1])).resolve()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 for rel,h in json.loads((HERE/'source-pins.json').read_text()).items():assert digest(REPO/rel)==h,rel
 if (HERE/'results.json').exists():
  result=json.loads((HERE/'results.json').read_text());assert result['device_calls']==0
  for rel,h in result['source_pins'].items():assert digest(HERE/rel)==h,rel
 r14=REPO/'benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline'
 r15=REPO/'benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline'
 out=Path(os.environ.get('T20_TEST_OUT',Path.home()/'.local/share/westlake/t20-provider-link/host'/str(time.time_ns())))
 out.mkdir(parents=True,exist_ok=False);rec={'scope':'host seams, real pair/R20/R14/R15, not OH execution','device_calls':0,'commands':[]}
 def run(name,argv):
  argv=list(map(str,argv));(out/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
  with (out/(name+'.stdout')).open('wb') as so,(out/(name+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(argv,stdout=so,stderr=se,timeout=30).returncode
   except subprocess.TimeoutExpired:rc=124
  (out/(name+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':name,'rc':rc});(out/'result.json').write_text(json.dumps(rec,indent=2)+'\n');assert rc==0,(name,rc,out)
 cc=shutil.which('cc');assert cc
 run('compile-pair',[cc,'-std=c11','-pthread','-I',HERE,'-I',HERE/'shim','-I',r15,HERE/'shim/test_pair.c',HERE/'entry.c',r14/'window_module.c',r15/'provider_adapter.c','-o',out/'pair-test'])
 for name in ['success','failed_retained','mixed_provider','mixed_slots','slot_resolver_drift','unreadable_slot','wrong_owner_offset','nonplayer','foreign_same_basename','player_base_drift']:run(name,[out/'pair-test',name])
 run('compile-entry',[cc,'-std=c11','-pthread','-I',r15,HERE/'test_entry.c',r14/'window_module.c',r15/'provider_adapter.c','-o',out/'entry-test'])
 run('real-posix-entry',[out/'entry-test'])
 print(json.dumps({'host_cases':11,'device_calls':0,'raw':str(out)}))
if __name__=='__main__':main()
