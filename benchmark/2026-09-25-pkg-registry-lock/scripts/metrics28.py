"""Recompute before/after medians and observed certificate invocation counts."""
import pathlib,json,gzip,statistics,re,sys
root=pathlib.Path(sys.argv[1]); summaries=json.loads((root/'summary.json').read_text())
def read(p):
 if p.exists():return p.read_text(errors='replace')
 return gzip.decompress(pathlib.Path(str(p)+'.gz').read_bytes()).decode(errors='replace')
trials=[];diagnostics=[];controls=[]
for row in summaries:
 name=row['run'];lines=read(root/name/'child.stderr').splitlines()
 cert=[{'line':i,'text':s} for i,s in enumerate(lines,1) if '[SOURCE-CERT]' in s]
 detail={**row,'uncaught_exceptions':[{'line':i,'text':s} for i,s in enumerate(lines,1) if '[UNCAUGHT]' in s],'certificates':cert,'certificate_starts':sum('[SOURCE-CERT] start ' in x['text'] for x in cert),'certificate_passes':sum('[SOURCE-CERT] pass ' in x['text'] for x in cert),'certificate_failures':sum('[SOURCE-CERT] fail ' in x['text'] for x in cert)}
 if name.startswith('control-'):
  detail['observation']=json.loads(read(root/name/'control-result.json'));controls.append(detail);continue
 detail['child_pid']=json.loads(read(root/name/'device-report.json'))['child']
 actions=json.loads(read(root/name/'actions.json'))
 detail['click_since_measurement_start_s']=round(next(a['epoch'] for a in actions if a['command']=='echo i 309 213 > /data/local/tmp/noice_tap')-actions[0]['epoch'],3)
 detail['registry_ui_samples']=[s for s in row['ui_stacks'] if 'SourcePackageRegistry' in '\n'.join(s['stack'])]
 if 'diag' in name:diagnostics.append(detail)
 else:
  assert len(row['touches'])==2 and not row['unconsumed_posts']
  assert not row['ui_stacks'] or min(s['line'] for s in row['ui_stacks'])>max(t['run_line'] for t in row['touches'])
  detail['post_run_ms']={('down' if t['action']==0 else 'up'):t['latency_ms'] for t in row['touches']}
  trials.append(detail)
baseline=json.loads((root.parents[1]/'2026-09-25-touch-factorial/results.json').read_text())
comparisons=[]
for mode in ('offline','online'):
 before=[t for t in baseline['trials'] if t['run'].startswith(mode+'-fresh-')]
 after=[t for t in trials if t['run'].startswith(mode+'-fresh-')]
 assert len(before)==len(after)==2
 def stats(rows):
  return {'runs':[t['run'] for t in rows], 'median_down_ms':statistics.median(t['post_run_ms']['down'] for t in rows),'median_up_ms':statistics.median(t['post_run_ms']['up'] for t in rows),'median_click_max_ms':statistics.median(max(t['post_run_ms'].values()) for t in rows)}
 a=stats(after);comparisons.append({'cell':mode+'-fresh','before':stats(before),'after':a,'under_2s':a['median_click_max_ms']<2000})
result={'task':28,'source_commit':read(root/'source-commit.txt').strip(),'status':'done' if all(x['under_2s'] for x in comparisons) else 'blocked','R2':'partially','board':'5ea34a4500000000000000001123012c','apk_sha256':baseline['apk_sha256'],'metric':'Per click maximum of DOWN/UP post-to-run; median across two independent processes. Also report each action separately.','comparisons':comparisons,'trials':trials,'diagnostics':diagnostics,'controls':controls}
(root.parent/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
for c in comparisons:print(c['cell'],c['before']['median_click_max_ms'],'->',c['after']['median_click_max_ms'],'ms; <2s:',c['under_2s'])
for r in trials+diagnostics:print(r['run'],'certificate calls:',r['certificate_starts'],'pass:',r['certificate_passes'],'UI registry samples:',len(r['registry_ui_samples']))
