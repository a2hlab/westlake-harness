"""Summarize each original app instance; literal errno=13 and Permission denied both count."""
from boardstub48 import *
rows=[]
for r in sorted(R.glob('*-r[0-9]*')):
 if not (r/'result.json').exists() or (r/'user-stop.json').exists():continue
 d=json.loads((r/'device-report.json').read_text());pid=d['child']
 samples=[json.loads(s) for s in (r/'samples.jsonl').read_text().splitlines()]
 states=[]
 for sample in samples:
  lines=sample['output'].splitlines();up=float(lines[0].split()[0])
  line=next((s for s in lines if s.startswith(str(pid)+' (')),None)
  f=line.rsplit(') ',1)[1].split() if line else []
  alive=bool(f and f[0]!='Z' and f[19]==d['birth'])
  states.append({'uptime':up,'alive':alive,'age':up-int(d['birth'])/100,'symlink':'-> /data/local/tmp/asx/lib/arm64-v8a/libmetasec_ml.so' in sample['output']})
 log=(r/'child.stderr').read_text(errors='replace');lines=log.splitlines()
 terminal=[l for l in (r/'parent.log').read_text(errors='replace').splitlines() if l.startswith('[WESTLAKE-REAP] child '+str(pid)+' ')]
 errors=[l for l in lines if l.startswith("[UNCAUGHT] thread='platform-back-handler'") and 'metasec' in l]
 eacces=[l for l in errors if 'errno=13' in l or 'Permission denied' in l]
 inputs=[json.loads(l) for l in (r/'inputs.jsonl').read_text().splitlines()] if (r/'inputs.jsonl').exists() else []
 consent_inputs=[i for i in inputs if '-d 600 1273' in i['command']]
 consent=float(consent_inputs[0]['output'].split()[0]) if consent_inputs else None
 clicks=[float(i['output'].split()[0]) for i in inputs if '-d 380 295' in i['command']]
 resumed=[l for l in lines if l.startswith('[ABILITY38-RESUMED]')]
 # Concurrent native logging can prefix a real marker on the same line.
 # Match the exact lifecycle record, never an Activity substring in settings JSON.
 entry='[B47-SLA] ENTRY bundle=com.ss.android.article.news ability=com.ss.android.detail.feature.detail2.view.NewDetailActivity recordId='
 detail=[l[l.index(entry):] for l in lines if entry in l]
 detail_position=max((i for i,l in enumerate(lines) if entry in l),default=-1)
 detail_resumed=[l for l in lines[detail_position+1:] if l.startswith('[ABILITY38-RESUMED]')] if detail_position>=0 else []
 last=states[-1];alive_age=max([s['age'] for s in states if s['alive']],default=0)
 # monitor checks liveness again after the composite sample; it may observe
 # death in that small gap. Do not turn the earlier stat into an alive result.
 result=json.loads((r/'result.json').read_text())
 final_alive=result['original_alive_at_end']
 # Java uptime is milliseconds; /proc uptime is seconds and birth is ticks.
 resume_s=int(re.search(r'uptime=(\d+)',detail_resumed[-1])[1])/1000 if detail_resumed else None
 assert resume_s is None or resume_s <= last['uptime'] + 1, (r.name,resume_s,last)
 row={'round':r.name,'pid':pid,'terminal':terminal[-1] if terminal else None,
      'last_observed_alive_age_s':alive_age,'end_age_s':last['age'],'alive_at_end':final_alive,
      'startup_over_180s':alive_age>=180,'consent_uptime':consent,
      'alive_after_consent_s':(states[-1]['uptime']-consent) if consent and final_alive else None,
      'article_inputs_uptime':clicks,'detail_entry':detail,'resumed':resumed,
      'last_resumed_uptime_s':resume_s,
      'alive_after_last_resumed_s':last['uptime']-resume_s if resume_s is not None and final_alive else None,
      'platform_back_handler_errors':errors,'metasec_eacces_count':len(eacces),
      'metasec_ule_count':len(errors),
      'sensor_relocation_errors':[l for l in lines if 'ASensor' in l and 'symbol not found' in l],
      'metasec_missing_symbols':sorted(set(m[1] for l in lines if 'libmetasec_ml.so' in l and (m:=re.search(r': ([A-Za-z_][A-Za-z_0-9]*): symbol not found',l)))),
      'metasec_ule_to_main_exit':bool(errors and 'J_invokeStaticMain_main_threw' in log and 'X.DEv' in log and terminal and 'exited(1)' in terminal[-1]),
      'eacces_to_main_exit':bool(eacces and 'J_invokeStaticMain_main_threw' in log and 'X.DEv' in log and terminal and 'exited(1)' in terminal[-1]),
      'null_looper_main':bool('J_invokeStaticMain_main_threw' in log and 'X.DEv' in log),
      'symlink_samples':sum(s['symlink'] for s in states),'samples':len(states),
      'literal_errno13_count':sum('app_lib/libmetasec_ml.so: failed to map library' in l and 'errno=13' in l for l in lines),
      'fatal_headers':[l for l in lines if l.startswith('Fatal signal')],
      'reuse_markers':[l for l in lines if l.startswith('[SOURCE-NATIVE-IDENTICAL-COPY]') and 'metasec' in l],
      'load_failures':[l for l in lines if l.startswith('[SOURCE-NATIVE-LOAD-FAIL]') and 'metasec' in l],
      'cppcrash_heads':{p.name:p.read_text(errors='replace').split('Registers:',1)[0] for p in r.glob('cppcrash-*.txt')}}
 (r/'summary.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
 refusal=[l for l in lines if 'refusing self-trapping library:' in l and ('libnpth_xasan' in l or 'libnpth_heap_tracker' in l)]
 counts=[];rss=[]
 for sample in samples:
  for line in sample['output'].splitlines():
   m=re.fullmatch(r'\s*(\d+)\s+/proc/'+str(pid)+r'/maps\s*',line)
   if m:counts.append(int(m[1]))
   m=re.match(r'VmRSS:\s+(\d+)\s+kB',line)
   if m:rss.append(int(m[1]))
 row.update({'npth_hook_refusal_lines':refusal,'npth_debug_mapped_samples':sum(bool(re.search(r'^[0-9a-f]+-[0-9a-f]+.*libnpth_(xasan|heap_tracker)',s['output'],re.M)) for s in samples),
             'maps_min':min(counts) if counts else None,'maps_max':max(counts) if counts else None,'rss_peak_kib':max(rss) if rss else None,
             'get_meta_crash_files':[p.name for p in r.glob('cppcrash-*.txt') if 'get_meta' in p.read_text(errors='replace')]})
 row['article_numeric_window_pass']=bool(final_alive and row['alive_after_last_resumed_s'] is not None and row['alive_after_last_resumed_s']>=180 and not row['metasec_ule_to_main_exit'] and not row['get_meta_crash_files'] and not terminal)
 row['missing_symbol_relocations']=[l for l in lines if 'symbol not found' in l]
 row['closure_numeric_gate']=bool(row['article_numeric_window_pass'] and not row['missing_symbol_relocations'] and not row['metasec_ule_count'])
 row['metasec_ule_absent']=not row['metasec_ule_count']
 row['platform_back_handler_all_errors']=[l for l in lines if l.startswith("[UNCAUGHT] thread='platform-back-handler'")]
 row['metasec_boolean_null_exception']=bool('boolean java.lang.Boolean.booleanValue()' in log and '[UNCAUGHT]   at ms.bd.c.p2.d' in log)
 row['main_exception_lines']=[l for l in lines if 'J_invokeStaticMain_main_threw:' in l]
 row['stub_numeric_gate']=bool(row['article_numeric_window_pass'] and not row['platform_back_handler_all_errors'])
 row['metasec_boolean_null_to_main_exit']=bool(row['metasec_boolean_null_exception'] and row['null_looper_main'] and terminal and 'exited(1)' in terminal[-1])
 row['original_cppcrash_lifetime_s']=[int(m[1]) for p in r.glob('cppcrash-*.txt') if (m:=re.search(r'Process life time:(\d+)s',p.read_text(errors='replace')))]
 row['native_a4_sigsegv']=bool(re.search(r'Fatal signal 11.*?Thread: \d+ \"a-4\"',log,re.S) and terminal and 'signal 11' in terminal[-1])
 row['fatal_thread_lines']=[l for l in lines if l.startswith('Thread:')]
 row['no_original_exit']=bool(final_alive and not terminal)
 (r/'summary.json').write_text(json.dumps(row,indent=2)+'\n')
(R/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r['round'],r['pid'],r['terminal'],'alive_age',round(r['last_observed_alive_age_s'],2),'end_age',round(r['end_age_s'],2),'metasec_ule_to_exit',r['metasec_ule_to_main_exit'],'article_numeric_window_pass',r['article_numeric_window_pass'],'refusals',len(r['npth_hook_refusal_lines']))
