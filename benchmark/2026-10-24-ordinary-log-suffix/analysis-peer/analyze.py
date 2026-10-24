#!/usr/bin/env python3
"""Offline suffix evidence. Outputs only allowlisted diagnostics and numeric summaries."""
from pathlib import Path
import collections,hashlib,json,re
OUT=Path(__file__).resolve().parent
H=Path.home()/'.local/share/westlake';C=H/'t122-hdc-outer-check-20261024/collection-01';S=H/'startup-stage-coverage-20261023/extended-01/head.stdout'
def sha(b):return hashlib.sha256(b).hexdigest()
def alias(p):return '$HOME/.local/share/westlake/'+str(p.relative_to(H))
collection=json.loads((C/'collection.json').read_text());sb=S.read_bytes();sl=sb.decode(errors='replace').splitlines()
assert sha(sb)=='2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6'
def hits(lines,needle,start=1):return [i for i,l in enumerate(lines,1) if i>=start and needle in l]
def conns(lines,start):
 d=collections.defaultdict(list)
 for i,l in enumerate(lines,1):
  if i>=start and ' connect ' in l:
   m=re.search(r'result=(-?\d+) errno=(\d+)',l)
   if m:d['result='+m[1]+' errno='+m[2]].append(i)
 return {k:{'count':len(v),'lines':v} for k,v in d.items()}
loads=['libnetworkpredictor.so','libwasm.so','libttopenssl.so','libavmdlbase.so','libavmdls.so','libavmdlv2.so','libavmdl.so','liblynx_v8_bridge.so','libquick.so']
rows=[]
for item in collection['files']:
 pid=item['pid'];p=C/f'{pid}-payload.stdout';b=p.read_bytes();old=H/f'spare-board-reboot-repeat-20261023/raw/06/log{pid}.stdout';ob=old.read_bytes();prefix=ob.split(b'---HEAD\n',1)[1][:131072]
 assert item['status']=='bound' and sha(ob)==item['old_raw_sha256']
 assert len(b)==item['bytes']==item['pre']['size'] and sha(b)==item['sha256']
 assert b[:131072]==prefix==(C/f'old-{pid}.prefix').read_bytes() and sha(prefix)==item['old_prefix_sha256']
 for k in ['dev','inode','size','mtime','ctime']:assert len({item[x][k] for x in ['old_pre','old_post','pre','post']})==1
 lines=b.decode(errors='replace').splitlines();start=b[:131072].count(b'\n')+1
 diagnostics=[]
 for lib in loads:
  f=[i for i,l in enumerate(lines,1) if i>=start and '[SOURCE-NATIVE-LOAD-FAIL]' in l and lib in l]
  if f:
   s=[i for i,l in enumerate(sl,1) if '[SOURCE-NATIVE-LOAD-FAIL]' in l and lib in l]
   diagnostics.append({'category':'native_load_failure','object':lib,'failure_lines':f,'success_lines':s,'exact_message_present_in_success':all(lines[i-1] in sl for i in f),'interpretation':'Observed dependency/load failure; also in success comparator, not sufficient causal discriminator'})
 for needle,cat in [('u_setDataDirectory symbol not found','ICU_symbol'),('sh: getprop: inaccessible or not found','getprop_command'),('A resource failed to call close.','resource_close_warning'),('A resource failed to call CursorWindow.close.','cursorwindow_close_warning'),('A resource failed to call AbstractCursor.close.','cursor_close_warning')]:
  f=hits(lines,needle,start)
  if f:diagnostics.append({'category':cat,'failure_lines':f,'success_lines':hits(sl,needle),'interpretation':'Ordinary warning/failure observed; no demonstrated blocking or feed dependency'})
 exceptions=[]
 for n in hits(lines,'org.json.JSONException:',start):
  assert lines[n-1]=='org.json.JSONException: Value <html><head><title>302 of type java.lang.String cannot be converted to JSONObject'
  stack=[{'line':i,'text':lines[i-1]} for i in range(n+1,min(n+9,len(lines)+1)) if lines[i-1].startswith('\tat ')]
  exceptions.append({'line':n,'text':lines[n-1],'stack':stack,'success_comparator_matching_lines':hits(sl,'org.json.JSONException:'),'interpretation':'Explicit JSON conversion exception with Java stack. Input text has HTML/title302; no actual HTTP status/header/URL binding, no proof of main-feed request or unhandled/fatal exception.'})
 stages={k:hits(lines,k,start) for k in ['createSession entry','flushed RS transaction after node create','EglManager::swapBuffers ENTRY','FATAL EXCEPTION','Caused by:','SSLHandshakeException','UnknownHostException','ConnectException','SocketTimeoutException']}
 # Broad lexical discovery includes all network terms; counts are not a proof of exhaustive semantic classification.
 broad=re.compile(r'error|except|fail|denied|missing|not found|no such|errno=[1-9]|result=-|ssl|cert|connect',re.I)
 discovery=[i for i,l in enumerate(lines,1) if i>=start and broad.search(l)]
 rows.append({'pid':pid,'path':alias(p),'sha256':sha(b),'bytes':len(b),'full_file_lines':len(lines),'newline_terminated':b.endswith(b'\n'),'suffix_offset_zero_based':131072,'suffix_bytes':len(b)-131072,'suffix_sha256':sha(b[131072:]),'suffix_first_full_file_line':start,'boundary_note':'First included line crosses old byte boundary and is reconstituted from the full file; all other reviewed lines are newly added. Original five-line collector wrapper is absent here.','identity':{'prefix_exact':True,'historical_stat_stable':True,'pre':item['pre'],'post':item['post'],'historical_boot':'ecb84d86-f22f-4622-9501-143a26f39cf1','limit':'Bind historical file via old prefix/stat and prior ps PID; not a fresh child-birth proof. Collection boot is not file creation boot.'},'diagnostics':diagnostics,'json_exceptions':exceptions,'ordinary_connect_return_values':conns(lines,start),'stage_and_exception_marker_lines':stages,'broad_discovery_lines':discovery,'last_complete_line':len(lines)})
