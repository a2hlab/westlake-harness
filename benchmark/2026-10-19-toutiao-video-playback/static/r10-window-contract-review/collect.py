#!/usr/bin/env python3
"""Bounded local ELF/evidence inspection; no target execution, build or device calls."""
from pathlib import Path
import hashlib,json,struct,subprocess,shutil
D=Path(__file__).resolve().parent
R=next(p for p in D.parents if (p/'scripts/lab/lab_paths.py').is_file())
M=R.parent/'westlake-harness'; B=Path.home()/'.local/share/westlake/toutiao-resume-20261019'; B20=B.parent/'toutiao-resume-20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def elf(p):
 b=p.read_bytes();assert b[:6]==b'\x7fELF\x02\x01'
 shoff=struct.unpack_from('<Q',b,40)[0];es,n=struct.unpack_from('<HH',b,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*es) for i in range(n)]
 names={};needed=[]
 for s in sections:
  if s[1] not in [6,11]:continue
  st=sections[s[6]];strings=b[st[4]:st[4]+st[5]]
  def z(o):return strings[o:strings.index(0,o)].decode()
  for off in range(s[4],s[4]+s[5],s[9]):
   if s[1]==11:
    nm,info,other,idx,val,sz=struct.unpack_from('<IBBHQQ',b,off)
    if nm:names[z(nm)]={'value':hex(val),'size':sz,'defined':idx!=0}
   else:
    tag,v=struct.unpack_from('<qQ',b,off)
    if tag==1:needed.append(z(v))
 return names,needed
