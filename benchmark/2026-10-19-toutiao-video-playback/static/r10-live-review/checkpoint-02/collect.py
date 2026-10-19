#!/usr/bin/env python3
"""Local exact ELF/GOT/record check. Never calls a device or compiler."""
from pathlib import Path
import hashlib,json,struct,shutil,subprocess,sys
D=Path(__file__).resolve().parent;R=next(p for p in D.parents if (p/'scripts/lab/run_facts.py').is_file());B=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
W=B/'video-r10-window-binding';P=B/'video-r10-play2';refs=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def bind(p):refs.append({'path':'BASE19/'+str(p.relative_to(B)),'sha256':sha(p),'size':p.stat().st_size});return p
j=json.loads(bind(W/'reads.json').read_text());assert (j['boot'],j['parent'],j['parent_birth'],j['child'],j['child_birth'])==('34309d1e-48b0-47c7-b8b1-732cdd7bce02',5160,7985,7080,9491)
assert j['identity_after_reads']=='same guarded boot/parent/child births'
bm=bind(W/'maps-before.txt').read_text().splitlines();am=bind(W/'maps-after.txt').read_text().splitlines()
objects={};verified=[]
for path,info in j['provider_files'].items():
 p=bind(W/info['local_file']);data=p.read_bytes();lines=info['identity'].splitlines();assert sha(p)==lines[0].split()[0]
 dev,ino=map(int,lines[1].split(':'));major=((dev>>8)&0xfff)|((dev>>32)&~0xfff);minor=(dev&255)|((dev>>12)&~255)
 rows=[x.split() for x in bm if x.split()[-1]==path];assert rows==[x.split() for x in am if x.split()[-1]==path]
 assert rows and all(int(x[4])==ino and tuple(int(y,16) for y in x[3].split(':'))==(major,minor) for x in rows)
 phoff=struct.unpack_from('<Q',data,32)[0];psz,pnum=struct.unpack_from('<HH',data,54)
 ph=[struct.unpack_from('<IIQQQQQQ',data,phoff+i*psz) for i in range(pnum)];loads=[x for x in ph if x[0]==1];candidates=set()
 for row in rows:
  lo=int(row[0].split('-')[0],16);off=int(row[2],16)
  options={lo-((x[3]&~4095)+off-(x[2]&~4095)) for x in loads if (x[2]&~4095)<=off<((x[2]+x[5]+4095)&~4095)}
  candidates.update(options)
 shoff=struct.unpack_from('<Q',data,40)[0];ss,sn=struct.unpack_from('<HH',data,58);secs=[struct.unpack_from('<IIQQQQIIQQ',data,shoff+i*ss) for i in range(sn)];dy=next(x for x in secs if x[1]==11);st=secs[dy[6]];strings=data[st[4]:st[4]+st[5]];symbols={}
 for o in range(dy[4],dy[4]+dy[5],dy[9]):
  n,inf,oth,ndx,v,size=struct.unpack_from('<IBBHQQ',data,o)
  if ndx:symbols[strings[n:].split(b'\0')[0].decode()]=v
 bound=[slot for slot in j['reads'] if any(row.split()[-1]==path for row in slot['value_maps'])]
 exact={int(slot['value'],16)-symbols[slot['label']] for slot in bound};assert len(exact)==1
 bias=next(iter(exact));assert bias in candidates
 for seg in loads:
  assert any(int(row[0].split('-')[0],16)==bias+(seg[3]&~4095) and int(row[2],16)==(seg[2]&~4095) for row in rows)
 objects[path]=(bias,symbols,data,loads)
 for slot in j['reads']:
  name=slot['label']
  if name in symbols and int(slot['value'],16)==bias+symbols[name]:
   verified.append({'function':name,'provider_sha256':sha(p),'provider_path':path,'elf_value':hex(symbols[name]),'bias':hex(bias),'actual':slot['value'],'got_address':slot['address']})
 idx=info['local_file'].split('-')[1].split('.')[0]
 for suffix in ['disassembly.json','disassembly.txt','disassembly.stderr.txt']:bind(W/('provider-'+idx+'-'+suffix))
 rc=json.loads((W/('provider-'+idx+'-disassembly.json')).read_text());assert rc['rc']==0 and rc['source_sha256']==sha(p)
