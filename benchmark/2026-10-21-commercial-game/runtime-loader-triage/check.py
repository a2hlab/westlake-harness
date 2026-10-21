#!/usr/bin/env python3
"""Read-only check of pinned static evidence; does not call devices or rebuild."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(d=D):
 idx=load(d/'evidence-index.json')
 for r in idx:
  p=d/r['snapshot'];assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
  lines=p.read_text().splitlines()
  for lo,hi in r['lines']:assert 1<=lo<=hi<=len(lines),(p,lo,hi)
 for n in ['llvm-index','outer-read-index']:
  for r in load(d/f'evidence/{n}.json'):assert sha(d/r['public'])==r['public_sha256']
 e=load(d/'evidence/exact-elf.json');assert len(e['system'])==5 and len(e['routes'])==6
 shared=[r['text'] for r in e['policy']['kBridgeSharedSonames']['entries']]
 assert shared==['libandroid.so','libEGL.so','liblog.so','libmediandk.so','libz.so','libwestlake_bionic_pthread_bridge.so','libstdc++.so']
 compat=next(x for x in e['system'] if x['name']=='libbionic_compat.so')
 assert not any(x.split('@')[0]=='__errno' for x in compat['defined'])
 gl=next(x for x in e['system'] if x['name']=='libGLESv2.so');assert gl['defined']==['_init','_fini'] and gl['needed']==['libc.so']
 rea=load(d/'rea-reuse.json');assert len(rea['existing_methods'])==5 and all(x['verified'] for x in rea['existing_methods']);assert rea['new_rea']=='NOT_EXECUTED'
 p=load(d/'provider-matrix.json');assert p['graphics_rewrite_required'] is False and p['same_batch_errno_required'] is False
 err=p['rows'][0];assert err['anticipated_key'] is None and err['next_files']==[]
 r=load(d/'results.json');assert r['child_loader_maps']=='MISSING' and r['runtime_PASS'] is False and r['device_calls']==0 and r['API_freeze']=='NONE'
 prov=load(d/'sources/benchmark/2026-10-21-commercial-game/normal-ui-01/log-provenance.json');assert prov['sha256']==r['log_sha256']
 excerpt=(d/'sources/benchmark/2026-10-21-commercial-game/normal-ui-01/exit-log-excerpt.txt').read_text()
 for needle in ['__errno','libGLESv2.so','nativeRestartActivityIndicator','exit with code:1']:assert needle in excerpt
 return {'status':'PASS','source_snapshots':len(idx),'REA_raw_reused':5,'system_ELFs':5,'route_ELFs':6,'runtime':'NOT_TESTED_BY_THIS_TASK','errno_terminal_causality':'UNPROVEN_DEFERRED'}
if __name__=='__main__':print(json.dumps(validate()))
