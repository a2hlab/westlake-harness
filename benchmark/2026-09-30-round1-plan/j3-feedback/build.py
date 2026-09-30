#!/usr/bin/env python3
"""J3 evidence refresh and conditional unlock expectations, offline only."""
import csv,json,re
from collections import Counter
from pathlib import Path
from extract import HERE,ROOT,SOURCE,sha,dump

def main():
 evidence={r['key']:r for r in json.loads((HERE/'evidence.json').read_text())}
 prior=json.loads((HERE.parent/'u2-feedback-addendum/next-clusters.json').read_text())
 original=json.loads((HERE.parent/'u2-feedback-addendum/unlit-42.json').read_text())
 inputs=json.loads((ROOT/'benchmark/2026-09-30-input-recovery/results.json').read_text())
 lit={k for k,e in evidence.items() if e['lit']};rows=[];snippets={}
 def events(k,pat):
  e=evidence[k];lines=Path(e['log']).read_text(errors='replace').splitlines()
  hits=[dict(line=n,text=l) for n,l in enumerate(lines,1) if len(l.split())>2 and l.split()[2] in e['pids'] and re.search(pat,l)]
  return hits
 for p in original:
  k=p['key'];e=evidence[k];causes=[x for x in e['chain'] if 'Caused by:' in x['text']];blocker=causes[-1] if causes else e['anchor'];fatal=(e['first_terminal'] or {}).get('anchor')
  if k in ['firefox','fd-fennec_fdroid']:blocker=events(k,r'libjnidispatch.so s=__sF')[0]
  if k=='ppsspp':
   blocker=events(k,r'LoadLibrary failed')[0];fatal=events(k,r'System.exit called')[0]
   p['cause']='J3 catches failure to load libGLESv2.so, later calls System.exit(-1); no J3 SIGSEGV is established by this log.'
  if k in ['vlc','fd-shatteredpixeldungeon']:blocker=events(k,r'Error loading shared library')[0]
  p.update(log=e['log'],log_sha256=e['log_sha256'],record=e['record'],record_sha256=e['record_sha256'],pids=e['pids'],alive_t5=e['alive_t5'],alive_t20=e['alive_t20'],first_blocker=blocker,first_fatal=fatal,has_explicit_fatal=fatal is not None,actual_lit=k in lit)
  # Old excerpts refer to U2, so keep them only behind an explicitly named source.
  p.pop('faultlogs',None);p.pop('secondary_evidence',None);p.pop('U0_first_failure',None)
  p['historical_U2_assessment']={name:p.pop(name) for name in list(p) if name.startswith(('U0_','U1_')) or name in ['known_U0_secondary_wall','faultlog_review']}
  p['faultlogs']=e.get('faultlogs',[])
  p['prior_receipt']=str(HERE.parent/'u2-feedback-addendum/unlit-42.json')
  if k=='fd-noice':p['cause']='Already outer-signed lit in J3; background SSLSockets failure remains. Functional repair, not new first-screen unlock.';p['secondary_evidence']=events(k,r'B8-UEH.*SSLSockets')[:2]
  if k=='fd-api':p['cause']='AliasTargetTheme fixes ID, but same Theme.AppCompat exception remains; resource/context investigation, not proved parser defect or completed theme-wall passage.';p['secondary_evidence']=events(k,r'B8-ALIASTHEME')[:1]
  if p['batch']=='input':p['offline_input_status']=next(x['status'] for x in inputs['inputs'] if x['key']==k)
  rows.append(p)
 np=events('newpipe',r'B8-ANDROIDPKG.*synthesized|B8-AMB.*(?:failed|caused by)')
 assert any('Platform signature not found' in x['text'] for x in np)
 snippets['newpipe']=np
 snippets['fd-api']=events('fd-api',r'B8-ALIASTHEME|Caused by:.*Theme.AppCompat')[:3]
 snippets['fd-noice']=events('fd-noice',r'B8-UEH.*SSLSockets')[:3]
 assert any('Theme.AppCompat' in x['text'] for x in snippets['fd-api'])
 bykey={r['key']:r for r in rows};clusters=[]
 low={'J4-null-producer','J4-cache-input','J4-verifier-interface','J4-intent-contract','J4-restrictions','N3-webview','N3-theme-projection','N3-no-fatal-observation','J4-alias-theme'}
 for c in prior:
  c['prior_U2_cluster_id']=c['cluster_id'];cid=c['cluster_id']
  c['execution_lane']={'J4':'cc-t3','N3':'cx-t0','input':'cx-bms'}[c['batch']]
  if cid=='J4-boot-api':c['layer']='boot';c['execution_lane']='oc-t4 (#91/T7), cc-t3 API consumers'
  c['currently_unlit_keys']=[k for k in c['keys'] if k not in lit]
  c['already_lit_functional_keys']=[k for k in c['keys'] if k in lit]
  c['expected_unlock_keys']=[] if cid in low or cid=='J4-boot-api' else list(c['currently_unlit_keys'])
  c['conditional_unlock_keys']=list(c['currently_unlit_keys']) if cid in low or cid=='J4-boot-api' else []
  c['expected_new_lights']=None
  c['prediction']='过墙 if specified repair removes the observed API failure; first-screen outcome unknown'
  c['dependency_note']='Secondary apps require their earlier first wall to be cleared; counts are unique keys, not added lighting claims.'
  if cid=='J4-boot-api':c['dependency_note']='Needs #91/T7 boot-classpath artifacts. Ordinary J4 adapter JAR alone predicts zero unlocks for these five boot classes.'
  if cid=='J4-alias-theme':c['dependency_note']='Alias ID fixed but AppCompat still fails. Coordinate resource/context owner; no repeat alias-only repair predicted to unlock fd-api.'
  if cid=='N3-theme-projection':c['dependency_note']='N3 candidate fixes GLES visibility only; selected-context/theme investigation remains. Do not invent a native resource fallback.'
  if cid in low:c['prediction']='unknown until producer/context mechanism is located; affected apps are candidates, not guaranteed repair yield'
  if cid=='INPUT-assembly':c['expected_unlock_keys']=c['keys'];c['prediction']='host preflight now passes all three; BMS install and first-screen remain unknown; Subway is revised identity'
  c['evidence']=[dict(key=k,log=bykey[k]['log'],log_sha256=bykey[k]['log_sha256'],blocker=bykey[k]['first_blocker'],fatal=bykey[k]['first_fatal']) for k in c['keys']]
  c['additional_evidence']=[dict(key=k,log=evidence[k]['log'],events=events(k,r'Error loading shared library|Error relocating')[:2]) for k in c['additional_observed_keys']]
  # Refresh data fields whose U2 values no longer describe J3.
  c['fatal_keys']=[k for k in c['keys'] if bykey[k]['has_explicit_fatal']];c['fatal_app_count']=len(c['fatal_keys'])
  c['observation_or_input_keys']=[k for k in c['keys'] if not bykey[k]['has_explicit_fatal']]
  c['notes']=[bykey[k]['cause'] for k in c['keys']]
  c['rank_blocked_app_count']=len(c['currently_unlit_keys'])
  clusters.append(c)
 clusters.append(dict(cluster_id='J4-platform-signature',layer='JAR',batch='J4',execution_lane='cc-t3',keys=['newpipe'],app_count=1,rank_blocked_app_count=0,currently_unlit_keys=[],already_lit_functional_keys=['newpipe'],expected_unlock_keys=[],conditional_unlock_keys=[],additional_observed_keys=[],expected_new_lights=0,prediction='Already lit; predict PlayerService bind progresses past Platform signature not found after coherent platform package signing metadata repair. Playback remains unverified.',dependency_note='No screenshot increment counted for a functional repair.',evidence=[dict(key='newpipe',log=evidence['newpipe']['log'],log_sha256=evidence['newpipe']['log_sha256'],events=np)]))
 clusters.sort(key=lambda c:(-c['rank_blocked_app_count'],-len(c['expected_unlock_keys']),c['cluster_id']))
 dump(HERE/'per-key.json',rows);dump(HERE/'next-clusters.json',clusters);dump(HERE/'target-evidence.json',snippets)
 for batch in ['J4','N3','input']:dump(HERE/(batch+'.json'),[c for c in clusters if c['batch']==batch])
 flat=[dict(cluster=c['cluster_id'],batch=c['batch'],layer=c['layer'],lane=c['execution_lane'],blocked_count=c['rank_blocked_app_count'],expected_unlock_keys=c['expected_unlock_keys'],conditional_unlock_keys=c['conditional_unlock_keys'],already_lit_functional_keys=c['already_lit_functional_keys'],additional_keys=c['additional_observed_keys'],prediction=c['prediction'],dependencies=c['dependency_note']) for c in clusters]
 with (HERE/'unlock-priority.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader()
  for r in flat:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in r.items()})
 facts=json.loads((HERE/'record-facts.json').read_text());runs=json.loads((HERE/'run-audit.json').read_text())
 assert len(evidence)==66 and len(lit)==25 and sum(not r['actual_lit'] for r in rows)==41
 result=dict(profile='U2 + J3 75c2068c',keys=66,lit=25,unlit=41,returned=['fd-noice'],retained_U2_lit=24,unlit_primary_batches=dict(Counter(r['batch'] for r in rows if not r['actual_lit'])),cluster_count=len(clusters),newpipe_included_as_functional_not_unlit=True,expected_new_lights='unknown; unlock means named API checkpoint only',facts_total=[next(l for l in x['facts'].splitlines() if l.startswith('TOTAL ')) for x in runs],captured=sum(f['captured'] for f in facts),alive={t:dict(yes=sum(f['alive_'+t] is True for f in facts),no=sum(f['alive_'+t] is False for f in facts),unknown=sum(f['alive_'+t] is None for f in facts)) for t in ['t5','t20']},source_sha256={str(p):sha(p) for p in [SOURCE/'results.json',SOURCE/'README.md',HERE.parent/'u2-feedback-addendum/next-clusters.json',ROOT/'benchmark/2026-09-30-input-recovery/results.json']},fd_api_verdict_correction='Outer image signature retained; source README claim of passing AppCompat contradicted by hilog:18447 and cc-t3 18:04 update. Alias ID change alone is not passage.',device_actions=0)
 dump(HERE/'results.json',result)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
