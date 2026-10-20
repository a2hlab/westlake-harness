#!/usr/bin/env python3
"""Local-only intake of the fixed actual T30 production-01; no compiler/device calls."""
import argparse,hashlib,json,shutil
from pathlib import Path
RECEIPT='61ce357966aab01f559b3e324f0d991855e8321c469fa7b28cc8f5d31cedc986'
SHIM='7f8d75bbf09e28e2b57a4621f1181ff944e79e462b78707c620dd67aef0b0bcb'
BRIDGE='b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4'
REVIEW='fff53a2b14aef75da51a23e6e0e65145365fc1d46f3ffdfd9c65eaeb8ea1f2b7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--production',type=Path,required=True);ap.add_argument('--frozen',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 pending=Path(__file__).resolve().parent.parent;repo=next(x for x in pending.parents if (x/'scripts/lab/board_note.sh').exists());out=a.out.resolve();rel=out.relative_to(repo)
 assert not out.exists();assert sha(a.production/'receipt.json')==RECEIPT;r=read(a.production/'receipt.json')
 assert r['status']=='OFFLINE_CANDIDATE_PENDING_PEER_AND_RUNTIME' and len(r['commands'])==7 and all(x['rc']==0 for x in r['commands'])
 assert len(r['outputs'])==38 and r['abi_definitions']==78 and r['needed']==['libc.so'] and r['compiled_units']==2 and r['bridge_recompiled'] is False
 for n,v in r['outputs'].items():
  assert not Path(n).is_absolute() and '..' not in Path(n).parts
  f=a.production/n;assert sha(f)==v['sha256'] and f.stat().st_size==v['bytes'],n
 assert sha(a.production/'shim.so')==SHIM and (a.production/'shim.so').stat().st_size==107544
 assert sha(a.production/'bridge.so')==BRIDGE and (a.production/'bridge.so').stat().st_size==2023136
 assert sha(a.frozen/'review.json')==REVIEW
 for unit in ('r14','r15'):
  spec=r['frozen_manifest']['source_'+unit];assert sha(a.frozen/spec['path'])==spec['sha256']
 assert r['shim_exports']=={'ANativeWindow_lock':'0x72c8','ANativeWindow_unlockAndPost':'0x72dc','ANativeWindow_setBuffersGeometry':'0xf8bc'}
 out.mkdir(parents=True);e=out/'production-evidence';e.mkdir()
 # Public copies are explicitly sanitized, originals remain unchanged and hash-indexed.
 aliases=[(str(a.production.resolve()),'$T30_PRODUCTION'),(str(a.frozen.resolve()),'$T30_FROZEN'),(str(Path.home()),'$HOME')];aliases.sort(key=lambda x:-len(x[0]))
 for src,n in [(a.production/'receipt.json','receipt.public.json'),(a.frozen/'review.json','source-review.public.json'),(a.frozen/'pins.json','source-pins.public.json')]:
  text=src.read_text()
  for old,new in aliases:text=text.replace(old,new)
  assert '/Users/' not in text and '/home/' not in text
  (e/n).write_text(text)
 dump(e/'intake.json',{'status':'ACTUAL_OFFLINE_OUTPUTS_VERIFIED_NOT_DEVICE_ADMISSION','original_receipt_sha256':RECEIPT,'original_review_sha256':REVIEW,'outputs_verified':38,'commands_rc':[x['rc'] for x in r['commands']],'source_r14':r['frozen_manifest']['source_r14'],'source_r15':r['frozen_manifest']['source_r15'],'bridge':r['outputs']['bridge.so'],'shim':r['outputs']['shim.so'],'shim_exports':r['shim_exports'],'device_calls':0,'originals_alias':'$HOME/.local/share/westlake/t30-production','new_runtime_proof':False})
 refs=[{'path':str(rel/'production-evidence'/f.name),'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted(e.iterdir())]
 names=['executor.py','executor-source-pins.json','readonly-inputs.json','bridge-candidate.json','run5cd.before.reference.sh','run5cd.after.wid29.reference.sh','player-relocations.txt','reuse-index.json']
 for n in names:shutil.copyfile(pending/n,out/n)
 c=read(pending/'shim-candidate.json');c.update(after_sha256=SHIM,after_bytes=107544,build_status='PRODUCTION_BUILD_VERIFIED',production_refs=refs,production_commit=None,production_identity='T30 actual production-01; source review fixed; runtime UNKNOWN',artifact_location='$HOME/.local/share/westlake/t30-production/production-01/shim.so',production_receipt=next(x for x in refs if x['path'].endswith('receipt.public.json')));dump(out/'shim-candidate.json',c)
 p=read(pending/'parameters.json');p.update(status='T30_FINAL_DATA_NOT_ADMISSION');p['artifacts'][5].update(after_sha256=SHIM,after_bytes=107544);dump(out/'parameters.json',p)
 s=read(pending/'three-slot-admission.json');s.update(candidate_sha256=SHIM,status='STATIC_EXPORTS_VERIFIED_LIVE_UNKNOWN')
 for x in s['slots']:x['candidate_export_offset']=r['shim_exports'][x['symbol']]
 dump(out/'three-slot-admission.json',s)
 b=read(pending/'bridge-binding-pending.json');b.update(shim_sha256=SHIM,status='UNCHANGED_BRIDGE_NEW_SHIM_STATIC_GATE_LIVE_UNKNOWN');dump(out/'bridge-binding-pending.json',b)
 ad=read(pending/'admission.template.json');ad['status']='T30_FINAL_DATA_TEMPLATE_NOT_ADMISSION'
 for k,n in read(out/'reuse-index.json')['selfpins'].items():ad[k]=sha(out/n)
 dump(out/'admission.template.json',ad)
 print(json.dumps({'out':str(out),'shim':SHIM,'receipt':RECEIPT,'fresh_identity':'UNKNOWN'}))
if __name__=='__main__':main()