assert len(verified)==8
shim='/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so';bias,sym,data,loads=objects[shim]
def word(va):
 seg=next(x for x in loads if x[3]<=va< x[3]+x[5]);return struct.unpack_from('<I',data,seg[2]+va-seg[3])[0]
assert sym['ANativeWindow_lock']==0x5e48 and sym['ANativeWindow_unlockAndPost']==0x5ff0
assert word(0x5f34)==0x52800269 and word(0x5f3c)==0x12800240 and word(0x5f44)==0xb9000109 and word(0x5f4c)==0xd65f03c0
assert word(0x6000)==0x52800269 and word(0x6004)==0x12800240 and word(0x6008)==0xb9000109 and word(0x6010)==0xd65f03c0
s=(W/'provider-1-disassembly.txt').read_text();start=s.index('0000000000005e48');end=s.index('0000000000005f50');last=s.index('0000000000005ff0')
(D/'shim-functions-excerpt.txt').write_text(s[start:end]+s[last:])
shutil.copyfile(W/'reads.json',D/'window-binding.json')
record=json.loads(bind(P/'record.json').read_text());view=D/'facts-layout/play2';view.mkdir(parents=True,exist_ok=True)
for shot in record['screenshots']:
 p=bind(P/Path(shot['path']).name);assert sha(p)==shot['sha256'];shutil.copyfile(p,view/p.name);shot['path']=p.name
(view/'record.json').write_text(json.dumps(record,indent=2)+'\n')
for name in ['child-before.stat','child-after.stat']:
 s=bind(P/name).read_text();a=s.split(') ',1)[1].split();assert int(s.split()[0])==7080 and a[0]=='S' and int(a[1])==5160 and int(a[19])==9491
p=bind(P/'child-full.stderr');raw=p.read_bytes();lines=raw.decode(errors='replace').splitlines();hits=[(i+1,s) for i,s in enumerate(lines) if '[WL-TTLOG ' in s]
result={'token':'video-2020-r10-live-review','scope':'PLAY2_AND_EXACT_ANW_BINDING_NOT_WINDOW_CLOSE','verified_function_bindings':verified,'lock_and_unlock_return':'Both exact normal return paths set errno19 and return -19; lock first-call path also emits diagnostics. Not a real native buffer lock implementation.','actual_failure':'play1 full stderr line69895 an_render.cpp drawPicture lock buffer ret:-19, continued in play2','limit':'Not a proof all video failures have one cause. Unlock invocation not separately proven. Getter zero cause/function table/object validity still pending. Provider GOT was read after first failure, with unchanged same-child identities, not a PC trace of the first call.','play2_full_stderr_sha256':sha(p),'captured_mirror_markers':raw.count(b'[WL-TTLOG '),'post_baseline_mirror_lines':sum(i>record['stderr_baseline_lines'] for i,s in hits),'last_mirror_line':hits[-1][0],'cap':4096,'coverage':'4096 captured markers reach cap; subsequent silence cannot exclude later events','window_lock_failure_lines':sum('Unable to lock window buffer' in s for i,s in hits),'visual':'Viewed t10/t25; t0/t5 identical to already viewed play1; t20 identical to t10. Same woman cover/play triangle. Clock/control differences do not establish content motion.','playback':'NOT_PASSED','audio':'UNKNOWN','rollback':'PENDING','device_calls':0}
assert result['captured_mirror_markers']==4096
(D/'results.json').write_text(json.dumps(result,indent=2)+'\n');(D/'private-source-index.json').write_text(json.dumps(refs,indent=2)+'\n')
r=subprocess.run([sys.executable,str(R/'scripts/lab/run_facts.py'),str(D/'facts-layout')],capture_output=True);assert r.returncode==0;(D/'facts.txt').write_bytes(r.stdout)
print(json.dumps({'bindings':len(verified),'mirrors':result['captured_mirror_markers'],'post_baseline':result['post_baseline_mirror_lines'],'lock_failures':result['window_lock_failure_lines']}));print(r.stdout.decode())
