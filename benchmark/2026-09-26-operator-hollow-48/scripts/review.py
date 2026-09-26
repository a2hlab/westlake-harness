from pathlib import Path
import json,re,subprocess,sys
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/hollow48';d=r/sys.argv[1]
lines=(d/'child.stderr').read_text(errors='replace').splitlines();sample=[json.loads(l) for l in (d/'samples.jsonl').read_text().splitlines()];j=json.loads((d/'result.json').read_text());pid=j['child'];parent=(d/'parent.log').read_text(errors='replace')
alive=[s['elapsed'] for s in sample if any(l.startswith(str(pid)+' (') and l.rsplit(') ',1)[1].split()[0]!='Z' for l in s['output'].splitlines())]
refused=['libnpth_xasan','libnpth_heap_tracker','libgodzilla-memsponge','libjato','libmonitorcollector-lib','libsysoptimizer','libnpth_vm_monitor','libnpth','libakamaibmp']
maps=[]
for f in sorted(list(d.glob('maps*.maps'))+list((d/'faults').glob('*.maps'))):
 s=f.read_text();maps.append({'file':str(f.relative_to(d)),'bytes':len(s),'lines':len(s.splitlines()),'valid':len(s.splitlines())>100 and '[stack]' in s,'refused_mapped':[n for n in refused if '/'+n+'.so' in s], 'npth_mapped':'/libnpth.so' in s})
visual=json.loads((d/'visual-review.json').read_text()) if (d/'visual-review.json').exists() else {}
j.update(last_alive_sample_s=max(alive,default=0),native_sig11_headers=[l for l in lines if l.startswith('Fatal signal 11')],native_sig11_snapshots=[p.name for p in (d/'faults').glob('*.txt') if 'signal=0xb' in p.read_text(errors='replace')],parent_exit_one='child '+str(pid)+' exited(1)' in parent,main_threw=any('J_invokeStaticMain_main_threw' in l for l in lines),uncaught=[l for l in lines if l.startswith("[UNCAUGHT] thread=")],refusals=[l for l in lines if l.startswith('[WESTLAKE-LOADER] refusing')],maps_review=maps,body_pass=visual.get('body_text_visible',False),feed_pass=visual.get('feed_real_titles',False),lifecycle=[l for l in lines if l.startswith(('[B47-SLA] ENTRY','[ABILITY38-RESUMED]'))])
j['stability_pass']=bool(j.get('alive_before_cleanup') and j['last_alive_sample_s']>=180 and not j.get('failure') and not j.get('cleanup_failure') and not j['native_sig11_headers'] and not j['native_sig11_snapshots'] and not j['parent_exit_one'] and not j['main_threw'])
j['ule_lines']=[l for l in lines if 'UnsatisfiedLinkError' in l]
j['npth_load_lines']=[l for l in lines if 'npth' in l.lower() and any(t in l for t in ('JNI','LOAD','dlopen','failed','refusing'))]
j['npth_mapping_pass']=any(m['valid'] and m['npth_mapped'] for m in maps)
j['combo_mapping']={n:any(m['valid'] and '/'+n in (d/m['file']).read_text() for m in maps) for n in ['libnpth.so','libgodzilla-memsponge.so','libmonitorcollector-lib.so','libgodzilla-sysopt.so']}
j['acceptance_pass']=bool(j.get('alive_before_cleanup') and j['last_alive_sample_s']>=180 and not j.get('failure') and not j['native_sig11_headers'] and not j['native_sig11_snapshots'] and not j['parent_exit_one'] and not j['main_threw'] and j['body_pass'] and j['feed_pass'] and any(m['valid'] for m in maps) and all(j['combo_mapping'].values()) and not j['ule_lines'])
(d/'strict-review.json').write_text(json.dumps(j,indent=2));print(json.dumps(j,indent=2))
