from pathlib import Path
import json,re,sys
R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/clamp48'
rows=[]
for d in sorted(R.glob('clamp-r[1-5]')):
 if not (d/'result.json').exists():continue
 j=json.loads((d/'result.json').read_text());lines=(d/'child.stderr').read_text(errors='replace').splitlines();parent=(d/'parent.log').read_text(errors='replace');visual=json.loads((d/'visual-review.json').read_text()) if (d/'visual-review.json').exists() else {}
 life=[];cur=None
 for l in lines:
  if l.startswith('[B47-SLA] ENTRY '):cur={'entry':l,'resumed':[]};life.append(cur)
  if l.startswith('[ABILITY38-RESUMED]') and cur:cur['resumed'].append(l)
 guard=[l for l in lines if l.startswith('[OH_WSA-relayout] DEGENERATE') and '[#48 Layout:-79 guard]' in l]
 layout=[l for l in lines if 'Layout: -79 < 0' in l and len(l)<4000]
 exceptions=[l for l in lines if 'J_invokeStaticMain_main_threw' in l or l.startswith('[UNCAUGHT]')]
 faults=[p.name for p in (d/'faults').glob('*.txt') if 'signal=0xb' in p.read_text(errors='replace')]
 fatal=[l for l in lines if l.startswith('Fatal signal')]
 exits=[l for l in parent.splitlines() if ('child '+str(j['child'])+' exited(') in l or ('child '+str(j['child'])+' killed') in l]
 sig11=any('signal 11' in l for l in fatal) or bool(faults) or any(re.search(r'signal[ =]11\b',l) for l in parent.splitlines())
 exit1=any('exited(1)' in l for l in exits)
 maps=[p.read_text(errors='replace') for p in list(d.glob('maps*.maps'))+list((d/'faults').glob('*.maps'))]
 native={n:any('/'+n in m for m in maps) for n in ('libnpth.so','libgodzilla-memsponge.so','libmonitorcollector-lib.so','libgodzilla-sysopt.so')}
 j['articles']=json.loads((d/'articles.json').read_text()) if (d/'articles.json').exists() else []
 j.update(guard_count=len(guard),guard_examples=guard[:3],layout79_lines=layout,main_exceptions=exceptions,native_sig11=bool(sig11),sig11_snapshots=faults,fatal_headers=fatal,parent_exit1=exit1,parent_exit_lines=exits,activity_lifecycles=life,visual=visual,library_mapping=native,ule_lines=[l for l in lines if 'UnsatisfiedLinkError' in l and len(l)<4000])
 j['stability_pass']=bool(j.get('alive_before_cleanup') and j['observed_seconds']>=180 and not j.get('failure') and not j.get('cleanup_failure') and not sig11 and not layout and not exit1 and not any('J_invokeStaticMain_main_threw' in l for l in exceptions))
 j['newdetail_resumed']=any('NewDetailActivity' in a['entry'] and a['resumed'] for a in life)
 j['inflow_resumed']=any('ArticleInflowActivity' in a['entry'] and a['resumed'] for a in life)
 (d/'clamp-review.json').write_text(json.dumps(j,indent=2,ensure_ascii=False))
 (d/'guard-lifecycle.txt').write_text('\n'.join(l for l in lines if l.startswith(('[OH_WSA-relayout] DEGENERATE','[B47-SLA] ENTRY','[ABILITY38-RESUMED]','Fatal signal','[CM-EXIT]')) or ('Layout: -79 < 0' in l and len(l)<4000))+'\n')
 (d/'guard-context.txt').write_text('\n'.join('\n'.join(lines[max(0,i-1):i+5]) for i,l in enumerate(lines) if l.startswith('[OH_WSA-relayout] DEGENERATE'))+'\n')
 rows.append(j)
summary=dict(rounds=rows,stable_count=sum(j['stability_pass'] for j in rows),body_count=sum(len(j['articles']) for j in rows),inflow_rounds=[j['round'] for j in rows if j['inflow_resumed']],newdetail_rounds=[j['round'] for j in rows if j['newdetail_resumed']])
summary['acceptance_pass']=len(rows)==5 and summary['stable_count']==5 and summary['body_count']>=3 and bool(summary['inflow_rounds']) and bool(summary['newdetail_rounds']) and all(j['guard_count']>0 for j in rows)
(R/'final-acceptance.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print(json.dumps([{k:j[k] for k in ('round','child','observed_seconds','stability_pass','guard_count','native_sig11','parent_exit1','newdetail_resumed','inflow_resumed')} for j in rows],indent=2))