bridge=R.parent/'westlake-inputs/seal-artifacts-20261012/sha256/d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'
assert sha(bridge)==bridge.name
provider=B/'video-r10-window-binding/provider-0.so';assert sha(provider)=='76512d97758c308acf7baff4647f07db792c02b8fae2eda93399bd18eda03727'
syms,needed=elf(bridge)
assert not any(syms.get(s,{}).get('defined') for s in ['ANativeWindow_fromSurface','ANativeWindow_getFormat'])
assert 'libhwui.so' in needed
objdump=shutil.which('llvm-objdump');assert objdump
commands=[]
for name,path,symbol in [('bridge-unwrap',bridge,'oh_anw_get_oh'),('provider-delegate',provider,'bridge_symbol')]:
 argv=[objdump,'-d','--disassemble-symbols='+symbol,path.name]
 run=subprocess.run(argv,cwd=path.parent,capture_output=True);assert run.returncode==0
 (D/(name+'.stdout.txt')).write_bytes(run.stdout);(D/(name+'.stderr.txt')).write_bytes(run.stderr)
 commands.append({'input_sha256':sha(path),'tool_sha256':sha(Path(objdump).resolve()),'argv':['llvm-objdump',*argv[1:]],'rc':run.returncode,'stdout_sha256':hashlib.sha256(run.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(run.stderr).hexdigest()})
refs=[]
def bind(p,alias):refs.append({'path':alias,'sha256':sha(p),'bytes':p.stat().st_size})
for n in ['hwui-anw.json','hwui-anw.stdout','hwui-symbols.json','hwui-symbols.stdout']:
 bind(B20/'r10-window-source-independent'/n,'BASE20/r10-window-source-independent/'+n)
for n in ['reads.json']:
 bind(B/'video-r10-window-state'/n,'BASE19/video-r10-window-state/'+n)
bind(provider,'BASE19/video-r10-window-binding/provider-0.so')
bind(bridge,'WORKSPACES/westlake-inputs/seal-artifacts-20261012/sha256/'+bridge.name)
source_defs=[('sources/api-implementations/source-build-native691/westlake/framework/webview-shim/libandroid_webview_shim.c',[415,877,925,933,944,955,980]),('sources/api-implementations/source-build-native691/westlake/framework/webview-shim/webview_bionic_shim.c',[3765,3962,4053]),('sources/api-implementations/shared-native-production/related-source/framework/window/jni/oh_anativewindow_shim.cpp',[221,234,813])]
for rel,lines in source_defs:
 bind(M/rel,'MAIN/'+rel);refs[-1]['lines']=lines;refs[-1]['scope']='reference contract, not asserted exact deployed source'
reads=json.loads((B/'video-r10-window-state/reads.json').read_text());head=next(x for x in reads['reads'] if x['name']=='window_word_0x0')
low=int(head['value'],16)&0xffffffff;assert low!=0x5f776e64
result={'token':'video-2020-window-contract-cx','status':'CONDITIONAL_CALLER_SCOPED_REUSE_REQUIRES_OBJECT_AND_WINNER_EVIDENCE','bridge_sha256':sha(bridge),'bridge_needed':needed,'bridge_exports':{k:syms.get(k) for k in ['ANativeWindow_fromSurface','ANativeWindow_getFormat','oh_anw_get_oh','oh_anw_wrap']},'exact_unwrap':{'entry':'0x125a00','base_magic_offset':0,'base_magic':'0x5f776e64','adapter_magic_offset':'0xc8','adapter_magic':'0x414e5731','oh_pointer_offset':'0xc0','reject':'NULL for either magic mismatch'},'existing_head':{'address':head['address'],'first_word':head['value'],'low32':hex(low),'matches_base_magic':False,'limitation':'Only historical 64-byte head, read separately from rendering call; +c0/+c8 missing. Not proof of live object type or corruption.'},'from_surface':{'outer_winner':'actual player GOT -> provider765 +3b9c','inner_delegate':'bridge_symbol +37d4 calls dlsym(handle,name) at3814 and returns pointer; d720 stores handle, NOT resolved function','hwui_static':'a11c9154 +807238 calls oh_anw_get_oh; nonnull retains original and try_acquire; otherwise oh_anw_wrap; may return null','actual_inner_winner':'UNKNOWN: DT_NEEDED includes hwui but actual dlsym dependency/namespace winner not read'},'raw_oh_consumers':{'provider':'76512d97','getWidth':'3ca4 /3cec passes unchanged window to table call3cf8','getHeight':'3d14 /3d5c passes unchanged window to3d68','setGeometry':'3d84 /3e44 and3ec4 pass unchanged window','lock':'3ee4 /3f98 passes unchanged window to request3fa0','unlock':'42e4; source ownership must match paired lock state','native_ready':'1 proves init flag only, not object validity, successful geometry or buffer request'},'minimal_reuse':'If AdapterAnw is confirmed, unwrap at the player-only OH boundary for width/height/geometry/lock/unlock while preserving original AOSP object for acquire/release; use paired lock state and existing format/stride/fence/flush handling. Never pass raw OH pointer to wrapper release. Do not globally replace shared libandroid or shim for WebView callers. Raw-OH input requires its own provenance; do not treat unwrap NULL as automatically valid raw OH.','source_limit':'related-source oh_anw_get_oh has directPathLive; exact d4fa has two magic checks without that branch. native691 source getFormat calls OH directly whereas exact765 delegates. Use exact ELF as authority.','missing_minimal_evidence':['Actual inner dlsym winner from the same provider765 instance/namespace (not opaque d720 handle); function is not persistently cached in examined helper. Existing resolver/caller trace or exact loaded lookup graph needed, no guessed GOT slot.','Current video window pointer tied to latest fromSurface/render call; read +0, +c0, +c8 with same child birth and mapping guards; only after both exact magic checks may +c0 be interpreted as OH pointer. Historical address must not be reused blindly.','Exact d4fa/hwui instance binding for oh_anw_get_oh and OH table targets; no native_ready or maps-only promotion.'], 'regression_scope':'Preserve all non-player callers and WebView bindings; caller-directed selection must be demonstrated for actual libttmplayer. Existing frozen providers stay unchanged. Geometry and playback remain runtime acceptance items.','device_calls':0,'builds':0}
(D/'results.json').write_text(json.dumps(result,indent=2)+'\n');(D/'source-index.json').write_text(json.dumps(refs,indent=2)+'\n');(D/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print(json.dumps({'status':result['status'],'bridge_hash':sha(bridge),'head_magic_matches':False,'device_calls':0}))
