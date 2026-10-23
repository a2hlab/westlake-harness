from pathlib import Path
import json,re,hashlib,datetime
out=Path(__file__).resolve().parent
base=Path.home()/'.local/share/westlake'
raw=base/'spare-board-reboot-repeat-20261023/raw'
success=base/'startup-stage-coverage-20261023/extended-01/head.stdout'
h=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return {'path':str(p).replace(str(Path.home()),'$HOME'),'bytes':len(b),'sha256':h(b)}
assert h(success.read_bytes())=='2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6'
logs={'6291':success.read_text(errors='replace').splitlines()};identities={};pins={'6291':pin(success)}
for pid,sample in [('7011','p30'),('9860','p60')]:
 p=raw/'06'/f'log{pid}.stdout';b=p.read_bytes();lines=b.decode(errors='replace').splitlines();start=b.index(b'---HEAD\n')+len(b'---HEAD\n');end=b.index(b'\n---END',start);payload=b[start:end]
 assert len(payload)==131072
 stats=[(i,l.split()) for i,l in enumerate(lines,1) if l.startswith('STAT ')]
 assert len(stats)==2
 assert stats[0][1][1:4]==stats[1][1][1:4] and stats[0][1][5:]==stats[1][1][5:]
 assert lines[0]==(raw/'NEW_BOOT').read_text().strip()
 assert str(pid) in lines[5]
 rc=(raw/'06'/f'log{pid}.rc').read_text().strip();assert rc=='0'
 assert (raw/'06'/f'log{pid}.stderr').stat().st_size==0
 ps=(raw/'05'/f'{sample}.stdout').read_text().splitlines();row=next(({'line':i,'text':l} for i,l in enumerate(ps,1) if re.match(r'\s*'+pid+r'\s+5201\s+\d+\s+com.ss.android.article.news$',l)),None);assert row
 mtime=int(stats[0][1][5]);identities[pid]={'boot':lines[0],'capture_device_date':lines[2],'mtime_epoch':mtime,'mtime_utc':datetime.datetime.fromtimestamp(mtime,datetime.timezone.utc).isoformat(),'original_size_bytes':int(stats[0][1][3]),'device_inode':stats[0][1][2],'stat_before_line':stats[0][0],'stat_after_line':stats[1][0],'stat_size_inode_mtime_unchanged':True,'captured_prefix_bytes':len(payload),'prefix_sha256':h(payload),'raw_prefix_first_line':6,'raw_prefix_last_line':len(payload.splitlines())+5,'prefix_last_line_complete':payload.endswith(b'\n'),'rc':0,'stderr_bytes':0,'ps_receipt':pin(raw/'05'/f'{sample}.stdout'),'ps_row':row,'identity_limit':'Filename plus contemporaneous ps and log PID fields; not a birth-tick proof.'}
 logs[pid]=lines;pins[pid]=pin(p)
 for ext in ['argv','rc','stderr','start','end']:pins[f'{pid}.{ext}']=pin(raw/'06'/f'log{pid}.{ext}')
patterns={
 'typeface_symbol_warning':'oh_typeface_mark_child unavailable',
 'activity_manager_fallback':'real adapter ctor FAILED',
 'input_manager_field_exception':'InputManagerGlobal.sService not found',
 'unsupported_class_loader':'Unsupported class loader',
 'plugin_authority':'Unknown authority com.ss.android.article.news.pm.PPMP',
 'sysoptimizer_symbol':'libsysoptimizer.so: _ZNSt6__ndk18ios_baseD2Ev: symbol not found',
 'wasm_symbol':'libwasm.so: _ZNKSt6__ndk18ios_base6getlocEv: symbol not found',
 'resource_close_warning':'A resource failed to call',
 'hotfix_metadata_missing':'hotfix-root/install/',
 'toutiao_metadata_missing':"toutiao.dm': No such file",
 'webview_metadata_missing':"webview-t.dm': No such file",
 'class_not_found':'ClassNotFoundException',
 'no_class_def':'NoClassDefFoundError',
 'no_such_method':'NoSuchMethodError',
 'unsatisfied_link_exception':'UnsatisfiedLinkError',
 'initializer_exception':'ExceptionInInitializerError',
 'dns_name_error':'EAI_NONAME',
 'network_unreachable':'ENETUNREACH'}
