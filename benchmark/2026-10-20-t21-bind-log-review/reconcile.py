#!/usr/bin/env python3
"""Offline technical-only T20 log/maps reconciliation. Never calls a device."""
import argparse,collections,hashlib,json,re
from pathlib import Path
SHA=lambda b:hashlib.sha256(b).hexdigest()
OWNER={'owner_get':0x125dc0,'owner_acquire':0x125dfc,'owner_release':0x125e4c}
PROVIDER={'owner_bound_reference':0x66d78,'owner_bound_unreference':0x66ea4,'OH_NativeWindow_NativeWindowRequestBuffer':0x671ec,'OH_NativeWindow_GetBufferHandleFromNative':0x68d94,'OH_NativeBuffer_FromNativeWindowBuffer':0x64be0,'OH_NativeBuffer_Map':0x64700,'OH_NativeBuffer_Unmap':0x647b4,'OH_NativeWindow_NativeWindowFlushBuffer':0x67688,'OH_NativeWindow_NativeWindowAbortBuffer':0x67f20}
BIND=re.compile(rb'\[WL-R20-BIND\] kind=(\w+) fn=(0x[0-9a-f]+) base=(0x[0-9a-f]+) file=([^\s]+)$')
DONE=re.compile(rb'\[WL-R20-BIND\] result=(-?\d+) context=(0x[0-9a-f]+|\(nil\)) owner_base=(0x[0-9a-f]+) provider_base=(0x[0-9a-f]+)$')
PAIR=re.compile(rb'\[WL-R20-PAIR\] seq=(\d+) op=(\w+) window=(0x[0-9a-f]+|\(nil\)) caller=(0x[0-9a-f]+|\(nil\)) rc=(-?\d+) request=(\d+)/(-?\d+) handle=(\d+)/(-?\d+) convert=(\d+)/(-?\d+) map=(\d+)/(-?\d+) unmap=(\d+)/(-?\d+) flush=(\d+)/(-?\d+) abort=(\d+)/(-?\d+) retained=(\d+)$')
UNWRAP=re.compile(rb'\[WL-R20-UNWRAP\] seq=(\d+) wrapper=(0x[0-9a-f]+|\(nil\)) oh=(0x[0-9a-f]+|\(nil\)) rc=(-?\d+)$')
REFUSE=re.compile(rb'\[WL-R20-BIND\] refuse=([a-z_]+)(?: name=(\w+))?$')
def maps(data):
 out=[]
 for line in data.decode().splitlines():
  f=line.split(None,5)
  if len(f)!=6:continue
  try:lo,hi=[int(x,16) for x in f[0].split('-')];off=int(f[2],16);inode=int(f[4])
  except ValueError:continue
  out.append({'lo':lo,'hi':hi,'perms':f[1],'offset':off,'device':f[3],'inode':inode,'path':f[5]})
 return out
def location(rows,fn,base,path):
 start=[r for r in rows if r['lo']==base and r['offset']==0 and r['path']==path]
 hit=[r for r in rows if r['lo']<=fn<r['hi'] and 'x' in r['perms'] and r['path']==path]
 if len(start)!=1 or len(hit)!=1:return None
 a,b=start[0],hit[0]
 if (a['device'],a['inode'])!=(b['device'],b['inode']):return None
 return {'base':hex(base),'device':a['device'],'inode':a['inode'],'path':path,'executable_range':[hex(b['lo']),hex(b['hi'])]}
def reconcile(log,before,after,source_offset=0):
 assert source_offset>=0
 bm,am=maps(before),maps(after);events=[];members=collections.defaultdict(list);done=[];refusals=[];pairs=[];malformed=0;offset=source_offset
 for line in log.splitlines(keepends=True):
  i=line.find(b'[WL-R20-');pos=offset;offset+=len(line)
  if i<0:continue
  raw=line[i:].rstrip(b'\r\n');event={'source_offset':pos+i,'length':len(raw),'sha256':SHA(raw)}
  match=next(((name,pattern.fullmatch(raw)) for name,pattern in [('member',BIND),('result',DONE),('pair',PAIR),('unwrap',UNWRAP),('refusal',REFUSE)] if pattern.fullmatch(raw)),None)
  if not match:malformed+=1;continue
  kind,m=match;g=[v.decode() if v else None for v in m.groups()];event.update(type=kind,technical=raw.decode())
  if kind=='member':
   name,ptr,base,path=g;fn,base=int(ptr,16),int(base,16);expected=(OWNER|PROVIDER).get(name);want='liboh_adapter_bridge.so' if name in OWNER else 'libsurface.z.so';a=location(bm,fn,base,path);b=location(am,fn,base,path)
   event.update(kind=name,layout_match=expected is not None and fn-base==expected and Path(path).name==want and a is not None and a==b,mapping_before=a,mapping_after=b);members[name].append(event)
  elif kind=='result':done.append({'rc':int(g[0]),'context':g[1],'owner_base':g[2],'provider_base':g[3]})
  elif kind=='refusal':refusals.append(g)
  elif kind=='pair':
   stages={name:{'called':int(g[5+i*2]),'rc':int(g[6+i*2])} for i,name in enumerate(['request','handle','convert','map','unmap','flush','abort'])}
   pair={'seq':int(g[0]),'op':g[1],'window':g[2],'rc':int(g[4]),'stages':stages,'retained':int(g[-1]),'source_offset':pos+i};pairs.append(pair)
  events.append(event)
 missing=[name for name in OWNER|PROVIDER if len(members[name])!=1]
 valid=not missing and all(v[0]['layout_match'] for v in members.values()) and len(done)==1 and done[0]['rc']==0 and done[0]['context']!='(nil)' and not refusals and not malformed
 if valid:
  valid=all(v[0]['mapping_before']['base']==done[0]['owner_base' if k in OWNER else 'provider_base'] for k,v in members.items())
 failures=[p for p in pairs if p['rc']!=0]
 return {'device_calls':0,'binding_layout':'MATCH_OBSERVED_LAYOUT' if valid else 'UNKNOWN_OR_MISMATCH','missing_or_repeated_members':missing,'bind_results':done,'refusals':refusals,'malformed_marker_lines':malformed,'operation_counts':dict(collections.Counter(p['op']+':'+str(p['rc']) for p in pairs)),'first_observed_operation_failure':failures[0] if failures else None,'pairs':pairs,'events':events,'input_sha256':{'log':SHA(log),'maps_before':SHA(before),'maps_after':SHA(after)},'source_range':[source_offset,source_offset+len(log)],'limits':['Input identity/boot/birth/UID and transport completeness require outer receipts.','Actual ELF hashes and player lock/unlock GOT slots require separate fresh evidence.','This is one bounded log range; no failure line does not prove no failure.','Log layout match is not overall admission, frame motion or playback acceptance.']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--log',required=True,type=Path);p.add_argument('--maps-before',required=True,type=Path);p.add_argument('--maps-after',required=True,type=Path);p.add_argument('--source-offset',type=int,required=True);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 result=reconcile(a.log.read_bytes(),a.maps_before.read_bytes(),a.maps_after.read_bytes(),a.source_offset)
 with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['binding_layout','operation_counts','malformed_marker_lines','device_calls']}))
if __name__=='__main__':main()
