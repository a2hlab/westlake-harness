import pathlib,json,gzip,hashlib,re
root=pathlib.Path(__file__).resolve().parents[1];r=pathlib.Path.home()/'a2hlab/board/61b0657200000000000000000324012c/bounded48'
rows=[]
for p in sorted(r.glob('*-r*/result.json')):
 d=p.parent;j=json.loads(p.read_text());log=(d/'child.stderr').read_text(errors='replace') if (d/'child.stderr').exists() else '';lines=log.splitlines()
 ent='[B47-SLA] ENTRY bundle=com.ss.android.article.news ability=com.ss.android.detail.feature.detail2.view.NewDetailActivity recordId='
 pos=max((i for i,l in enumerate(lines) if ent in l),default=-1)
 end=next((i for i in range(pos+1,len(lines)) if lines[i].startswith('[B47-SLA] ENTRY ')),len(lines))
 resumes=[l for l in lines[pos+1:end] if l.startswith('[ABILITY38-RESUMED]')] if pos>=0 else []
 inputs=[json.loads(l) for l in (d/'inputs.jsonl').read_text().splitlines()] if (d/'inputs.jsonl').exists() else []
 clicks=[float(i['output'].split()[0]) for i in inputs if '-d 380 ' in i['command']]
 click=clicks[-1] if clicks else None
 resume=float(re.search(r'uptime=(\d+)',resumes[0])[1])/1000 if resumes else None
 snapshots=[p.name for p in (d/'faults').glob('*.txt') if 'signal=0xb' in p.read_text(errors='replace')]
 j.update(input_records=inputs,article_attempt_uptimes=clicks,lifecycle_entries=[l for l in lines if l.startswith('[B47-SLA] ENTRY ')],fatal_thread_headers=[lines[i+3] for i,l in enumerate(lines) if l.startswith('Fatal signal') and i+3<len(lines)],detail_entry=pos>=0,detail_resumed=resumes,article_click_uptime=click,click_to_resumed_s=resume-click if resume and click else None,
   native_sig11_headers=[l for l in lines if 'Fatal signal 11' in l],native_sig11_snapshots=snapshots,
   fatal_headers=[l for l in lines if l.startswith('Fatal signal')],
   boolean_null_npe='boolean java.lang.Boolean.booleanValue()' in log,
   main_exception=[l for l in lines if 'J_invokeStaticMain_main_threw' in l],
   platform_errors=[l for l in lines if l.startswith("[UNCAUGHT] thread='platform-back-handler'")],
   anonymous_jit='using ART anonymous cache' in log,file_jit='using app-private unlinked file' in log,
   other_errors=[l for l in lines if l.startswith('[UNCAUGHT] thread=')])
 j['body_verified']=json.loads((d/'visual-review.json').read_text()).get('body_text_visible',False) if (d/'visual-review.json').exists() else False
 j['acceptance_pass']=bool(j.get('alive_before_cleanup') and not j.get('failure') and not j.get('cleanup_failure') and resumes and j['body_verified'] and not j['native_sig11_headers'] and not snapshots and not j['boolean_null_npe'] and not j['main_exception'])
 (d/'summary.json').write_text(json.dumps(j,indent=2));rows.append(j)
(r/'summary.json').write_text(json.dumps(rows,indent=2));print(json.dumps([{k:j.get(k) for k in ('round','child','failure','observed_seconds','alive_before_cleanup','detail_entry','click_to_resumed_s','native_sig11_headers','native_sig11_snapshots','cleanup_failure','mem_available_after_kib')} for j in rows],indent=2))
out=root/'evidence';out.mkdir(exist_ok=True);manifest=[]
for p in sorted(r.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();packed=len(raw)>65536 and p.suffix!='.jpeg';data=gzip.compress(raw,mtime=0) if packed else raw
 name=str(p.relative_to(r))+('.gz' if packed else '');q=out/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
 manifest.append(dict(path=name,source=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),gzip=packed))
expected={e['path'] for e in manifest}|{'manifest.json'}
for p in out.rglob('*'):
 if p.is_file() and str(p.relative_to(out)) not in expected:p.unlink()
(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print('EXPORTED',len(manifest))
