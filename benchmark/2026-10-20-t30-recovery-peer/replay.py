#!/usr/bin/env python3
"""Reuse actual T29 route fixture; only Request seam and an added test scenario change."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--window-module',type=Path);ap.add_argument('--provider-adapter',type=Path);ap.add_argument('--expect',choices=['baseline','recovery'],default='baseline');a=ap.parse_args()
 assert a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/'))
 a.out.mkdir(parents=True,exist_ok=False);v=a.out/'source';base=a.repo/'benchmark/2026-10-20-t29-window-observation';donor=base/'shim';shutil.copytree(donor,v)
 # Joint production changes the five owner offsets in pair/geometry. Use those exact sources.
 for n in ['pair.c','geometry.c']:shutil.copyfile(base/'production-01/derived'/n,v/'derived'/n)
 observer=a.repo/'benchmark/2026-10-20-t27-buffer-observation'
 pins=[{'path':str(f.relative_to(a.repo)),'sha256':sha(f)} for f in sorted(donor.rglob('*')) if f.suffix in ['.c','.h']]
 pins +=[{'path':str((base/'production-01/derived'/n).relative_to(a.repo)),'sha256':sha(base/'production-01/derived'/n)} for n in ['pair.c','geometry.c']]
 for n in ['observer.c','observer.h']:pins.append({'path':str((observer/n).relative_to(a.repo)),'sha256':sha(observer/n)})
 if a.window_module:
  assert a.expect=='recovery';shutil.copyfile(a.window_module,v/'derived/window_module.c')
 else:assert a.expect=='baseline'
 if a.provider_adapter:
  assert a.expect=='recovery';shutil.copyfile(a.provider_adapter,v/'derived/provider_adapter.c')
 test=v/'test_route.c';s=test.read_text();old=s
 s=s.replace('owner_image[0x175000]','owner_image[0x176000]')
 binding=json.loads((base/'production-01/owner-bindings.json').read_text())['offsets']
 for oldhex,name in [('0x125dc0','oh_anw_get_oh'),('0x125dfc','oh_anw_try_acquire'),('0x125e4c','oh_anw_try_release'),('0x1740a0','OH_NativeWindow_NativeObjectReference'),('0x173fc8','OH_NativeWindow_NativeObjectUnreference')]:s=s.replace(oldhex,binding[name])
 needle="request_calls++;event('Q');*out=(void*)&buffer_obj;*fd=-1;return request_error;"
 assert s.count(needle)==1
 s=s.replace(needle,"request_calls++;event('Q');if(!strncmp(mode,\"peer_\",5) && request_calls==1){*out=NULL;*fd=-1;return 40601000;}*out=(void*)&buffer_obj;*fd=-1;return request_error;")
 case=r'''
 if(!strncmp(mode,"peer_",5)){
  assert(!ANativeWindow_setBuffersGeometry(&wrapper,17,3,2));assert(refs==2);
  struct r14_buffer b;int first=ANativeWindow_lock(&wrapper,&b,NULL);
  assert(first==-EIO && !b.bits && !b.format && request_calls==1 && !map_calls && !unmap_calls && !flush_calls && !abort_calls);
  int first_refs=refs,first_cache=cache->entries[0].state,first_ac=acalls,first_rel=rcalls;
  struct r14_report report={0};int report_rc=r20_report(context,&wrapper,&report);
  int second=ANativeWindow_lock(&wrapper,&b,NULL);int unlock=999;
  fprintf(stderr,"[PEER-COUNTERS] first=%d second=%d requests=%u refs=%d first_refs=%d maps=%u flushes=%u cache=%d\n",first,second,request_calls,refs,first_refs,map_calls,flush_calls,cache->entries[0].state);
  if(!strcmp(mode,"peer_baseline")){
   assert(second==-EBUSY && request_calls==1 && refs==3);
   assert(report_rc==0 && report.request_rc==40601000 && report.retained==1);
   assert(first_cache==R26_FAILED && !map_calls && !flush_calls);
  }else{
   assert(first_refs==2 && second==0 && request_calls==2 && map_calls==1 && refs==3);
   unlock=ANativeWindow_unlockAndPost(&wrapper);assert(unlock==0 && flush_calls==1 && unmap_calls==1 && refs==2 && !abort_calls);
  }
  printf("{\"first\":%d,\"second\":%d,\"unlock\":%d,\"request_calls\":%u,\"map_calls\":%u,\"unmap_calls\":%u,\"flush_calls\":%u,\"abort_calls\":%u,\"first_refs\":%d,\"final_refs\":%d,\"first_cache_state\":%d,\"first_acquire_calls\":%d,\"first_release_calls\":%d,\"acquire_calls\":%d,\"release_calls\":%d,\"first_report_rc\":%d,\"first_report_raw\":%d,\"first_report_retained\":%u,\"journal\":\"%s\"}\n",first,second,unlock,request_calls,map_calls,unmap_calls,flush_calls,abort_calls,first_refs,refs,first_cache,first_ac,first_rel,acalls,rcalls,report_rc,report.request_rc,report.retained,journal);
  if(!strcmp(mode,"peer_recovery")){assert(!r20_destroy(context));assert(!r26_destroy(cache));assert(refs==1);}
  return 0;
 }
'''
 needle=' if(!strcmp(mode,"wrong_lock"))';assert s.count(needle)==1;s=s.replace(needle,case+needle);test.write_text(s)
 (a.out/'fixture-original.c').write_text(old)
 save(a.out/'source-pins.json',{'originals':pins,'fixture_original_sha256':hashlib.sha256(old.encode()).hexdigest(),'fixture_derived_sha256':sha(test),'window_module_sha256':sha(v/'derived/window_module.c'),'provider_adapter_sha256':sha(v/'derived/provider_adapter.c'),'expect':a.expect})
 def run(name,argv):
  argv=list(map(str,argv));save(a.out/(name+'.argv.json'),argv)
  with (a.out/(name+'.stdout')).open('wb') as o,(a.out/(name+'.stderr')).open('wb') as e:r=subprocess.run(argv,stdout=o,stderr=e,timeout=60)
  (a.out/(name+'.rc')).write_text(str(r.returncode)+'\n');assert r.returncode==0,(name,r.returncode)
 cc=shutil.which('clang');assert cc
 cmd=[cc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-pthread','-D_GNU_SOURCE=1','-DWL_T27_OBSERVER','-I'+str(v),'-I'+str(v/'derived'),'-I'+str(observer),test,v/'derived/window_module.c',v/'derived/provider_adapter.c',v/'derived/entry.c',v/'rgbx.c',v/'observation.c',v/'observe29.c',observer/'observer.c','-o',a.out/'fixture']
 run('build',cmd);run('run',[a.out/'fixture','peer_'+a.expect])
 facts=json.loads((a.out/'run.stdout').read_text());text=(a.out/'run.stderr').read_text()
 assert 'Q=1/1/40601000' in text and 'H=0/0/0 N=0/0/0 M=0/0/0' in text
 for row in pins:assert sha(a.repo/row['path'])==row['sha256']
 result={'status':'BASELINE_FAILURE_REPRODUCED_CANDIDATE_PENDING' if a.expect=='baseline' else 'CANDIDATE_REAL_ROUTE_RECOVERY_PASSED_HOST_ONLY','facts':facts,'device_calls':0,'production_builds':0,'host_builds':1,'window_module_sha256':sha(v/'derived/window_module.c'),'provider_adapter_sha256':sha(v/'derived/provider_adapter.c'),'fixture_sha256':sha(test),'compiler_sha256':sha(Path(cc))}
 save(a.out/'results.json',result);print(json.dumps(result))
if __name__=='__main__':main()
