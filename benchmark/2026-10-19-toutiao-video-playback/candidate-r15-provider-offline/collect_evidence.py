#!/usr/bin/env python3
"""Publish aliased build receipts and exact small journals; retain originals privately."""
import json, hashlib, os
from pathlib import Path
from build import HERE, ROOT, STATUS, sha, R14_PINS
from verify import verify

def main():
 evidence=HERE/'evidence';evidence.mkdir(exist_ok=True)
 sdk=Path(os.environ.get('OH_SDK_NATIVE','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native')).resolve()
 aliases=[(str(ROOT),'$T4_REPO'),(str(sdk),'$OH_SDK_NATIVE'),(str(Path.home()),'$HOME')]
 def alias(s):
  for a,b in aliases:s=s.replace(a,b)
  return s
 def write(name,obj):(evidence/name).write_text(json.dumps(obj,indent=2)+'\n')
 outputs={}
 for mode in ['host','oh']:
  out=HERE/'.private'/(mode+'-final');verify(out);raw=(out/'receipt.json').read_bytes();record=json.loads(raw)
  write(mode+'-receipt.json',{'representation':'path-aliased derived receipt; original bytes remain in private build directory','original':{'path':'$T4_REPO/'+str((out/'receipt.json').relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest()},'receipt':json.loads(alias(raw.decode()))})
  outputs[mode]={'receipt_sha256':sha(out/'receipt.json'),'artifacts':record['artifacts'],'dependencies':len(record['dependencies_before']),'groups':record['groups']}
 for group in ['pair','layout','failures','concurrency']:
  src=HERE/'.private/host-final/raw'/('30-'+group+'.stdout.txt');(evidence/(group+'.journal.jsonl')).write_bytes(src.read_bytes())
 src=HERE/'.private/oh-final/raw/20-readelf.stdout.txt';(evidence/'oh-readelf.txt').write_bytes(src.read_bytes())
 ver=HERE/'.private/verification'
 lifecycle=json.loads((ver/'lifecycle.stdout.txt').read_text())
 write('lifecycle-summary.json',{'rc':int((ver/'lifecycle.rc').read_text()),'quality_score':lifecycle['quality_score'],'lint_issues':lifecycle['lint_issues'],'summary':lifecycle['verification']['summary'],'human':'PendingReview','raw_sha256':sha(ver/'lifecycle.stdout.txt'),'scenarios':[{'name':x['scenario_name'],'verdict':x['verdict'],'explicit_tests':[{'test':y['test_name'],'passed':y['passed']} for y in x['evidence'] if y['type']=='test_output']} for x in lifecycle['verification']['results']]})
 (evidence/'rust-selectors.stdout.txt').write_text(alias((ver/'rust-selectors.stdout.txt').read_text()))
 index=[]
 for p in sorted((HERE/'.private').rglob('*')):
  if p.is_file():index.append({'path':'$T4_REPO/'+str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
 write('private-raw-index.json',{'scope':'all original commands/stdout/stderr/rc, build outputs and initial failed OH attempt; no raw file altered','remote_archive':'PENDING_OUTER','files':index})
 inputs=[]
 rels=['specs/toutiao-video-playback/project.spec.md','specs/toutiao-video-playback/t10-typed-provider-adapter.spec.md','benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/window_module.c','benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/window_module.h','benchmark/2026-10-19-toutiao-video-playback/static/r14-provider-next-review/results.json']
 for rel in rels:inputs.append({'repository':'t4','path':rel,'sha256':sha(ROOT/rel)})
 mainrepo=ROOT.parent/'westlake-harness'
 for suffix in ['exact-surface','exact-surface-internals','exact-surface-getters']:
  for name in ['source-index.json','results.json','llvm.txt']:
   rel='benchmark/2026-10-20-window-candidate-preflight/provider-abi/'+suffix+'/'+name
   inputs.append({'repository':'MAIN','path':rel,'sha256':sha(mainrepo/rel)})
 write('source-lock.json',{'inputs':inputs,'r14_pins':R14_PINS,'sdk_consumed_headers':'oh-receipt.json receipt.dependencies_before; original paths aliased','sources_unchanged':True})
 selector=sorted((HERE/'.private').glob('selector-receipt-*'))[0]
 negative=json.loads((selector/'result.json').read_text())['negative_cases']
 write('receipt-negatives.json',{'source':'$T4_REPO/'+str((selector/'result.json').relative_to(ROOT)),'sha256':sha(selector/'result.json'),'cases':negative})
 result={'token':'r15-provider-offline-ready','status':STATUS,'core_sha256':sha(HERE/'provider_adapter.c'),'header_sha256':sha(HERE/'provider_adapter.h'),'test_sha256':sha(HERE/'test_adapter.c'),'builds':outputs,'host_cases':44,'receipt_negatives':len(negative),'rust_selectors':{'passed':5,'failed':0,'raw_sha256':sha(ver/'rust-selectors.stdout.txt')},'lifecycle':{'rc':int((ver/'lifecycle.rc').read_text()),'summary':lifecycle['verification']['summary'],'quality_score':lifecycle['quality_score']},'device_calls':0,'shared_library':False,'actual_provider_binding':'UNKNOWN_NOT_TESTED','playback':'NOT_TESTED','expected_help':'toutiao conditional','failure_preserved':{'path':'.private/oh-01','reason':'SDK native_buffer.h needs caller stdbool.h; included before SDK headers in successor, original logs retained'},'human_review':'PendingReview','outer_rebuild':'User reports independent host44 and byte-identical OH object; separate outer receipt not replaced here'}
 (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'raw_files':len(index),'host_dependencies':outputs['host']['dependencies'],'oh_dependencies':outputs['oh']['dependencies'],'status':STATUS}))
if __name__=='__main__':main()