result={'task':'T122 ordinary suffix analysis peer','status':'NEW_RESPONSE_PARSE_EXCEPTION_NO_IMPLEMENTABLE_PUBLIC_API_CANDIDATE','collection':{'path':alias(C/'collection.json'),'sha256':sha((C/'collection.json').read_bytes()),'identity_receipt':{'path':alias(C/'identity.stdout'),'sha256':sha((C/'identity.stdout').read_bytes())}},'files':rows,'success_comparator':{'path':alias(S),'sha256':sha(sb),'bytes':len(sb),'lines':len(sl),'pid':6291,'stage_markers':{k:hits(sl,k) for k in ['application-ready cache-republish=OK','AFTER scheduleTransaction OK','createSession entry','flushed RS transaction after node create','EglManager::swapBuffers ENTRY','org.json.JSONException:']},'connect_return_values':{k:{'count':v['count'],'first_lines':v['lines'][:8]} for k,v in conns(sl,1).items()}},'conclusion':{'new_observed_error':'Both failure suffixes print HTML/title302-to-JSONObject exceptions through LJSONObject and com.jdwx.sdk.util.b.run; none in this T95 prefix.','implementation_candidate':None,'candidate_reason':'No bound request/response status or public API contract violation; caller is application/SDK stack. Correctly rejecting non-JSON input does not itself demonstrate a JSON API defect. No source search or change justified.','ordinary_render_progress':'Both failure suffixes reach WMC createSession and RS node-create flush, so not wholly pre-window initialization. The selected swapBuffers ENTRY marker is absent there and present in T95; absence is only log coverage, not proof no rendering or cause.','network':'All ordinary connect return-value records retained, including negative results; no broad-word exclusion. Numeric errno results are not classified as fatal service failures without socket/operation context. T95 has different network results/conditions, not a matched-request control.'},'limits':['Only added suffixes semantically reviewed; old prefix bytes used solely for identity and boundary-line reconstruction.','Complete captured bytes are complete files at the two stable stat observations, not guaranteed complete process lifetime or all buffered logs.','T95 is successful61b child6291; failures are5cd7011/9860. Different board/run/network state, no matching request or successful5cd7111 log.','No unique marker establishes Activity completion or first content frame; no exact cross-clock timing inference.','Broad lexical discovery includes connect/ssl/cert/errno; no claim that keywords exhaust all possible ordinary API defects. HTML302 text is not a verified HTTP302 status.','Shared messages may participate in timing/state-specific failure; shared presence does not universally exonerate them.','No protected mechanisms, memory/signal/exit attribution, stopped object or runtime implementation analysis.'], 'next_evidence_gap':'If separately tasked, use existing ordinary request diagnostics to bind the specific com.jdwx.sdk parse operation to response status/content type/redirect behavior and its consumer; no URL/token/body collection or new device action performed here.','actions':{'device':0,'deployment':0,'REA':0,'implementation_source_reads':0,'runtime_changes':0}}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'suffix_lines':{str(x['pid']):[x['suffix_first_full_file_line'],x['full_file_lines']] for x in rows},'exceptions':{str(x['pid']):[e['line'] for e in x['json_exceptions']] for x in rows}},ensure_ascii=False))
