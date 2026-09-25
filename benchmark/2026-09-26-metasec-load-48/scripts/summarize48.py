"""Summarize each original app instance; literal errno=13 and Permission denied both count."""
from board48 import *
rows=[]
for r in sorted(R.glob('*-r[0-9]*')):
 if not (r/'result.json').exists():continue
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
 consent=float(inputs[0]['output'].split()[0]) if inputs else None
 clicks=[float(i['output'].split()[0]) for i in inputs if '-d 380 295' in i['command']]
 resumed=[l for l in lines if l.startswith('[ABILITY38-RESUMED]')]
 detail=[l for l in lines if l.startswith('[B47-SLA] ENTRY') and 'NewDetailActivity' in l]
 detail_position=max((i for i,l in enumerate(lines) if l.startswith('[B47-SLA] ENTRY') and 'NewDetailActivity' in l),default=-1)
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
(R/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r['round'],r['pid'],r['terminal'],'alive_age',round(r['last_observed_alive_age_s'],2),'end_age',round(r['end_age_s'],2),'eacces',r['metasec_eacces_count'],'eacces_to_exit',r['eacces_to_main_exit'],'over3m',r['startup_over_180s'])
