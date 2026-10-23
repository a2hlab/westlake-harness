#!/usr/bin/env python3
"""Bounded offline, allowlisted extraction from T95 ordinary startup prefix."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path.home()/'.local/share/westlake/startup-stage-coverage-20261023/head.stdout');p.add_argument('--old-prefix',type=Path,default=Path.home()/'.local/share/westlake/success-startup-log-20261023/head.stdout');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
b=a.input.read_bytes();old=a.old_prefix.read_bytes();ls=b.decode().splitlines();sha=hashlib.sha256(b).hexdigest()
assert sha=='4eb388bf71be98f2676db57dace507a52346b743315e5a0daf6a582d388dcfaa'
assert len(b)==131072 and len(ls)==1583 and b.startswith(old)
assert hashlib.sha256(old).hexdigest()=='3eabb43dff55b5f6ca31569a25131ba7f8474487f9daf29c5c21f4621407202d'
anchors=[];verifications=[];counters=[]
for i,l in enumerate(ls,1):
 m=re.match(r'nullptr\s+\w\s+(\d\d-\d\d)\s+(\d\d:\d\d:\d\d)\s+(\d+)\s+(\d+)\s+',l)
 if m:
  anchor={'line':i,'date_literal':m[1],'time_literal':m[2],'pid':int(m[3]),'tid':int(m[4]),'precision':'one second'};anchors.append(anchor)
  v=re.search(r'Verification of (.*?) took ([\d.]+)ms',l)
  if v:verifications.append(dict(anchor,operation=v[1],reported_duration_ms=float(v[2]),limit='Explicit reported duration; not CPU time, source-bound defect, or entire startup interval.'))
 if l.startswith(('[TOUCH21-POLL]','[TOUCH21-WAKE]','[TOUCH21-QUEUE]')):
  m=re.search(r'now=(\d+) tid=(\d+)',l)
  if m:counters.append({'line':i,'now_raw':int(m[1]),'tid':int(m[2])})
stage_lines=[506,1172,1411,1419,1420,1421]
stages=[{'line':i,'excerpt':ls[i-1],'timestamp':None,'meaning':'Ordinary checkpoint only; no elapsed duration or rendered-frame success inferred.'} for i in stage_lines]
failures=[]
for label,needle,excerpt in [
 ('name_resolution','android_getaddrinfo failed: EAI_NONAME','android_getaddrinfo failed: EAI_NONAME (Name does not resolve)'),
 ('name_resolution_errno','android_getaddrinfo failed: ENOENT','android_getaddrinfo failed: ENOENT (No such file or directory)'),
 ('network_unreachable','sendto failed: ENETUNREACH','sendto failed: ENETUNREACH (Network unreachable)'),
 ('native_dependency','_ZNSt6__ndk18ios_baseD2Ev: symbol not found','libsysoptimizer.so: _ZNSt6__ndk18ios_baseD2Ev: symbol not found'),
 ('plugin_provider','Unknown authority com.ss.android.article.news.pm.PPMP','Unknown authority com.ss.android.article.news.pm.PPMP'),
 ('webview_archive_metadata',"webview-t.dm': No such file",'webview-t.dm: No such file or directory'),
 ('webview_extra_dex','Unable to find entry classes3.dex','Unable to find entry classes3.dex')]:
 rows=[i for i,l in enumerate(ls,1) if i>300 and needle in l]
 if rows:failures.append({'category':label,'lines':rows,'safe_excerpt':excerpt,'timestamp':None,'causal_status':'No fatality, required-dependency status or latency attribution established.'})
r={'task':'T95 ordinary startup stage coverage','status':'PARTIAL_STARTUP_COVERAGE_CAUSE_UNKNOWN','executor':'Outer collected; Codex offline extraction only','input':{'sha256':sha,'bytes':len(b),'lines':len(ls),'old_T93_prefix_equal':True,'old_prefix_bytes':len(old),'old_prefix_sha256':hashlib.sha256(old).hexdigest(),'ends_with_newline':b.endswith(b'\n')},'identity':'Same-boot collection attributed to outer; explicit timestamp/PID6291 fields retained. Untimestamped lines inherit only file context, not an invented per-line timestamp.','timestamp_anchors':anchors,'explicit_timed_operations':verifications,'ordinary_checkpoints':stages,'visible_ordinary_failures':failures,'raw_now':{'unit':'unknown (T94 unchanged)','clock_domain':'unknown','conversion_performed':False,'records':counters},'end_of_fragment':{'line1582':'SOURCE-NATIVE-LOAD of libwebviewchromium.so','line1583_safe_exact_prefix':ls[-1],'line1583_is_partial':not b.endswith(b'\n'),'stage':'Beginning native loading/loader record for WebView, after archive scanning and MainActivity launch transaction posting.','native_load_completed':'unknown','first_frame_completed':'unknown','coverage_to_first_T92_trace_marker':'unknown: no explicit content::Start match or clock-bound completion marker; final raw now cannot be aligned by numerical resemblance.'},'interpretation':'MainActivity scheduling success is posting, not proof of onCreate completion or first render. Network/native dependency warnings are ordinary application log content, not transport errors or established causes of startup latency.','optimization_candidate':None,'one_gap':'Prefix truncates mid-WebView-loader record and lacks clock-bound native-load/first-render completion; no concrete phase explains the remaining time to the known successful feed.','privacy':'No raw log copy, tokens, pointer/network addresses, URLs or user content in exported fields.','actions':{'device_calls':0,'deployments':0,'source_reads':0,'REA_calls':0,'git_calls':0,'tmp_used':False,'commit':'Not attempted per user instruction about known Git permissions.'}}
# The final partial loader line contains only a library path, not network or pointer fields.
assert not re.search(r'https?://|token|password|0x[0-9a-f]+',r['end_of_fragment']['line1583_safe_exact_prefix'],re.I)
a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sha_verified':True,'prefix_equal':True,'timed_operations':verifications,'last_timestamp_anchor':anchors[-1],'last_line_partial':not b.endswith(b'\n'),'status':r['status']}))
