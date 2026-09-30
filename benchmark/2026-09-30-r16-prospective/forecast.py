#!/usr/bin/env python3
"""Outcome-blind r16 forecasts from allowlisted frozen predecessors only."""
import csv,datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRE=HERE.parent/'2026-09-29-static-wall-prediction'
MITIGATED={'jobscheduler-startup','shortcutmanager','network-permission'}
KNOWN_LIT={'aegis','fd-AppManager','fd-droidify','noice','fd-noice','fd-stk'}
JOB_RECOVERY={'fd-fitness','fd-calendar','fd-client','fd-reader','fd-feeder','newpipe','fd-libretube','fd-organicmaps','ooniprobe'}
OVERRIDES={
 'wikipedia':('no','application-init','medium','Previously disclosed r16 sanity advanced beyond offline callback but still had onResume/WikiSite failure; networking is insufficient proof.'),
 'anki':('no','launcher-entry','medium','Previously disclosed r15c diagnosis selected LeakCanary launcher; installer main-entry choice is not among stated r16 fixes.'),
 'fd-notes':('yes','none','medium','Previously disclosed cc-t3 r15c t10 read found Notes editor; initial t5 blank is not the later visual state. Outer adjudication still required for r16.'),
 'fd-seal':('no','install-native-validation','low','r15c failed before launch; #77 patch acceptance does not prove this installer has the precise native-data exceptions.'),
 'toutiao':('no','install-native-validation','low','Manifest size fix may be present but prior mixed-class native entry validation remains a risk; installation forecast is conditional.'),
 'x':('no','install-manifest','low','r15c failed installation; current installer permission mapping alone does not prove manifest-buffer/split handling changed.'),
 'subwaysurfers':('no','install-unknown','low','Prior failure occurred before screenshots; exact remaining installation cause unknown.'),
 'fd-musicplayer':('no','bitmap-colorspace','medium','r15c cannot create bitmap without color space; no matching r16 fix disclosed.'),
 'fd-mobile':('no','application-init','medium','r15c KoinApplication not started; no targeted r16 initialization repair disclosed.'),
 'fd-com-amaze-filemanager':('no','application-classloading','medium','r15c AppConfig/Multidex initialization failed; no matching r16 fix disclosed.'),
 'fd-binaryeye':('no','unknown','low','Blank cause not established; connectivity/coroutine warning alone is not causal proof and camera support remains a latent risk.'),
 'fd-filemanager':('no','unknown','low','Blank cause not established; coroutine warning is known tolerated elsewhere.'),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def decide(r):
 key=r['app'];remaining=[f for f in r['observed_wall_order'] if f not in MITIGATED]
 if key in OVERRIDES:return OVERRIDES[key],remaining
 if key in KNOWN_LIT:return ('yes','none','high','Preserve accepted own UI; dual-layer network fix may additionally restore online content.'),remaining
 if key in JOB_RECOVERY and not remaining:
  conf='medium' if key in {'fd-fitness','fd-calendar','fd-client','fd-reader'} else 'low'
  return ('yes','none',conf,'Forecast startup recovery from OnlineJobScheduler/OnlineConnectivityManager; downstream initialization or a new wall may still defeat it.'),remaining
 if remaining:return ('no',remaining[0],'medium','Observed startup requirement remains outside disclosed r16/network repairs.'),remaining
 return ('no','unknown','low','No proven path from disclosed fixes to own UI; remaining root cause unknown.'),remaining
def main():
 if (HERE/'freeze.json').exists():raise SystemExit('Frozen forecast exists; no overwrite')
 inputs=[PRE/'task90-feedback-static/predictions.json',PRE/'task90-feedback-static/freeze.json',PRE/'task90-feedback-static/matrix.json',PRE/'task90-r15c/predictions.json',PRE/'task90-r15c/freeze.json']
 for folder in ['task90-feedback-static','task90-r15c']:
  d=PRE/folder;f=json.loads((d/'freeze.json').read_text())
  for x in f['outputs']:
   if sha(d/x['path'])!=x['sha256']:raise ValueError('Input freeze mismatch')
 prior=json.loads(inputs[0].read_text());rows=[]
 for r in prior:
  decision,remaining=decide(r);light,wall,confidence,reason=decision
  rows.append({'app':r['app'],'apk_sha256':r['apk_sha256'],'package':r['package'],'expected_lit':light=='yes','expected_first_wall':wall,'confidence':confidence,'reason':reason,'r15c_visual':r['visual'],'r15c_observed_walls':r['observed_wall_order'],'predicted_mitigated_walls':[f for f in r['observed_wall_order'] if f in MITIGATED],'remaining_observed_candidates':remaining,'latent_static_candidates':r.get('candidate_wall_order',[]),'static_coverage':r['new_static_coverage'],'network_content_recovery':r['app'] in {'noice','fd-noice'},'prediction_profile':'r16 6a5d7fca + appspawn d977bd15 + libbms 6f94d4f4 + installer eb6824b4 + reinstall with HAP INTERNET','runtime_uncertainty':'A/B native generation parity not assumed; record actual hashes before attributing a miss. CommonEvent #91 is not assumed installed.','evidence':{'prior':str(inputs[0])+'#'+r['app'],'r15c_log':str(PRE/'task90-r15c/evidence/logs'/f'{r["app"]}.json')}})
 assert len(rows)==66 and len({r['app'] for r in rows})==66
 write(HERE/'predictions.json',rows)
 with (HERE/'predictions.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()})
 policy={'version':1,'lighting_definition':'Own app UI at any captured scheduled shot in this run, including identified loading/content-error UI; exclude desktop, blank/black window, system crash dialog or unrelated/debug launcher. Final observed labels require screenshot adjudication.','lighting_labels':['lit','not-lit','unknown'],'wall_definition':'Earliest adjudicated startup blocker preventing own UI, not last exception or tolerated warning. For lit apps use none, even if nonblocking warnings remain.','lighting_denominator':'Exact APK identity, completed record, adjudicated lit/not-lit. Unknown and unmatched excluded with count.','first_wall_denominator':'Exact APK identity, completed record, adjudicated non-lit first wall other than unknown, and a non-unknown forecast. Unknown forecasts are abstentions reported separately; also publish conservative coverage-adjusted score counting forecast abstentions as misses.','strict_pre_click':'clicked_at strictly greater than frozen_at; missing clicked_at unknown, earlier click outcome-blind-only. Report all exact adjudicated and strict-pre-click separately.','profile_strata':'Report requested-profile-confirmed vs mismatch vs unknown; never silently discard mismatch misses from overall exact-APK score.','no_results_read_declaration':'No r16full A/B record, log, summary, screenshot, directory listing or triage read before freeze. Prior r16 sanity and rollout/control messages were disclosed and are training context.','mitigations':sorted(MITIGATED),'not_assumed_fixed':['CommonEvent JNI #91','VelocityTracker on both boards','guest dlopen thread readiness','app native namespace/dependencies','activity theme/colorspace','launcher entry selection','all prior installation walls'],'known_prior_disclosures':['r16 sanity: OnlineCM/OnlineJobScheduler/ShortcutManager; Wiki still onResume failure','cc-t3 r15c correction: fd-notes t10 editor; anki LeakCanary launcher','61b previously retained VT/liblog fixes; native parity for r16 full is unknown','5cd/61b network components deployed; per-app HAP grant requires reinstall']}
 write(HERE/'policy.json',policy)
 score_inputs=[HERE/'forecast.py',HERE/'score.py',HERE/'policy.json']
 now=datetime.datetime.now().astimezone().isoformat()
 receipt={'frozen_at':now,'outcome_exposure':'r15c + disclosed r16 sanity/control only; no r16full outcomes','inputs':[{'path':str(p),'sha256':sha(p)} for p in inputs],'outputs':[{'path':p.name,'sha256':sha(p)} for p in [HERE/'predictions.json',HERE/'predictions.csv',*score_inputs]],'expected_lit':sum(r['expected_lit'] for r in rows),'expected_not_lit':sum(not r['expected_lit'] for r in rows),'unknown_first_wall':sum(r['expected_first_wall']=='unknown' for r in rows)}
 write(HERE/'freeze.json',receipt)
 (HERE/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
