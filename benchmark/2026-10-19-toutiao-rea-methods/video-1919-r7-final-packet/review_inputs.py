"""Offline review of exact recorded objects. No device or build invocation."""
from pathlib import Path
import hashlib,json,struct,collections,re,runpy
F=Path(__file__).resolve().parent;R=next(p for p in F.parents if (p/'scripts/lab/run_facts.py').is_file());M=R.parent/'westlake-harness';B=Path.home()/'.local/share/westlake/toutiao-resume-20261019';P=F.parent/'video-1919-r7-live-review'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
probe=M/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r5/retry-r6/read_log_state.py';assert h(probe)=='6812122e7eb7f8184a231c5ed6e2ccbf2712960a38d6a75fc77436e391bf6aa9'
m=runpy.run_path(str(probe),run_name='offline_module');s=B/'video-r7-log-slots1';rows=m['map_rows']((s/'maps-before.txt').read_text());after=m['map_rows']((s/'maps-after.txt').read_text());r=json.loads((s/'reads.json').read_text());vals={x['label']:int(x['value'],16) for x in r['reads']}
for name in m['PINS']:
 bias,path=m['bias_for'](name,rows);assert hex(bias)==r['biases'][name];sel=[x for x in rows if x['path']==path];assert sel==[x for x in after if x['path']==path]
 for phase in ['before','after']:
  ls=(s/(phase+'-'+name+'-identity.txt')).read_text().splitlines();assert ls[0].split()[0]==m['PINS'][name][1];dev,ino=map(int,ls[1].split(':'));pair=(((dev>>8)&0xfff)|((dev>>32)&~0xfff),(dev&255)|((dev>>12)&~255));assert all(tuple(int(v,16) for v in x['device'].split(':'))==pair and int(x['inode'])==ino for x in sel)
assert vals['player_log_print_GOT']==int(r['biases']['liblog.so'],16)+0x7548
assert vals['player_verbose_pointer']==int(r['biases']['libttmplayer.so'],16)+0x475bac
assert vals['player_verbose']==1 and vals['player_callback_enabled']==0 and vals['liblog_minimum_priority']==1
chain={x['label']:x for x in json.loads((B/'video-r7-logger-chain/reads.json').read_text())}
for key,expected in [('liblog_is_loggable_GOT',0x7fab480000+0x9ce8),('liblog_logger',0x7face40000+0x1eff0),('libbase_function_call',0x7fac400000+0x1b31dc),('libbase_function_payload',0x7fac400000+0x1b2fa4)]:assert int(chain[key]['value'],16)==expected
for k in ['liblog_logger','libbase_logger_object','libbase_function_object']:assert chain[k]['value']==chain[k+'_after']['value']
raw=B/'baseline-runtime-logger-readonly/liboh_android_runtime.so';d=raw.read_bytes();assert h(raw)=='8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1'
def readva(va,n):
 off=struct.unpack_from('<Q',d,32)[0];sz,num=struct.unpack_from('<HH',d,54)
 for i in range(num):
  t,fl,o,v,pa,fs,ms,a=struct.unpack_from('<IIQQQQQQ',d,off+sz*i)
  if t==1 and v<=va and va+n<=v+fs:return d[o+va-v:o+va-v+n]
 raise ValueError(hex(va))
fmt=readva(0x43a5c,11);assert fmt==b'[%s:%u] %s\0';severity=list(struct.unpack('<7i',readva(0x55a00,28)));assert severity==[3,3,4,5,6,7,7]
ls=(B/'video-r7-native-after/hilog.txt').read_text(errors='replace').splitlines();counts=collections.Counter();times=[]
for l in ls:
 mm=re.match(r'\s*([\d.]+)\s+\d+\s+\d+\s+([A-Z])\s+C00f00/([^:]+):',l)
 if mm:counts[(mm[2],mm[3])]+=1;times.append(float(mm[1]))
assert len(ls)==38077 and sum(counts.values())==30112
maps=(B/'video-r7-logger-chain/maps.txt').read_text();hilogrows=[l for l in maps.splitlines() if l.endswith('/system/lib64/chipset-sdk/libhilog.so')];assert len(hilogrows)==8 and all(l.split()[4]=='2552' for l in hilogrows)
zero=[l.split()[0].split('-')[0] for l in hilogrows if l.split()[2]=='00000000'];assert zero==['7d789c0000','7fb4980000']
rea=[]
for name in ['ev_b4304d56.txt','ev_f0efb750.txt']:
 f=B/'rea-native-originals-2246'/name;x=json.loads(f.read_text());assert x['subject']['digest']['sha256']=='b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02';src=x['raw_result']['value'];assert src==x['normalized_result'];rea.append({'path':'$HOME/.local/share/westlake/toutiao-resume-20261019/rea-native-originals-2246/'+name,'sha256':h(f),'evidence_id':x['evidence_id'],'body_read':True,'note':'Private exact tool result; not a verbatim Markdown summary and not claimed to be in r7 window archive.'})
out={'rc':0,'device_calls':0,'actual8slot_and_mapped_identity':'PASS','registered_chain_to_runtime_callback':'PASS','runtime_input_sha256':h(raw),'runtime_format_at43a5c':fmt[:-1].decode(),'runtime_severity_map':severity,'fprintf_base_severity':[5,6],'argument_positions':{'x5':'file','w6':'line','x7':'message'},'HiLogPrint_GOT_live_read':False,'liblog_get_minimum_GOT_live_read':False,'player_FILE_live_read':False,'hilog':{'lines':len(ls),'C00f00_lines':sum(counts.values()),'domain_time_range':[min(times),max(times)],'top_tags':[{'level':k[0],'tag':k[1],'count':v} for k,v in counts.most_common(12)],'two_hilog_offsetzero_starts':zero,'exact_caller_provider_unknown':True},'exact_REA_sources':rea,'conclusion':'Domain/chromium output is not a player-call trace. Full registered chain does not prove actual HiLogPrint provider or message passage. No logging or playback cause is established.'}
(P/'independent-checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'rc':0,'actual8slots':'PASS','format':'[%s:%u] %s','hilog_groups':2,'device_calls':0}))