comparison={}
for name,pattern in patterns.items():
 entries={pid:[i for i,l in enumerate(ls,1) if pattern in l] for pid,ls in logs.items()}
 comparison[name]={'match':pattern,'raw_line_numbers':entries,'classification':'shared_with_success' if entries['6291'] and (entries['7011'] or entries['9860']) else 'not_observed_in_failure_prefixes' if not(entries['7011'] or entries['9860']) else 'new_in_bounded_comparison'}
phases={}
for name,pat in {'jni_registration':'kRegJNI loop done: 38 ok, 0 failed','ams_fallback_installed':'IActivityManagerSingleton.mInstance installed','input_manager_stage_completed':'J_after_installInputManagerAdapter','application_ready':'application-ready cache-republish=OK','feature_published':'application=ready feature=published','activity_transaction_posted':'AFTER scheduleTransaction OK'}.items():phases[name]={pid:[i for i,l in enumerate(ls,1) if pat in l] for pid,ls in logs.items()}
def norm(l):
 l=re.sub(r'^nullptr\s+\w\s+\d\d-\d\d\s+\d\d:\d\d:\d\d\s+\d+\s+\d+\s+','',l);l=re.sub(r'0x[0-9a-fA-F]+|@[0-9a-fA-F]+','<hex>',l);return re.sub(r'\d+','N',l)
ss={norm(l) for l in logs['6291']};unmatched={}
for pid in ['7011','9860']:
 found=[]
 for i,l in enumerate(logs[pid],1):
  if re.search(r'exception|error|failed|failure|unsupported|not found|unable|cannot|denied|missing',l,re.I) and not re.search(r'crash|signal|sigchain|sigsegv|npth|guardian|watchdog|reentry|malloc|heap|fault|memtrack|memory|token|credential|https?://|socket|connect|ssl|cert|netsys|NATIVENET|errCode=0|error=0|errno=',l,re.I) and norm(l) not in ss:found.append(i)
 unmatched[pid]=found
result={'task':'T113','status':'no_candidate','inputs':pins,'identity':identities,'comparison':comparison,'ordinary_progress':phases,'bounded_normalized_unmatched_error_lines':unmatched,'coverage':{'success_bytes':success.stat().st_size,'success_lines':len(logs['6291']),'failure_prefix_bytes_each':131072,'failure_payload_lines':{pid:identities[pid]['raw_prefix_last_line']-5 for pid in identities},'line_number_convention':'All references use original .stdout lines including five-line collector header for failures. T95 has no collector wrapper.','endpoints':{'7011':'Partial [OHServ record; no completion inference','9860':'Partial ordinary network record; address suppressed'},'whole_failure_logs_reviewed':False},'candidate':None,'conclusion':'No new and demonstrated blocking public API/class/service initialization failure found in these prefixes. Shared warnings alone do not establish cause; timing, state and uncollected-suffix interactions are not excluded.','limits':['128 KiB failure prefixes are shorter than their 368251/314796-byte files and the 4 MiB success prefix.','Different stage interleaving and counts are not durations or causal evidence.','scheduleTransaction OK is dispatch progress, not first-frame or Activity completion.','Normalized textual screening is bounded and can merge numeric variants; explicit comparison rows are primary evidence.','No signal, memory, protection-mechanism or stopped-object attribution; no device/REA/source calls.']}
(out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'no_candidate','prefixes':{pid:{'mtime_utc':v['mtime_utc'],'bytes':v['captured_prefix_bytes'],'payload_lines':v['raw_prefix_last_line']-5} for pid,v in identities.items()},'unmatched':unmatched},ensure_ascii=False))
